#!/usr/bin/env python3
"""Pekaway Power Unit BLE <-> MQTT bridge with optional Home Assistant MQTT discovery.

Reads measurements, battery and BMS data from the Pekaway Power Unit via Bluetooth LE,
publishes them as JSON via MQTT and executes switching commands with confirmation.
See README.md for the topic and payload reference.

Start (e.g. from a Node-RED exec node in spawn mode):
    python3 -u pu_ble_mqtt.py --address 41:42:XX:XX:XX:XX [--ha-discovery]

MQTT topics (<base> = <topic prefix>/<device id>, e.g. pekaway/power_unit/4142b91c569f):
    <base>/state      full status JSON (schema 1), retained, about once per second
    <base>/ha_state   same JSON for Home Assistant, every --ha-interval seconds
    <base>/health     connection state, retained (offline via last will)
    <base>/cmd        commands (plain text or {"command": "..."})
    <base>/result     command results: sent, confirmed, timeout, superseded or error

BLE connection:
    The Linux default LE supervision timeout of 420 ms disconnects the link on
    short radio dropouts. --le-supervision-timeout (default 5 s) sets the kernel
    default for new connections (debugfs, sudo). Persistent alternative:
    /etc/bluetooth/main.conf, [LE] ConnectionSupervisionTimeout=500.
"""

import argparse
import asyncio
import json
import logging
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time

import paho.mqtt.client as mqtt
from bleak import BleakClient, BleakScanner

__version__ = "1.0.0"
SCHEMA_VERSION = 1

LOG = logging.getLogger("pu_ble_mqtt")

MAX_AGE = 10                   # seconds until measurements are considered stale
PACK_EXPIRY = 60               # seconds until a battery is no longer listed
HEALTH_INTERVAL = 10           # seconds between unchanged health messages
HA_SETTLE = 2                  # seconds of 1 s HA updates after a command was resolved
STATUS_FRAME_LENGTH = 37       # status frame AA 01 incl. checksum
BMS_FRAME_LENGTHS = (24, 22)   # BMS frame AA 03 incl. checksum, with or without an extra word
BUFFER_LIMIT = 512
# Without commands the Power Unit stops sending data after a while,
# so "display sleep off" is sent periodically to keep it active.
KEEPALIVE_COMMAND = "display_sleep_off"
WRITE_TIMEOUT = 5
SCAN_TIMEOUT = 15
STATS_INTERVAL = 60
MIN_ESTIMABLE_CURRENT = 0.05   # A
MAX_ESTIMATED_MINUTES = 14 * 24 * 60

# Command name -> (byte index, bit) in the command frame AA 02.
COMMAND_BITS = {
    "ac_output_on": (2, 0), "ac_output_off": (2, 1),
    "mains_charge_high_on": (2, 2), "mains_charge_high_off": (2, 3),
    "reverse_charge_on": (2, 4), "reverse_charge_off": (2, 5),
    "display_sleep_on": (2, 6), "display_sleep_off": (2, 7),
    "car_charge_high": (3, 0), "car_charge_low": (3, 1),
    "buzzer_on": (3, 2), "buzzer_off": (3, 3),
}
# Status field and target value that confirm a command.
COMMAND_STATE = {
    "ac_output_on": ("ac_output_on", True), "ac_output_off": ("ac_output_on", False),
    "mains_charge_high_on": ("mains_charge_low_power", False),
    "mains_charge_high_off": ("mains_charge_low_power", True),
    "reverse_charge_on": ("reverse_charge_on", True), "reverse_charge_off": ("reverse_charge_on", False),
    "display_sleep_on": ("display_sleep_enabled", True), "display_sleep_off": ("display_sleep_enabled", False),
    "car_charge_high": ("car_charge_low_power", False), "car_charge_low": ("car_charge_low_power", True),
    "buzzer_on": ("buzzer_enabled", True), "buzzer_off": ("buzzer_enabled", False),
}
# Power Unit protection and fault flags: status field, JSON key, alert text.
PROTECTION_FLAGS = (
    ("ac_output_overtemp", "inverter_overtemp", "Inverter overtemperature"),
    ("ac_output_overload", "inverter_overload", "Inverter overload"),
    ("ac_output_short", "inverter_short_circuit", "Inverter short circuit"),
    ("mains_charge_overtemp", "ac_charge_overtemp", "AC charge overtemperature"),
    ("charge_overtemp", "charge_path_overtemp", "Charge path overtemperature"),
    ("battery_ov_protection", "battery_overvoltage_protection", "Battery high-voltage protection"),
    ("battery_uv_warning", "battery_undervoltage_warning", "Battery low-voltage warning"),
    ("battery_uv_protection", "battery_undervoltage_protection", "Battery low-voltage protection"),
    ("pv_input_overvoltage", "pv_input_overvoltage", "PV input overvoltage"),
    ("pv_input_undervoltage", "pv_input_undervoltage", "PV input undervoltage"),
    ("pv_output_overvoltage", "pv_output_overvoltage", "PV output overvoltage"),
    ("ac_start_voltage_low", "ac_start_voltage_low", "AC startup voltage too low"),
    ("pv_overtemp", "pv_overtemp", "PV overtemperature"),
)


# ---------------------------------------------------------------------------
# BLE protocol
# ---------------------------------------------------------------------------

def checksum(data):
    return sum(data) & 0xFF


def u16(high, low):
    return (high << 8) | low


def bit(value, number):
    return bool(value & (1 << number))


def bits(value, start, width):
    return (value >> start) & ((1 << width) - 1)


def tenths(raw):
    # raw * 0.1 leaves floating point residue (459 * 0.1 = 45.900000000000006).
    return round(raw / 10, 1)


def command_packet(command):
    byte_index, bit_number = COMMAND_BITS[command]
    packet = bytearray([0xAA, 0x02, 0x00, 0x00])
    packet[byte_index] = 1 << bit_number
    packet.append(checksum(packet))
    return bytes(packet)


STATUS_BITS = (
    (2, (("battery_uv_warning", 0), ("battery_uv_protection", 1), ("fan_on", 2),
         ("car_charge_on", 3), ("reverse_charge_on", 4), ("charge_overtemp", 5),
         ("pv_charging_on", 6), ("pv_overtemp", 7))),
    (3, (("ac_output_on", 0), ("frequency_50hz", 1), ("ac_output_overtemp", 2),
         ("ac_output_short", 3), ("ac_output_overload", 4), ("mains_charge_overtemp", 5),
         ("battery_ov_protection", 7))),
    (4, (("ac_start_voltage_low", 0), ("pv_output_overvoltage", 1),
         ("pv_input_overvoltage", 2), ("pv_input_undervoltage", 3),
         ("mains_charge_low_power", 5), ("car_charge_low_power", 6), ("mains_charge_on", 7))),
)
# key, index of the high byte, value in tenths?
STATUS_MEASUREMENTS = (
    ("ac_voltage", 5, True), ("ac_power", 7, False), ("battery_48v", 9, True),
    ("battery_soc", 11, False), ("battery_12v", 13, True), ("car_or_reverse_power", 15, False),
    ("pv_charge_power", 17, False), ("mains_charge_power", 19, False),
    ("pv_input_voltage", 27, True),
)


