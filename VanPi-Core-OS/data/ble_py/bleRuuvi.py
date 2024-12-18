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
from datetime import datetime
os.environ["RUUVI_BLE_ADAPTER"] = "bleak"
from ruuvitag_sensor.ruuvi import RuuviTagSensor

# Function to read MAC addresses from a JSON file
def get_mac_addresses_from_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        macs = [entry["mac"] for entry in data]
    return macs

# Graceful shutdown function
def shutdown(loop):
    print("Shutting down gracefully...")
    for task in asyncio.all_tasks(loop):
        task.cancel()
    loop.stop()

async def main():
    # Path to the JSON file containing MAC addresses
    file_path = "/home/pi/pekaway/ruuvitags.json"

    while True:
        # Get MAC addresses from the file
        macs = get_mac_addresses_from_file(file_path)

        # Initialize data_json with None for each MAC
        data_json = {mac: None for mac in macs}

        # Get data only for defined MACs with a timeout of 20 seconds
        try:
            datas = await asyncio.wait_for(collect_ruuvitag_data(macs), timeout=20)
            
            # Populate data_json with received data
            for data in datas:
                mac_address = data[0]
                data_json[mac_address] = data[1]
            
        except asyncio.TimeoutError:
            print("Timeout occurred. Retrying...")

        # Print JSON string
        print(json.dumps(data_json, indent=4))

        # Wait for 60 seconds before starting the next request
        await asyncio.sleep(60)

async def collect_ruuvitag_data(macs):
    datas = []
    async for found_data in RuuviTagSensor.get_data_async(macs):
        datas.append(found_data)
        # Continue collecting data until all MACs have been seen at least once
        unique_macs = {data[0] for data in datas}
        if unique_macs == set(macs):
            break
    return datas

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Register signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: shutdown(loop))
    
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
