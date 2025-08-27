import smbus
import math
import time
import json
import argparse

# MPU6050 Registers
MPU6050_ADDR = 0x69
MPU6050_PWR_MGMT_1 = 0x6B
MPU6050_TEMP_OUT_H = 0x41
MPU6050_ACCEL_XOUT_H = 0x3B
MPU6050_ACCEL_YOUT_H = 0x3D
MPU6050_ACCEL_ZOUT_H = 0x3F
MPU6050_GYRO_XOUT_H = 0x43
MPU6050_GYRO_YOUT_H = 0x45
MPU6050_GYRO_ZOUT_H = 0x47

# Configuration
bus = smbus.SMBus(1)  # or 0 for RPi 1
bus.write_byte_data(MPU6050_ADDR, MPU6050_PWR_MGMT_1, 0)

def read_raw_data(addr):
    # Read raw data in a single transaction
    high = bus.read_i2c_block_data(MPU6050_ADDR, addr, 2)
    value = (high[0] << 8) | high[1]
    if value > 32768:
        value -= 65536
    return value

def parse_args():
    parser = argparse.ArgumentParser(description="MPU6050 Data Logger")
    parser.add_argument("--time", type=float, default=1, help="Sleep time in seconds (default: 1)")
    return parser.parse_args()

args = parse_args()

while True:
    start_time = time.time()
    
    # Read sensor data
    accel_x, accel_y, accel_z = [read_raw_data(addr) for addr in (MPU6050_ACCEL_XOUT_H, MPU6050_ACCEL_YOUT_H, MPU6050_ACCEL_ZOUT_H)]
    gyro_x, gyro_y, gyro_z = [read_raw_data(addr) for addr in (MPU6050_GYRO_XOUT_H, MPU6050_GYRO_YOUT_H, MPU6050_GYRO_ZOUT_H)]
    temp = read_raw_data(MPU6050_TEMP_OUT_H)
    
    # Calculate angles
    x_angle = math.atan(accel_x / 16384.0) * (180 / math.pi)
    y_angle = math.atan(accel_y / 16384.0) * (180 / math.pi)
    
    # Prepare data dictionary
    data = {
        "x_angle": x_angle,
        "y_angle": y_angle,
        "accel_x_raw": accel_x,
        "accel_y_raw": accel_y,
        "accel_z_raw": accel_z,
        "gyro_x_raw": gyro_x,
        "gyro_y_raw": gyro_y,
        "gyro_z_raw": gyro_z,
        "mpu_temp": (temp / 340.0) + 36.53  # Temperature formula for MPU6050
    }
    
    # Print JSON data
    print(json.dumps(data))
    
    # Adjust sleep time to optimize logging frequency
    sleep_time = max(0, args.time - (time.time() - start_time))
    time.sleep(sleep_time)