def decode_status(packet):
    """AA 01 / 37 bytes -> {key: value}."""
    values = {}
    for index, definitions in STATUS_BITS:
        for key, number in definitions:
            values[key] = bit(packet[index], number)
    for key, high, scaled in STATUS_MEASUREMENTS:
        raw = u16(packet[high], packet[high + 1])
        values[key] = tenths(raw) if scaled else raw
    raw_time = u16(packet[25], packet[26])
    # The top bit of byte 26 is a direction flag, not part of the minutes.
    values["remaining_time"] = raw_time & 0x7FFF
    values["remaining_time_usage"] = bit(packet[25], 7)
    values["battery_temperature"] = u16(packet[33], packet[34]) - 40
    values["buzzer_enabled"] = bit(packet[35], 1)
    values["display_sleep_enabled"] = bit(packet[35], 2)
    values["parallel_battery_count"] = bits(packet[35], 3, 3)
    return values


# BMS word, byte, start bit, width, name, kind (level = warning level 0-7,
# fault = protection/fault, state = information).
BMS_BITS = (
    (2, "low", 0, 3, "cell_overvoltage", "level"), (2, "low", 3, 3, "cell_undervoltage", "level"),
    (2, "low", 6, 1, "smart_charger_connected", "state"), (2, "low", 7, 1, "smart_charger_failed", "fault"),
    (2, "high", 0, 3, "voltage_delta", "level"), (2, "high", 3, 3, "charge_overtemp", "level"),
    (2, "high", 6, 1, "smart_discharger_connected", "state"),
    (2, "high", 7, 1, "smart_discharger_failed", "fault"),
    (3, "low", 0, 3, "charge_lowtemp", "level"), (3, "low", 3, 3, "discharge_overtemp", "level"),
    (3, "low", 6, 1, "charge_mos_overtemp", "fault"), (3, "low", 7, 1, "charge_mos_sensor_fault", "fault"),
    (3, "high", 0, 3, "discharge_lowtemp", "level"), (3, "high", 3, 3, "temperature_delta", "level"),
    (3, "high", 6, 1, "discharge_mos_overtemp", "fault"),
    (3, "high", 7, 1, "discharge_mos_sensor_fault", "fault"),
    (4, "low", 0, 3, "total_voltage_high", "level"), (4, "low", 3, 3, "total_voltage_low", "level"),
    (4, "low", 6, 1, "short_circuit_protection", "fault"),
    (4, "high", 0, 3, "charge_overcurrent", "level"), (4, "high", 3, 3, "discharge_overcurrent", "level"),
    (4, "high", 6, 1, "low_voltage_charge_block", "fault"),
    (4, "high", 7, 1, "high_voltage_discharge_block", "fault"),
    (5, "low", 0, 3, "soc_low", "level"), (5, "low", 3, 3, "soh_low", "level"),
    (5, "high", 0, 3, "mos_overtemp", "level"), (5, "high", 3, 3, "thermal_runaway", "level"),
) + tuple((7, "high", n, 1, name, "fault") for n, name in enumerate((
    "afe_chip_fault", "afe_communication_fault", "afe_sampling_fault", "voltage_detection_fault",
    "voltage_sense_wire_disconnected", "total_voltage_measurement_fault",
    "current_measurement_fault", "temperature_measurement_fault"))
) + tuple((8, "low", n, 1, name, "fault") for n, name in enumerate((
    "temperature_sense_wire_disconnected", "eeprom_fault", "flash_fault", "rtc_fault",
    "charge_mos_fault", "discharge_mos_fault", "precharge_mos_fault", "precharge_failed"))
) + tuple((8, "high", n, 1, name, "fault" if name == "heating_fault" else "state") for n, name in enumerate((
    "command_charge_mos_off", "command_discharge_mos_off", "switch_charge_mos_off",
    "switch_discharge_mos_off", "fan_operating", "heating_operating", "current_limit_operating",
    "heating_fault"))
)


def decode_bms(packet):
    """AA 03 / 22 or 24 bytes -> battery ID, bank current, remaining capacity, BMS states."""
    raw_current = u16(packet[2], packet[3])
    # The 24-byte frame has an additional word before the BMS words.
    word_start = 9 if len(packet) == 24 else 7
    words = {number: (packet[index], packet[index + 1])
             for number, index in zip(range(2, 9), range(word_start, word_start + 14, 2))}
    levels, faults, states = {}, {}, {}
    for word, byte_name, start, width, name, kind in BMS_BITS:
        high, low = words[word]
        value = bits(low if byte_name == "low" else high, start, width)
        {"level": levels, "fault": faults, "state": states}[kind][name] = value if width > 1 else bool(value)
    return {
        "battery_id": packet[6],
        # A raw value of 0 appears sporadically and would mean -3000 A: invalid.
        "current": None if raw_current == 0 else tenths(raw_current - 30000),
        "remaining_capacity_ah": tenths(u16(packet[4], packet[5])),
        "levels": levels, "faults": faults, "states": states,
    }


def extract_packet(buffer):
    """Remove and return the next valid frame from the bytearray, or None."""
    while len(buffer) >= 2:
        if buffer[0] != 0xAA or buffer[1] not in (0x01, 0x03):
            del buffer[0]
            continue
        lengths = (STATUS_FRAME_LENGTH,) if buffer[1] == 0x01 else BMS_FRAME_LENGTHS
        # Only check once the longest variant is complete. Otherwise a
        # fragmented 24-byte BMS frame would be dropped at 22/23 bytes.
        if len(buffer) < max(lengths):
            return None
        for length in lengths:
            if checksum(buffer[:length - 1]) == buffer[length - 1]:
                packet = bytes(buffer[:length])
                del buffer[:length]
                return packet
        del buffer[0]
    return None


# ---------------------------------------------------------------------------
# Status JSON (schema 1)
# ---------------------------------------------------------------------------

def safe_current(power, voltage):
    return round(power / voltage, 2) if voltage else None


def remaining_time(status, current, smoothed_current, capacity):
    """Remaining time reported by the device, otherwise estimated from BMS data."""
    if status["remaining_time"] > 0:
        return {"minutes": status["remaining_time"],
                "mode": "use" if status["remaining_time_usage"] else "charge", "estimated": False}
    if current is None or abs(current) < MIN_ESTIMABLE_CURRENT:
        return {"minutes": 0, "mode": "unknown", "estimated": False}
    rate = smoothed_current if smoothed_current is not None and abs(smoothed_current) >= MIN_ESTIMABLE_CURRENT else current
    soc = status["battery_soc"]
    if capacity and capacity > 0 and 1 <= soc <= 100:
        nominal = capacity / (soc / 100)
        if capacity <= nominal <= 1000:
            hours = (nominal - capacity) / rate if rate > 0 else capacity / abs(rate)
            return {"minutes": max(0, min(MAX_ESTIMATED_MINUTES, round(hours * 60))),
                    "mode": "charge" if rate > 0 else "use", "estimated": True}
    return {"minutes": 0, "mode": "charge" if rate > 0 else "use", "estimated": False}


def label(name):
    return name.replace("_", " ")


