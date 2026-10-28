#!/usr/bin/env python3
"""BMI270-Ausgabe kompatibel zu mpu_py/mpuAngle.py.

Der Sensor wird nicht automatisch genullt. Die drei Winkel entstehen bei jeder
Messung direkt aus dem aktuellen Beschleunigungsvektor, genau wie im MPU-Skript.
"""

import argparse
import base64
import gzip
import json
import math
import struct
import sys
import time

try:
    from smbus2 import SMBus
except ImportError:
    try:
        from smbus import SMBus
    except ImportError as exc:
        raise SystemExit(
            "Das I2C-Modul fehlt. Installation: sudo apt install python3-smbus "
            "oder: python3 -m pip install smbus2"
        ) from exc


# Der BMI270 braucht nach jedem Reset seine offizielle 8-KiB-Konfiguration.
# Sie stammt aus dem Bosch BMI270 Sensor API und ist hier komprimiert eingebettet.
_CONFIG_GZIP_BASE64 = "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"


class BMI270:
    CHIP_ID_REG = 0x00
    CHIP_ID = 0x24
    DATA_REG = 0x0C       # Accel XYZ, danach Gyro XYZ (je int16 little-endian)
    INTERNAL_STATUS = 0x21
    TEMP_REG = 0x22
    ACC_CONF = 0x40
    ACC_RANGE = 0x41
    GYR_CONF = 0x42
    GYR_RANGE = 0x43
    INIT_CTRL = 0x59
    INIT_ADDR_0 = 0x5B
    INIT_ADDR_1 = 0x5C
    INIT_DATA = 0x5E
    PWR_CONF = 0x7C
    PWR_CTRL = 0x7D
    CMD = 0x7E

    def __init__(self, bus, address):
        self.bus = bus
        self.address = address

    def read_byte(self, register):
        return self.bus.read_byte_data(self.address, register)

    def write_byte(self, register, value):
        self.bus.write_byte_data(self.address, register, value)

    def initialize(self):
        if self.read_byte(self.CHIP_ID_REG) != self.CHIP_ID:
            raise RuntimeError(
                f"Kein BMI270 an I2C-Adresse 0x{self.address:02X} "
                f"(erwartete Chip-ID 0x{self.CHIP_ID:02X})"
            )

        config = gzip.decompress(base64.b64decode(_CONFIG_GZIP_BASE64))
        if len(config) != 8192:
            raise RuntimeError("Interner Fehler: BMI270-Konfiguration ist unvollständig")

        # Reset und Bosch-Initialisierungssequenz laut Datenblatt.
        self.write_byte(self.CMD, 0xB6)
        time.sleep(0.003)
        self.write_byte(self.PWR_CONF, 0x00)  # Advanced power save aus
        time.sleep(0.001)
        self.write_byte(self.INIT_CTRL, 0x00)

        # Linux SMBus erlaubt maximal 32 Nutzdatenbytes pro Blocktransfer.
        for offset in range(0, len(config), 32):
            init_address = offset // 2
            self.write_byte(self.INIT_ADDR_0, init_address & 0x0F)
            self.write_byte(self.INIT_ADDR_1, (init_address >> 4) & 0xFF)
            self.bus.write_i2c_block_data(
                self.address, self.INIT_DATA, list(config[offset : offset + 32])
            )

        self.write_byte(self.INIT_CTRL, 0x01)

        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:
            if self.read_byte(self.INTERNAL_STATUS) & 0x0F == 0x01:
                break
            time.sleep(0.005)
        else:
            status = self.read_byte(self.INTERNAL_STATUS)
            raise RuntimeError(
                f"BMI270-Initialisierung fehlgeschlagen (INTERNAL_STATUS=0x{status:02X})"
            )

        # Gleiche Messbereiche wie der MPU6050 im vorhandenen mpuAngle.py:
        # Accelerometer ±2 g = 16384 LSB/g
        # Gyroskop ±250 Grad/s = ca. 131.2 LSB/(Grad/s)
        self.write_byte(self.ACC_CONF, 0xA8)   # 100 Hz, Normal/AVG4, Performance
        self.write_byte(self.ACC_RANGE, 0x00)  # ±2 g
        self.write_byte(self.GYR_CONF, 0xE8)   # 100 Hz, Normal, Performance
        self.write_byte(self.GYR_RANGE, 0x03)  # ±250 Grad/s
        self.write_byte(self.PWR_CTRL, 0x0E)   # Temperatur, Gyro und Accel an
        time.sleep(0.06)

    def read_measurement(self):
        raw = self.bus.read_i2c_block_data(self.address, self.DATA_REG, 12)
        accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z = struct.unpack(
            "<hhhhhh", bytes(raw)
        )

        temp_bytes = self.bus.read_i2c_block_data(self.address, self.TEMP_REG, 2)
        temp_raw = struct.unpack("<h", bytes(temp_bytes))[0]
        temperature = 23.0 + (temp_raw / 512.0)

        return accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, temperature


