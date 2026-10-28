#########################
#                       #
#       Script by       #
#      Pekaway GmbH     #
#                       #
#########################

import asyncio
import os
import json
import signal
from datetime import datetime, timedelta

os.environ["RUUVI_BLE_ADAPTER"] = "bleak"
from ruuvitag_sensor.ruuvi import RuuviTagSensor

# Read MAC addresses once at startup
def get_mac_addresses_from_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        macs = [entry["mac"] for entry in data]
    return set(macs)  # Return as a set for fast lookup

# Graceful shutdown function
def shutdown(loop):
    print("Shutting down gracefully...")
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.stop()

async def main():
    file_path = "/home/pi/pekaway/ruuvitags.json"
    macs = get_mac_addresses_from_file(file_path)

    while True:
        try:
            data_json = await asyncio.wait_for(collect_ruuvitag_data(macs, per_device_timeout=20), timeout=25)
        except asyncio.TimeoutError:
            print("Global timeout occurred. Retrying...")
            data_json = {mac: "timeout" for mac in macs}

        print(json.dumps(data_json, indent=4))
        await asyncio.sleep(20)

async def collect_ruuvitag_data(macs, per_device_timeout=20):
    found = {}
    first_seen = {}
    start_time = datetime.now()

    async for mac_address, sensor_data in RuuviTagSensor.get_data_async(list(macs)):
        now = datetime.now()

        # Check if we have exceeded total timeout
        if (now - start_time).total_seconds() > per_device_timeout:
            print("Per-device timeout reached.")
            break

        if mac_address in macs and mac_address not in found:
            found[mac_address] = sensor_data
            first_seen[mac_address] = now
            print(f"Received data from {mac_address}")

        # Minor sleep to reduce CPU pressure
        await asyncio.sleep(0.01)

        # Early exit if we already have all
        if len(found) == len(macs):
            break

    # Prepare result: mark missing devices as "timeout"
    data_json = {}
    for mac in macs:
        if mac in found:
            data_json[mac] = found[mac]
        else:
            data_json[mac] = "timeout"
            print(f"Device {mac} not found in time.")

    return data_json

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: shutdown(loop))
    
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