def make_status(snapshot, device_id, now=None):
    """Status JSON (schema 1), or None if there is no current data."""
    now = time.time() if now is None else now
    status = snapshot.get("status")
    if not snapshot.get("connected") or not status or not 0 <= now - status["timestamp"] <= MAX_AGE:
        return None
    # Pending commands: show the target value until the device confirms it or the
    # confirmation times out, so switches do not jump back in between.
    pending = snapshot.get("pending") or {}
    s = {**status["values"], **{field: entry["target"] for field, entry in pending.items()}}

    last_bms = snapshot.get("last_bms")
    bms_fresh = last_bms is not None and 0 <= now - last_bms["timestamp"] <= MAX_AGE
    current_at, current = snapshot.get("current") or (None, None)
    if current_at is None or not 0 <= now - current_at <= MAX_AGE:
        current = None
    capacity = last_bms["values"]["remaining_capacity_ah"] if bms_fresh else None
    battery_power = round(current * s["battery_48v"], 1) if current is not None else None

    alerts = [text for key, _, text in PROTECTION_FLAGS if s[key]]
    batteries = []
    for battery_id, report in sorted((snapshot.get("packs") or {}).items()):
        age = now - report["timestamp"]
        if not 0 <= age <= PACK_EXPIRY:
            continue
        b = report["values"]
        warnings = {name: level for name, level in b["levels"].items() if level}
        faults = [name for name, active in b["faults"].items() if active]
        batteries.append({
            "id": battery_id, "age": round(age, 1), "fresh": age <= MAX_AGE,
            # Current and remaining capacity from this battery's frame refer to the whole bank.
            "current": b["current"], "remaining_capacity_ah": b["remaining_capacity_ah"],
            "warnings": warnings, "faults": faults,
            "states": [name for name, active in b["states"].items() if active],
        })
        alerts += [f"Battery {battery_id}: {label(name)} level {level}" for name, level in warnings.items()]
        alerts += [f"Battery {battery_id}: {label(name)}" for name in faults]

    return {
        "schema": SCHEMA_VERSION,
        "device_id": device_id,
        "timestamp": status["timestamp"],
        "battery": {"voltage": s["battery_48v"], "soc": s["battery_soc"], "current": current,
                    "power": battery_power, "charging": battery_power is not None and battery_power > 0,
                    "remaining_capacity_ah": capacity, "temperature": s["battery_temperature"],
                    "count": s["parallel_battery_count"],
                    "reporting": sum(1 for b in batteries if b["fresh"])},
        "starter_battery": {"voltage": s["battery_12v"]},
        "pv": {"power": s["pv_charge_power"], "voltage": s["pv_input_voltage"],
               "current": safe_current(s["pv_charge_power"], s["pv_input_voltage"]),
               "charging": s["pv_charging_on"]},
        "shore": {"power": s["mains_charge_power"], "charging": s["mains_charge_on"],
                  "high_power": not s["mains_charge_low_power"]},
        # mode: forward = charging from the alternator, reverse = charging the
        # starter battery from the house battery. power is always positive.
        "alternator": {"power": s["car_or_reverse_power"], "high_power": not s["car_charge_low_power"],
                       "charging": s["car_charge_on"], "reverse_charging": s["reverse_charge_on"],
                       "mode": {(True, False): "forward", (False, True): "reverse",
                                (False, False): "inactive"}.get((s["car_charge_on"], s["reverse_charge_on"]), "unknown")},
        "ac_output": {"enabled": s["ac_output_on"], "power": s["ac_power"], "voltage": s["ac_voltage"],
                      "current": safe_current(s["ac_power"], s["ac_voltage"]),
                      "frequency": 50 if s["frequency_50hz"] else 60},
        "remaining_time": remaining_time(s, current, snapshot.get("current_smoothed"), capacity),
        "batteries": batteries,
        "protection": {key: s[protocol_key] for protocol_key, key, _ in PROTECTION_FLAGS},
        "device": {"fan_on": s["fan_on"], "buzzer_enabled": s["buzzer_enabled"],
                   "display_sleep_enabled": s["display_sleep_enabled"]},
        "alerts": alerts,
        "pending": sorted(entry["command"] for entry in pending.values()),
    }


# ---------------------------------------------------------------------------
# Topics and Home Assistant discovery
# ---------------------------------------------------------------------------

# Advertisement features of a Power Unit: GATT service, service data or device name.
POWER_UNIT_SERVICES = ("0000ffe0-0000-1000-8000-00805f9b34fb", "0000ffe1-0000-1000-8000-00805f9b34fb")
POWER_UNIT_SERVICE_DATA = ("0000ffe0-0000-1000-8000-00805f9b34fb", "0000e0ff-0000-1000-8000-00805f9b34fb")
POWER_UNIT_NAMES = ("power unit", "powerunit")


def is_power_unit(name, service_uuids, service_data_uuids):
    name = (name or "").lower()
    return (any(uuid.lower() in POWER_UNIT_SERVICES for uuid in service_uuids)
            or any(uuid.lower() in POWER_UNIT_SERVICE_DATA for uuid in service_data_uuids)
            or any(part in name for part in POWER_UNIT_NAMES))


async def scan_power_units(adapter, seconds):
    """Power Units in range, strongest signal first. A connected Power Unit does not advertise.
    The advertised device name is used for detection only and never returned."""
    found = await BleakScanner.discover(timeout=seconds, return_adv=True, adapter=adapter)
    devices = [{"address": device.address.upper(), "rssi": advertisement.rssi}
               for device, advertisement in found.values()
               if is_power_unit(advertisement.local_name or device.name, advertisement.service_uuids,
                                advertisement.service_data.keys())]
    return sorted(devices, key=lambda device: -device["rssi"])


def device_id_from_address(address):
    return re.sub(r"[^0-9a-f]", "", address.lower())


class Topics:
    def __init__(self, prefix, device_id):
        base = f"{prefix.strip('/')}/{device_id}"
        self.state = f"{base}/state"
        self.ha_state = f"{base}/ha_state"
        self.health = f"{base}/health"
        self.cmd = f"{base}/cmd"
        self.result = f"{base}/result"


