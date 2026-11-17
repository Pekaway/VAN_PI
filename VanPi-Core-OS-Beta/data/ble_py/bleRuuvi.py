#########################
#                       #
#      Script by        #
#     Pekaway GmbH       #
#                       #
#########################

import asyncio
import json
import os
import signal
import sys

os.environ["RUUVI_BLE_ADAPTER"] = "bleak"
from bleak import BleakScanner
from ruuvitag_sensor.adapters.bleak_ble import BleCommunicationBleak
from ruuvitag_sensor.adapters.utils import rssi_to_hex
from ruuvitag_sensor.ruuvi import RuuviTagSensor


def get_mac_addresses_from_file(file_path):
    with open(file_path, "r") as file:
        return {entry["mac"] for entry in json.load(file)}


def shutdown(task):
    # Cancel once and let the scanner's finally block finish before exiting.
    if not task.cancelling():
        print("Shutting down gracefully...", file=sys.stderr, flush=True)
        task.cancel()


async def main():
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown, task)

    macs = get_mac_addresses_from_file("/home/pi/pekaway/ruuvitags.json")
    while True:
        try:
            data_json = await asyncio.wait_for(
                collect_ruuvitag_data(macs, per_device_timeout=20), timeout=25
            )
        except asyncio.TimeoutError:
            print("Global timeout occurred. Retrying...", file=sys.stderr, flush=True)
            data_json = {mac: "timeout" for mac in macs}

        # Keep diagnostics out of the JSON stream consumed by Node-RED.
        print(json.dumps(data_json), flush=True)
        await asyncio.sleep(20)


async def collect_ruuvitag_data(macs, per_device_timeout=20):
    if not macs:
        return {}

    found = {}
    wanted = {mac.upper(): mac for mac in macs}
    packets = asyncio.Queue(maxsize=32)

    def receive(device, advertisement):
        mac = wanted.get(device.address.upper())
        if mac is None or mac in found:
            return
        manufacturer_data = advertisement.manufacturer_data.get(1177)
        if manufacturer_data is not None and not packets.full():
            packets.put_nowait((mac, manufacturer_data, advertisement.rssi))

    # Own the scanner here: the library's async generator can skip scanner.stop()
    # when wait_for cancels it. Reuse its existing Ruuvi decoding unchanged.
    scanner = BleakScanner(detection_callback=receive)
    try:
        await scanner.start()
        try:
            async with asyncio.timeout(per_device_timeout):
                while len(found) < len(macs):
                    mac, manufacturer_data, rssi = await packets.get()
                    raw = BleCommunicationBleak._parse_data(manufacturer_data)
                    raw += rssi_to_hex(rssi)
                    parsed = RuuviTagSensor._parse_data((mac, raw), [], [mac])
                    if parsed is not None:
                        found[mac] = parsed[1]
        except asyncio.TimeoutError:
            # This deadline also expires when no advertisements arrive at all.
            pass
    finally:
        # Finish StopDiscovery before returning, retrying, or shutting down.
        await scanner.stop()

    return {mac: found.get(mac, "timeout") for mac in macs}


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