def parse_i2c_address(value):
    try:
        address = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Adresse z. B. als 0x68 angeben") from exc
    if not 0x03 <= address <= 0x77:
        raise argparse.ArgumentTypeError("I2C-Adresse muss zwischen 0x03 und 0x77 liegen")
    return address


def parse_args():
    parser = argparse.ArgumentParser(
        description="BMI270 Data Logger mit MPU6050-kompatibler JSON-Ausgabe"
    )
    parser.add_argument(
        "--time",
        type=float,
        default=1.0,
        help="Zeit zwischen Ausgaben in Sekunden (Standard: 1)",
    )
    parser.add_argument(
        "--bus", type=int, default=1, help="Linux-I2C-Busnummer (Standard: 1)"
    )
    parser.add_argument(
        "--addr",
        type=parse_i2c_address,
        help="I2C-Adresse, z. B. 0x68; ohne Angabe werden 0x68/0x69 gesucht",
    )
    args = parser.parse_args()
    if args.time < 0:
        parser.error("--time darf nicht negativ sein")
    return args


def find_sensor(bus, requested_address=None):
    addresses = [requested_address] if requested_address is not None else [0x68, 0x69]
    for address in addresses:
        try:
            if bus.read_byte_data(address, BMI270.CHIP_ID_REG) == BMI270.CHIP_ID:
                return address
        except OSError:
            pass
    checked = ", ".join(f"0x{address:02X}" for address in addresses)
    raise RuntimeError(f"Kein BMI270 gefunden (geprüft: {checked})")


def calculate_angles(accel_x, accel_y, accel_z):
    # Absichtlich exakt dieselben Formeln wie in mpu_py/mpuAngle.py.
    x_angle = math.atan2(
        accel_y, math.sqrt(accel_x**2 + accel_z**2)
    ) * (180.0 / math.pi)
    y_angle = math.atan2(
        accel_x, math.sqrt(accel_y**2 + accel_z**2)
    ) * (180.0 / math.pi)
    z_angle = math.atan2(
        accel_z, math.sqrt(accel_x**2 + accel_y**2)
    ) * (180.0 / math.pi)
    return x_angle, y_angle, z_angle


def remap_axes(accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z):
    """BMI270-X/Y-Achsen an die Achsrichtungen des MPU6050 anpassen."""
    return -accel_x, -accel_y, accel_z, -gyro_x, -gyro_y, gyro_z


def main():
    args = parse_args()
    bus = None
    try:
        bus = SMBus(args.bus)
        address = find_sensor(bus, args.addr)
        sensor = BMI270(bus, address)
        sensor.initialize()

        while True:
            start_time = time.monotonic()
            (
                accel_x,
                accel_y,
                accel_z,
                gyro_x,
                gyro_y,
                gyro_z,
                temperature,
            ) = sensor.read_measurement()
            (
                accel_x,
                accel_y,
                accel_z,
                gyro_x,
                gyro_y,
                gyro_z,
            ) = remap_axes(
                accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z
            )
            x_angle, y_angle, z_angle = calculate_angles(accel_x, accel_y, accel_z)

            data = {
                "x_angle": x_angle,
                "y_angle": y_angle,
                "z_angle": z_angle,
                "accel_x_raw": accel_x,
                "accel_y_raw": accel_y,
                "accel_z_raw": accel_z,
                "gyro_x_raw": gyro_x,
                "gyro_y_raw": gyro_y,
                "gyro_z_raw": gyro_z,
                "mpu_temp": temperature,
            }
            print(json.dumps(data), flush=True)

            sleep_time = max(0.0, args.time - (time.monotonic() - start_time))
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
    finally:
        if bus is not None:
            bus.close()


if __name__ == "__main__":
    raise SystemExit(main())