def ha_discovery(topics, device_id, address, ha_prefix):
    """Home Assistant MQTT discovery messages: [(topic, config)]."""
    node = f"pekaway_pu_{device_id}"
    device = {"identifiers": [node], "name": "Pekaway Power Unit", "manufacturer": "Pekaway",
              "model": "Power Unit", "sw_version": __version__, "serial_number": address.upper()}
    origin = {"name": "pekaway-pu-ble-mqtt", "sw_version": __version__}
    available = [{"topic": topics.health, "value_template": "{{ 'online' if value_json.connected else 'offline' }}"}]

    def sensor(key, name, template, unit=None, device_class=None, state_class="measurement", **extra):
        config = {"name": name, "state_topic": topics.ha_state, "value_template": template}
        if unit:
            config["unit_of_measurement"] = unit
        if device_class:
            config["device_class"] = device_class
        if state_class:
            config["state_class"] = state_class
        return "sensor", key, {**config, **extra}

    def switch(key, name, command, template, **extra):
        return "switch", key, {"name": name, "state_topic": topics.ha_state, "value_template": template,
                               "command_topic": topics.cmd, "payload_on": f"{command}_on",
                               "payload_off": f"{command}_off", "state_on": "ON", "state_off": "OFF", **extra}

    def high_low(key, name, high, low, template):
        return "select", key, {"name": name, "state_topic": topics.ha_state, "value_template": template,
                               "command_topic": topics.cmd, "options": ["High", "Low"],
                               "command_template": f"{{{{ '{high}' if value == 'High' else '{low}' }}}}"}

    entities = [
        sensor("battery_soc", "Battery SOC", "{{ value_json.battery.soc }}", "%", "battery"),
        sensor("battery_voltage", "Battery voltage", "{{ value_json.battery.voltage }}", "V", "voltage"),
        sensor("battery_current", "Battery current", "{{ value_json.battery.current }}", "A", "current"),
        sensor("battery_power", "Battery power", "{{ value_json.battery.power }}", "W", "power"),
        sensor("battery_temperature", "Battery temperature", "{{ value_json.battery.temperature }}", "°C", "temperature"),
        sensor("battery_remaining_capacity", "Battery remaining capacity",
               "{{ value_json.battery.remaining_capacity_ah }}", "Ah", icon="mdi:battery-clock"),
        sensor("remaining_time", "Remaining time", "{{ value_json.remaining_time.minutes }}", "min", "duration",
               json_attributes_topic=topics.ha_state,
               json_attributes_template="{{ value_json.remaining_time | tojson }}"),
        sensor("starter_battery_voltage", "Starter battery voltage", "{{ value_json.starter_battery.voltage }}",
               "V", "voltage"),
        sensor("pv_power", "Solar power", "{{ value_json.pv.power }}", "W", "power"),
        sensor("pv_voltage", "Solar voltage", "{{ value_json.pv.voltage }}", "V", "voltage"),
        sensor("shore_power", "Shore power", "{{ value_json.shore.power }}", "W", "power"),
        sensor("alternator_power", "Alternator power", "{{ value_json.alternator.power }}", "W", "power"),
        sensor("alternator_mode", "Alternator mode", "{{ value_json.alternator.mode }}", device_class="enum",
               state_class=None, options=["forward", "reverse", "inactive", "unknown"]),
        sensor("ac_output_power", "AC output power", "{{ value_json.ac_output.power }}", "W", "power"),
        sensor("ac_output_voltage", "AC output voltage", "{{ value_json.ac_output.voltage }}", "V", "voltage"),
        sensor("alerts", "Alerts", "{{ value_json.alerts | count }}", icon="mdi:alert",
               json_attributes_topic=topics.ha_state,
               json_attributes_template="{{ {'alerts': value_json.alerts} | tojson }}"),
        sensor("batteries_reporting", "Batteries reporting", "{{ value_json.battery.reporting }}",
               entity_category="diagnostic", icon="mdi:battery-sync"),
        ("binary_sensor", "problem", {"name": "Problem", "state_topic": topics.ha_state, "device_class": "problem",
                                      "value_template": "{{ 'ON' if value_json.alerts | count > 0 else 'OFF' }}"}),
        ("binary_sensor", "battery_charging", {"name": "Battery charging", "state_topic": topics.ha_state,
                                               "device_class": "battery_charging",
                                               "value_template": "{{ 'ON' if value_json.battery.charging else 'OFF' }}"}),
        switch("inverter", "Inverter", "ac_output", "{{ 'ON' if value_json.ac_output.enabled else 'OFF' }}",
               icon="mdi:power-socket-eu"),
        # The Power Unit manages reverse charging itself (above 30 % SoC); the switch forces or
        # releases it and shows whether reverse charging is active.
        switch("reverse_charge", "Force reverse charging", "reverse_charge",
               "{{ 'ON' if value_json.alternator.reverse_charging else 'OFF' }}", icon="mdi:car-battery"),
        switch("buzzer", "Buzzer", "buzzer", "{{ 'ON' if value_json.device.buzzer_enabled else 'OFF' }}",
               entity_category="config", icon="mdi:volume-high"),
        high_low("shore_charge_power", "Shore charging power", "mains_charge_high_on", "mains_charge_high_off",
                 "{{ 'High' if value_json.shore.high_power else 'Low' }}"),
        high_low("alternator_charge_power", "Alternator charging power", "car_charge_high", "car_charge_low",
                 "{{ 'High' if value_json.alternator.high_power else 'Low' }}"),
    ]
    messages = []
    for component, key, config in entities:
        config.update(unique_id=f"{node}_{key}", device=device, origin=origin, availability=available)
        messages.append((f"{ha_prefix}/{component}/{node}/{key}/config", config))
    # Connection state and RSSI stay available when the Power Unit is offline.
    for component, key, config in (
        ("binary_sensor", "connection", {"name": "Connection", "device_class": "connectivity",
                                         "value_template": "{{ 'ON' if value_json.connected else 'OFF' }}"}),
        ("sensor", "rssi", {"name": "Signal strength", "device_class": "signal_strength", "unit_of_measurement": "dBm",
                            "state_class": "measurement", "value_template": "{{ value_json.rssi }}"}),
    ):
        config.update(state_topic=topics.health, entity_category="diagnostic", unique_id=f"{node}_{key}",
                      device=device, origin=origin)
        messages.append((f"{ha_prefix}/{component}/{node}/{key}/config", config))
    return messages


# ---------------------------------------------------------------------------
# Linux BLE parameters and HCI diagnostics
# ---------------------------------------------------------------------------

def debugfs_path(adapter, name):
    return f"/sys/kernel/debug/bluetooth/{adapter}/{name}"


def read_le_defaults(adapter):
    """Kernel defaults for new LE connections (debugfs, requires sudo)."""
    values = {}
    for name in ("supervision_timeout", "conn_min_interval", "conn_max_interval", "conn_latency"):
        result = subprocess.run(["sudo", "-n", "cat", debugfs_path(adapter, name)],
                                capture_output=True, text=True, timeout=5, check=False)
        if result.returncode == 0 and result.stdout.strip().isdigit():
            values[name] = int(result.stdout.strip())
    return values


def describe_le_defaults(values):
    if not values:
        return "unknown"
    parts = []
    if "conn_min_interval" in values and "conn_max_interval" in values:
        parts.append(f"interval {values['conn_min_interval'] * 1.25:g}-{values['conn_max_interval'] * 1.25:g} ms")
    if "conn_latency" in values:
        parts.append(f"latency {values['conn_latency']}")
    if "supervision_timeout" in values:
        parts.append(f"supervision timeout {values['supervision_timeout'] * 10} ms")
    return ", ".join(parts)


def configure_le_supervision_timeout(adapter, timeout_ms):
    """Set the default LE supervision timeout for new connections."""
    before = read_le_defaults(adapter)
    LOG.info("LE defaults on %s: %s", adapter, describe_le_defaults(before))
    if timeout_ms <= 0:
        return
    target = max(10, min(3200, round(timeout_ms / 10)))   # units of 10 ms, allowed 100 ms - 32 s
    if before.get("supervision_timeout") == target:
        return
    result = subprocess.run(["sudo", "-n", "tee", debugfs_path(adapter, "supervision_timeout")],
                            input=str(target), capture_output=True, text=True, timeout=5, check=False)
    if result.returncode == 0:
        LOG.info("LE supervision timeout set to %d ms for new connections (was %s)", target * 10,
                 f"{before['supervision_timeout'] * 10} ms" if "supervision_timeout" in before else "unknown")
    else:
        LOG.warning("Could not set LE supervision timeout (%s). Set ConnectionSupervisionTimeout=%d "
                    "in [LE] of /etc/bluetooth/main.conf instead.", result.stderr.strip() or "sudo/debugfs", target)


