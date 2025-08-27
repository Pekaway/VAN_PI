#########################
#                       #
#       Script by       #
#      Pekaway GmbH     #
#                       #
#########################

import sys
import json
import asyncio
import bleak
from bleak import BleakClient

# UUIDs for the characteristics
INA_AMPS_UUID = "d2e8ede8-9b31-4478-9fd6-75845cb68b1d"
INA_VOLTS_UUID = "ff100f8c-1266-4309-b472-76bc25e4a62f"
INA_SOC_UUID = "459e9ea4-a335-4a3f-b838-46788fd6bbe4"

async def request_ina_data(client):
    try:
        print("Requesting INA data...")
        # Read characteristics concurrently
        amps_data = await client.read_gatt_char(INA_AMPS_UUID)
        volts_data = await client.read_gatt_char(INA_VOLTS_UUID)
        soc_data = await client.read_gatt_char(INA_SOC_UUID)

        # Parse data to float
        amps = float(amps_data.decode('utf-8'))
        volts = float(volts_data.decode('utf-8'))
        soc = float(soc_data.decode('utf-8'))

        # Construct JSON object
        data = {
            "PekawayBLEShunt": {
                "milliamps": round(amps, 2),
                "volts": round(volts, 2),
                "soc": round(soc, 2)
            }
        }

        # Print JSON object
        print(json.dumps(data))

        return data
    except Exception as e:
        print("Error:", e)
        return None

async def establish_connection(mac_address):
    while True:
        try:
            async with BleakClient(mac_address) as client:
                print("Connecting to the Pekaway Shunt...")
                while True:
                    data = await request_ina_data(client)
                    if data is None:
                        break
                    await asyncio.sleep(10)  # Default interval in seconds
        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(5)  # Retry after 5 seconds

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 bleShunt.py <ESP32_MAC_ADDRESS>")
        return

    esp32_mac = sys.argv[1]
    asyncio.run(establish_connection(esp32_mac))

if __name__ == "__main__":
    main()