class HciEventFilter:
    """Filters btmon output down to connection setup, parameters and disconnect reason."""
    EVENTS = re.compile(r"Disconnect Complete|LE (Enhanced )?Connection Complete|LE Connection Update"
                        r"|Connection Parameter Update|Remote Connection Parameter Request")
    FIELDS = re.compile(r"^\s*(Status|Reason|Peer address|Connection interval|Connection latency"
                        r"|Supervision timeout|Min connection interval|Max connection interval"
                        r"|Slave latency|Peripheral latency|Timeout multiplier|Result):", re.I)

    def __init__(self):
        self.capture = False

    def feed(self, line):
        line = line.rstrip()
        if not line:
            return None
        if not line[0].isspace():
            # New HCI event; strip the counter/timestamp at the end of the line.
            self.capture = bool(self.EVENTS.search(line))
            return re.sub(r"\s{2,}#\d+.*$", "", line) if self.capture else None
        if self.EVENTS.search(line):
            # L2CAP signalling is printed indented inside an ACL packet.
            self.capture = True
            return line.strip()
        if self.capture and self.FIELDS.match(line):
            return "  " + line.strip()
        return None


# ---------------------------------------------------------------------------
# BLE
# ---------------------------------------------------------------------------

class Bridge:
    def __init__(self, address, char_uuid, frame_timeout, keepalive=4.0, log_frames=False,
                 adapter="hci0", hci_monitor=False, confirm_timeout=10.0):
        self.address = address
        self.char_uuid = char_uuid
        self.frame_timeout = frame_timeout
        self.keepalive = keepalive
        self.confirm_timeout = confirm_timeout
        self.pending = {}              # status field -> pending command
        self.command_events = []       # (command, status, details) for the result topic
        self.log_frames = log_frames
        self.adapter = adapter
        self.hci_monitor = hci_monitor
        self.lock = threading.Lock()
        self.buffer = bytearray()
        self.connected = False
        self.last_error = "No frame received yet"
        self.reset_data()
        self.loop = None
        self.client = None
        self.write_lock = None
        self.commands_waiting = 0
        self.last_write = 0.0
        self.last_frame = 0.0
        self.disconnect_reason = None
        self.stop_requested = threading.Event()
        self.metrics = {"rx": 0, "tx": 0, "keepalives": 0, "frames": 0, "reconnects": 0,
                        "write_errors": 0, "session_disconnects": 0, "watchdog_resets": 0}
        self.session_id = 0
        self.session_started = 0
        self.rssi = None

    def reset_data(self):
        self.status = None
        self.packs = {}
        self.last_bms = None
        self.battery_count = 0
        self.current = None
        self.current_smoothed = None
        self.stats = {"status_frames": 0, "bms_frames": 0, "max_gap": 0.0, "keepalives": 0,
                      "commands": 0, "write_errors": 0}

    def snapshot(self):
        with self.lock:
            return {"connected": self.connected, "last_error": self.last_error,
                    "status": self.status, "packs": dict(self.packs), "last_bms": self.last_bms,
                    "current": self.current, "current_smoothed": self.current_smoothed,
                    "metrics": dict(self.metrics), "session_id": self.session_id,
                    "session_started": self.session_started, "rssi": self.rssi,
                    "pending": dict(self.pending)}

    def command_sent(self, command, now=None):
        """Track a written command until a later status frame confirms the target value."""
        field, target = COMMAND_STATE[command]
        now = time.time() if now is None else now
        with self.lock:
            previous = self.pending.get(field)
            if previous:
                self.command_events.append((previous["command"], "superseded", {}))
            self.pending[field] = {"command": command, "target": target, "sent_at": now,
                                   "deadline": now + self.confirm_timeout}

    def confirm_commands(self, values, now):
        """Called with the lock held for every status frame."""
        for field, entry in list(self.pending.items()):
            # Only a frame received after the write counts.
            if now > entry["sent_at"] and values[field] == entry["target"]:
                self.command_events.append((entry["command"], "confirmed",
                                            {"duration": round(now - entry["sent_at"], 1)}))
                del self.pending[field]

    def take_command_events(self, now=None):
        """Confirmations and timeouts since the last call."""
        now = time.time() if now is None else now
        with self.lock:
            for field, entry in list(self.pending.items()):
                if now >= entry["deadline"]:
                    self.command_events.append((entry["command"], "timeout", {"timeout": self.confirm_timeout}))
                    del self.pending[field]
            events, self.command_events = self.command_events, []
        return events

    def store(self, packet, now=None):
        now = time.time() if now is None else now
        with self.lock:
            self.last_error = ""
            self.metrics["frames"] += 1
            if packet[1] == 0x01:
                values = decode_status(packet)
                count = values["parallel_battery_count"]
                if count:
                    if self.battery_count > count:
                        # The protocol does not say which battery is missing: relearn.
                        self.packs.clear()
                        self.last_bms = None
                    self.battery_count = count
                if self.status:
                    self.stats["max_gap"] = max(self.stats["max_gap"], now - self.status["timestamp"])
                self.stats["status_frames"] += 1
                self.status = {"timestamp": now, "values": values}
                self.last_frame = now
                self.confirm_commands(values, now)
            else:
                values = decode_bms(packet)
                report = {"timestamp": now, "values": values}
                self.packs[values["battery_id"]] = report
                self.last_bms = report
                self.stats["bms_frames"] += 1
                current = values["current"]
                if current is not None:
                    self.current = (now, current)
                    previous = self.current_smoothed
                    self.current_smoothed = current if previous is None else round(previous * .8 + current * .2, 3)

    def on_notify(self, _sender, data):
        if self.log_frames:
            LOG.debug("RX %s", bytes(data).hex(" ").upper())
        with self.lock:
            self.metrics["rx"] += 1
        self.buffer.extend(data)
        if len(self.buffer) > BUFFER_LIMIT:
            del self.buffer[:-BUFFER_LIMIT]
        while (packet := extract_packet(self.buffer)) is not None:
            self.store(packet)

    def on_disconnected(self, _client):
        if not self.stop_requested.is_set() and self.disconnect_reason is None:
            self.disconnect_reason = "link lost (device or radio)"
            LOG.warning("BLE link lost (Power Unit disconnected or radio supervision timeout)")

    async def write_command(self, command, keepalive=False):
        """All writes are serialised through write_lock."""
        packet = command_packet(command)
        async with self.write_lock:
            client = self.client
            if client is None or not client.is_connected:
                raise RuntimeError("BLE not connected")
            started = time.monotonic()
            try:
                await asyncio.wait_for(client.write_gatt_char(self.char_uuid, packet, response=True),
                                       WRITE_TIMEOUT)
            except Exception:
                with self.lock:
                    self.metrics["write_errors"] += 1
                    self.stats["write_errors"] += 1
                raise
            finally:
                # A command also postpones the next keepalive.
                self.last_write = time.monotonic()
        if self.log_frames:
            LOG.debug("TX %s (%s, %.0f ms)", packet.hex(" ").upper(), command,
                      (self.last_write - started) * 1000)
        with self.lock:
            self.metrics["keepalives" if keepalive else "tx"] += 1
            self.stats["keepalives" if keepalive else "commands"] += 1
        return packet.hex().upper()

    async def send_command_async(self, command):
        if command not in COMMAND_BITS:
            raise ValueError("Unknown command")
        # No keepalive is started while a command is waiting.
        self.commands_waiting += 1
        try:
            started = time.time()
            packet = await self.write_command(command)
            self.command_sent(command, started)
            return packet
        finally:
            self.commands_waiting -= 1

    def send_command(self, command):
        """Callable from another thread (MQTT worker)."""
        if self.loop is None:
            raise RuntimeError("BLE loop not running")
        future = asyncio.run_coroutine_threadsafe(self.send_command_async(command), self.loop)
        try:
            return future.result(timeout=WRITE_TIMEOUT * 2 + 1)
        except TimeoutError:
            future.cancel()
            raise

    async def keepalive_loop(self):
        """Send a keepalive only when no command is waiting and the interval has
        passed since the last write. A running keepalive delays a command by
        at most one write."""
        while True:
            await asyncio.sleep(0.1)
            if self.commands_waiting or time.monotonic() - self.last_write < self.keepalive:
                continue
            try:
                await self.write_command(KEEPALIVE_COMMAND, keepalive=True)
            except Exception as exc:
                LOG.warning("Keepalive failed: %s", str(exc) or type(exc).__name__)

    async def stats_loop(self):
        """One line per minute for connection diagnostics."""
        while True:
            await asyncio.sleep(STATS_INTERVAL)
            with self.lock:
                stats = dict(self.stats)
                self.stats.update(status_frames=0, bms_frames=0, max_gap=0.0, keepalives=0,
                                  commands=0, write_errors=0)
                uptime = time.time() - self.session_started
            LOG.info("Link session %d up %.0f s: %d status / %d BMS frames, max status gap %.1f s, "
                     "%d keepalives, %d commands, %d write errors (last %d s)",
                     self.session_id, uptime, stats["status_frames"], stats["bms_frames"],
                     stats["max_gap"], stats["keepalives"], stats["commands"], stats["write_errors"],
                     STATS_INTERVAL)

    async def hci_monitor_loop(self):
        """Follow btmon: log connection parameters and HCI disconnect reasons."""
        try:
            process = await asyncio.create_subprocess_exec(
                "sudo", "-n", "btmon", "-i", self.adapter,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        except Exception as exc:
            LOG.warning("HCI monitor not available: %s", exc)
            return
        LOG.info("HCI monitor started (btmon)")
        event_filter = HciEventFilter()
        try:
            while True:
                line = await process.stdout.readline()
                if not line:
                    LOG.warning("HCI monitor stopped (btmon exit code %s)", await process.wait())
                    return
                text = event_filter.feed(line.decode("utf-8", "replace"))
                if text:
                    LOG.info("HCI %s", text)
        finally:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), 3)
                except asyncio.TimeoutError:
                    process.kill()

    async def bluetoothctl_disconnect(self):
        """Drop a stale BlueZ connection before/after owning the BLE session."""
        try:
            await asyncio.to_thread(subprocess.run, ["bluetoothctl", "disconnect", self.address],
                                    capture_output=True, text=True, timeout=10, check=False)
        except Exception:
            pass

    async def find_device(self):
        """Find the device by scanning; log RSSI for diagnostics."""
        found = {}

        def match(device, advertisement):
            if device.address.upper() != self.address.upper():
                return False
            found["rssi"] = advertisement.rssi
            return True

        device = await BleakScanner.find_device_by_filter(match, timeout=SCAN_TIMEOUT, adapter=self.adapter)
        if device is None:
            raise RuntimeError(f"Power Unit {self.address} not found during {SCAN_TIMEOUT} s scan")
        with self.lock:
            self.rssi = found.get("rssi")
        return device

    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.write_lock = asyncio.Lock()
        monitor = asyncio.create_task(self.hci_monitor_loop()) if self.hci_monitor else None
        await self.bluetoothctl_disconnect()
        while not self.stop_requested.is_set():
            tasks = []
            self.disconnect_reason = None
            try:
                LOG.info("Scanning for %s ...", self.address)
                device = await self.find_device()
                LOG.info("Found %s (RSSI %s dBm), connecting ...", self.address, self.rssi)
                async with BleakClient(device, disconnected_callback=self.on_disconnected,
                                       adapter=self.adapter) as client:
                    self.client = client
                    try:
                        with self.lock:
                            self.connected = True
                            self.reset_data()
                            self.buffer.clear()
                            self.session_id += 1
                            self.session_started = time.time()
                            self.metrics["reconnects"] = self.session_id - 1
                        self.last_frame = time.time()
                        self.last_write = 0.0   # keepalive right after connecting
                        await client.start_notify(self.char_uuid, self.on_notify)
                        if self.keepalive > 0:
                            tasks.append(asyncio.create_task(self.keepalive_loop()))
                        tasks.append(asyncio.create_task(self.stats_loop()))
                        LOG.info("BLE connected (session %d)", self.session_id)
                        while client.is_connected and not self.stop_requested.is_set():
                            # Link is up but no frames arrive anymore: reconnect.
                            if time.time() - self.last_frame > self.frame_timeout:
                                with self.lock:
                                    self.metrics["watchdog_resets"] += 1
                                self.disconnect_reason = "watchdog"
                                raise TimeoutError(f"no valid status frame for {self.frame_timeout:g} s, reconnecting")
                            await asyncio.sleep(0.2)
                    finally:
                        for task in tasks:
                            task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                        if client.is_connected:
                            try:
                                await client.stop_notify(self.char_uuid)
                            except Exception:
                                pass
            except asyncio.CancelledError:
                if not self.stop_requested.is_set():
                    raise
            except Exception as exc:
                message = f"BLE connection ({type(exc).__name__}): {exc}"
                LOG.warning(message)
                self.disconnect_reason = self.disconnect_reason or type(exc).__name__
                with self.lock:
                    self.last_error = message
            finally:
                self.client = None
                with self.lock:
                    if self.connected and not self.stop_requested.is_set():
                        self.metrics["session_disconnects"] += 1
                        LOG.info("Session %d ended after %.0f s (%s)", self.session_id,
                                 time.time() - self.session_started, self.disconnect_reason or "unknown")
                        self.last_error = self.last_error or f"Disconnected: {self.disconnect_reason}"
                    self.connected = False
            if not self.stop_requested.is_set():
                await asyncio.sleep(3)
        await self.bluetoothctl_disconnect()
        if monitor:
            monitor.cancel()
            await asyncio.gather(monitor, return_exceptions=True)
        self.loop = None


# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------

class MqttBridge:
    def __init__(self, bridge, topics, device_id, host, port, username=None, password=None,
                 ha_prefix=None, ha_interval=5):
        self.bridge = bridge
        self.topics = topics
        self.device_id = device_id
        self.host = host
        self.port = port
        self.ha_prefix = ha_prefix            # None = Home Assistant discovery disabled
        self.ha_interval = ha_interval
        self.ha_last = 0.0
        self.ha_burst_until = 0.0
        self.health_last = 0.0
        self.health_key = None
        self.stop_event = threading.Event()
        self.wake = threading.Event()         # publish immediately instead of waiting for the next second
        self.queue = queue.Queue(maxsize=16)
        self.connections = 0
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"pekaway-pu-{device_id}", clean_session=True)
        # An exception in a callback must not terminate the network thread.
        self.client.suppress_exceptions = True
        self.client.max_queued_messages_set(50)
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)
        if username:
            self.client.username_pw_set(username, password)
        self.client.will_set(topics.health, json.dumps(self.offline_health("MQTT connection lost")),
                             qos=1, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.publisher = threading.Thread(target=self.publish_loop, name="mqtt-status", daemon=True)
        self.worker = threading.Thread(target=self.command_loop, name="mqtt-commands", daemon=True)

    def offline_health(self, reason):
        return {"schema": SCHEMA_VERSION, "device_id": self.device_id, "state": "OFFLINE",
                "connected": False, "ble_connected": False, "last_error": reason,
                "address": self.bridge.address, "rssi": None}

    def publish(self, topic, payload, retain=False, qos=0):
        return self.client.publish(topic, json.dumps(payload, allow_nan=False), qos=qos, retain=retain)

    def on_connect(self, client, _userdata, _flags, reason_code, _properties):
        if reason_code != 0:
            hint = " (check --mqtt-username/--mqtt-password)" if re.search(
                r"authori[sz]ed|user ?name|password", str(reason_code), re.I) else ""
            LOG.warning("MQTT connection to %s:%d refused: %s%s", self.host, self.port, reason_code, hint)
            return
        self.connections += 1
        self.health_key = None
        client.subscribe(self.topics.cmd, qos=1)
        LOG.info("MQTT connected to %s:%d, base topic %s", self.host, self.port, self.topics.cmd[:-4])
        if self.ha_prefix:
            client.subscribe(f"{self.ha_prefix}/status", qos=1)
            self.publish_discovery()

    def on_disconnect(self, _client, _userdata, _flags, reason_code, _properties):
        if not self.stop_event.is_set():
            LOG.warning("MQTT disconnected: %s", reason_code)

    def publish_discovery(self):
        messages = ha_discovery(self.topics, self.device_id, self.bridge.address, self.ha_prefix)
        for topic, config in messages:
            self.publish(topic, config, retain=True, qos=1)
        self.ha_last = 0.0   # send the HA state right away
        LOG.info("Home Assistant discovery published (%d entities)", len(messages))

    def on_message(self, _client, _userdata, message):
        if self.ha_prefix and message.topic == f"{self.ha_prefix}/status":
            # Home Assistant restarted: announce the entities again.
            if message.payload == b"online":
                self.publish_discovery()
            return
        if message.topic != self.topics.cmd:
            return
        command = None
        try:
            if len(message.payload) > 256:
                raise ValueError("Command too long")
            command = message.payload.decode("utf-8").strip()
            if command.startswith("{"):
                data = json.loads(command)
                command = data.get("command") if isinstance(data, dict) else None
            if message.retain:
                raise ValueError("Retained commands are not executed")
            if not isinstance(command, str):
                raise ValueError("Command must be a string")
            if command not in COMMAND_BITS:
                raise ValueError("Unknown command")
            if not self.bridge.snapshot().get("connected"):
                raise ValueError("BLE not connected")
            self.queue.put_nowait((time.monotonic(), command))
        except queue.Full:
            self.result(command, "error", error="Command queue full")
        except (ValueError, UnicodeError) as exc:
            self.result(command, "error", error=str(exc))

    def result(self, command, status, **details):
        """status: sent -> confirmed | timeout | superseded, or error (rejected / write failed)."""
        payload = {"device_id": self.device_id, "command": command, "status": status,
                   "ok": status in ("sent", "confirmed"), **details}
        (LOG.warning if status in ("error", "timeout") else LOG.info)(
            "Command %s: %s%s", command, status,
            "".join(f", {key} {value}" for key, value in details.items()))
        self.publish(self.topics.result, payload)

    def command_loop(self):
        while not self.stop_event.is_set():
            try:
                received, command = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if self.stop_event.is_set() or time.monotonic() - received > 5:
                    raise ValueError("Command expired")
                self.result(command, "sent", packet=self.bridge.send_command(command))
                self.wake.set()   # publish the pending target value right away
            except Exception as exc:
                self.result(command, "error", error=str(exc) or type(exc).__name__)
            finally:
                self.queue.task_done()

    def health(self, snapshot, payload, now):
        status = snapshot.get("status")
        metrics = dict(snapshot.get("metrics", {}))
        metrics["mqtt_reconnects"] = max(0, self.connections - 1)
        return {"schema": SCHEMA_VERSION, "device_id": self.device_id,
                "state": "ONLINE" if payload else "STALE" if snapshot["connected"] else "DISCONNECTED",
                "connected": bool(payload), "ble_connected": snapshot["connected"], "timestamp": now,
                "age": round(now - status["timestamp"], 2) if status else None,
                "last_error": snapshot.get("last_error", ""),
                "address": self.bridge.address, "rssi": snapshot.get("rssi"),
                "session_id": snapshot.get("session_id", 0),
                "session_age": round(now - snapshot["session_started"]) if snapshot.get("session_started") else 0,
                "metrics": metrics}

    def publish_once(self, now, tick):
        # Timeouts first, so a timed-out command no longer overrides the state.
        events = self.bridge.take_command_events(now)
        snapshot = self.bridge.snapshot()
        payload = make_status(snapshot, self.device_id, now)
        health = self.health(snapshot, payload, now)
        # Health immediately on change, otherwise every HEALTH_INTERVAL seconds.
        key = (health["state"], health["last_error"], health["session_id"], health["rssi"])
        if key != self.health_key or tick - self.health_last >= HEALTH_INTERVAL:
            self.publish(self.topics.health, health, retain=True)
            self.health_key, self.health_last = key, tick
        if events:
            # Show the final state in Home Assistant without waiting for the next interval.
            self.ha_burst_until = tick + HA_SETTLE
        # Stale data is not published; consumers use health/timestamp.
        if payload:
            self.publish(self.topics.state, payload, retain=True)
            fast = payload["pending"] or tick < self.ha_burst_until
            if self.ha_prefix and (fast or tick - self.ha_last >= self.ha_interval):
                self.publish(self.topics.ha_state, payload, retain=True)
                self.ha_last = tick
        # Results after the state, so consumers already see the final value.
        for command, status, details in events:
            self.result(command, status, **details)

    def publish_loop(self):
        while not self.stop_event.is_set():
            if self.client.is_connected():
                self.publish_once(time.time(), time.monotonic())
            self.wake.wait(1)
            self.wake.clear()

    def start(self):
        self.client.connect_async(self.host, self.port, keepalive=15)
        self.client.loop_start()
        self.publisher.start()
        self.worker.start()

    def stop(self):
        self.stop_event.set()
        self.wake.set()
        self.publisher.join(timeout=3)
        self.worker.join(timeout=WRITE_TIMEOUT * 2 + 2)
        if self.client.is_connected():
            info = self.publish(self.topics.health, self.offline_health("Script stopped"), retain=True, qos=1)
            info.wait_for_publish(timeout=2)
        self.client.disconnect()
        self.client.loop_stop()


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def single_instance(path):
    """Prevent a second instance for the same Power Unit."""
    import fcntl
    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def seconds_between(low, high):
    def parse(value):
        seconds = float(value)
        if not low <= seconds <= high:
            raise argparse.ArgumentTypeError(f"must be between {low} and {high} seconds")
        return seconds
    return parse


def parse_args(argv=None):
    env = os.environ.get
    parser = argparse.ArgumentParser(description="Pekaway Power Unit BLE <-> MQTT bridge")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--address", default=env("PEKAWAY_BLE_ADDRESS"), help="BLE MAC address of the Power Unit")
    parser.add_argument("--device-id", default=env("PEKAWAY_DEVICE_ID"),
                        help="device ID used in topics and payloads (default: MAC address without colons)")
    parser.add_argument("--adapter", default=env("PEKAWAY_BLE_ADAPTER", "hci0"), help="Bluetooth adapter (default hci0)")
    parser.add_argument("--char-uuid", default=env("PEKAWAY_CHAR_UUID", "0000ffe1-0000-1000-8000-00805f9b34fb"))
    parser.add_argument("--mqtt-host", default=env("PEKAWAY_MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--mqtt-port", type=int, default=int(env("PEKAWAY_MQTT_PORT", "1883")))
    parser.add_argument("--mqtt-username", default=env("PEKAWAY_MQTT_USERNAME"), help="MQTT username (optional)")
    parser.add_argument("--mqtt-password", default=env("PEKAWAY_MQTT_PASSWORD"),
                        help="MQTT password; visible in the process list, prefer --mqtt-password-file "
                             "or PEKAWAY_MQTT_PASSWORD")
    parser.add_argument("--mqtt-password-file", help="file containing the MQTT password (first line)")
    parser.add_argument("--topic-prefix", default=env("PEKAWAY_TOPIC_PREFIX", "pekaway/power_unit"),
                        help="topic prefix, the device ID is appended (default pekaway/power_unit)")
    parser.add_argument("--ha-discovery", action="store_true", help="publish Home Assistant MQTT discovery")
    parser.add_argument("--ha-prefix", default="homeassistant", help="Home Assistant discovery prefix")
    parser.add_argument("--ha-interval", type=seconds_between(1, 30), default=5,
                        help="seconds between Home Assistant state updates, 1-30 (default 5)")
    parser.add_argument("--confirm-timeout", type=seconds_between(2, 60), default=10,
                        help="seconds to wait for the Power Unit to confirm a command, 2-60 (default 10)")
    parser.add_argument("--keepalive", type=float, default=4,
                        help="seconds without a write before sending display_sleep_off, 0 = off (default 4)")
    parser.add_argument("--frame-timeout", type=float, default=30,
                        help="seconds without a status frame before reconnecting (default 30)")
    parser.add_argument("--le-supervision-timeout", type=int, default=5000,
                        help="LE supervision timeout in ms for new connections, "
                             "0 = leave unchanged (default 5000)")
    parser.add_argument("--hci-monitor", action="store_true",
                        help="log connection parameters and HCI disconnect reasons via btmon (sudo)")
    parser.add_argument("--lock-file", help="default /tmp/pu_ble_mqtt_<device id>.lock")
    parser.add_argument("--debug", action="store_true", help="log raw BLE frames and keepalives")
    parser.add_argument("--scan", action="store_true",
                        help='scan for Power Units, print {"devices": [...]} as one JSON line and exit')
    parser.add_argument("--scan-time", type=seconds_between(3, 60), default=10,
                        help="scan duration in seconds, 3-60 (default 10)")
    args = parser.parse_args(argv)
    if args.scan:
        return args
    if not args.address:
        parser.error("--address or PEKAWAY_BLE_ADDRESS is required")
    args.device_id = (args.device_id or device_id_from_address(args.address)).lower()
    if not re.fullmatch(r"[a-z0-9_-]{1,32}", args.device_id):
        parser.error("--device-id may only contain a-z, 0-9, _ and - (max. 32 characters)")
    args.lock_file = args.lock_file or f"/tmp/pu_ble_mqtt_{args.device_id}.lock"
    if args.mqtt_password_file:
        try:
            with open(args.mqtt_password_file, encoding="utf-8") as handle:
                args.mqtt_password = handle.readline().rstrip("\r\n")
        except OSError as exc:
            parser.error(f"cannot read --mqtt-password-file: {exc.strerror}")
    if args.mqtt_password and not args.mqtt_username:
        parser.error("an MQTT password requires --mqtt-username or PEKAWAY_MQTT_USERNAME")
    return args


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(message)s")
    # bleak is very verbose at debug level.
    logging.getLogger("bleak").setLevel(logging.WARNING)
    if args.scan:
        LOG.info("Scanning for Power Units for %g s on %s ...", args.scan_time, args.adapter)
        try:
            devices = asyncio.run(scan_power_units(args.adapter, args.scan_time))
        except Exception as exc:
            LOG.error("Scan failed: %s", str(exc) or type(exc).__name__)
            print(json.dumps({"devices": [], "error": str(exc) or type(exc).__name__}), flush=True)
            return 1
        LOG.info("Found %d Power Unit(s)", len(devices))
        print(json.dumps({"devices": devices}), flush=True)
        return 0
    lock = single_instance(args.lock_file)
    if lock is None:
        LOG.error("Already running (%s is locked)", args.lock_file)
        return 2

    LOG.info("Pekaway Power Unit bridge %s: BLE %s on %s, device ID %s, MQTT %s:%d (%s), keepalive %g s, "
             "Home Assistant %s", __version__, args.address, args.adapter, args.device_id, args.mqtt_host,
             args.mqtt_port, f"user {args.mqtt_username}" if args.mqtt_username else "anonymous", args.keepalive,
             f"discovery every {args.ha_interval:g} s" if args.ha_discovery else "off")
    try:
        configure_le_supervision_timeout(args.adapter, args.le_supervision_timeout)
    except Exception as exc:
        LOG.warning("Could not read/set LE parameters: %s", exc)

    bridge = Bridge(args.address, args.char_uuid, args.frame_timeout, args.keepalive,
                    log_frames=args.debug, adapter=args.adapter, hci_monitor=args.hci_monitor,
                    confirm_timeout=args.confirm_timeout)
    mqtt_bridge = MqttBridge(bridge, Topics(args.topic_prefix, args.device_id), args.device_id,
                             args.mqtt_host, args.mqtt_port,
                             args.mqtt_username, args.mqtt_password,
                             ha_prefix=args.ha_prefix if args.ha_discovery else None,
                             ha_interval=args.ha_interval)

    def stop_signal(signum, _frame):
        LOG.info("Signal %d received, stopping ...", signum)
        bridge.stop_requested.set()
    signal.signal(signal.SIGINT, stop_signal)
    signal.signal(signal.SIGTERM, stop_signal)

    mqtt_bridge.start()
    try:
        asyncio.run(bridge.run())
    finally:
        mqtt_bridge.stop()
        LOG.info("Stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
