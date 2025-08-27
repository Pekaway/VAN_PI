#########################
#                       #
#       Script by       #
#      Pekaway GmbH     #
#                       #
#########################

import asyncio
import logging
import uuid
import json
import sys
import signal  # Import the signal module
import os

from bleak import BleakClient

class PekawayBleMppt:
    def __init__(self, logger=None):
        # Initialize the logger
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)

        # Initialize BLE client and UUIDs
        self.client = None
        self.GET_STATUS_PAYLOAD = "fe043030002bab15"
        self.GET_STATUS_UUID = uuid.UUID("0000ff02-0000-1000-8000-00805f9b34fb")
        self.NOTIFY_UUID = uuid.UUID("0000ff01-0000-1000-8000-00805f9b34fb")
        self.ENABLE_UUID = uuid.UUID("0000ff03-0000-1000-8000-00805f9b34fb")

        # Initialize data storage
        self.data = b""
        self.future = None

    async def connect(self, mac_address):
        try:
            # Connect to the BLE device
            self.logger.info("Connecting to the Pekaway MPPT device...")
            self.client = BleakClient(mac_address)
            await self.client.connect()
            self.logger.info("Connected to the device.")

            # Start notifications and enable data notifications
            await self.client.start_notify(self.NOTIFY_UUID, self.__data_handler_cb)
            await self.client.write_gatt_char(self.ENABLE_UUID, b"0100")
            self.logger.info("Notifications started.")
        except Exception as e:
            self.logger.error(f"Error connecting to the device: {e}")
            raise

    async def disconnect(self):
        try:
            if self.client:
                # Disconnect from the BLE device if connected
                self.logger.info("Disconnecting from the device...")
                await self.client.stop_notify(self.NOTIFY_UUID)
                await self.client.disconnect()
                self.logger.info("Disconnected from the device.")
        except Exception as e:
            self.logger.error(f"Error disconnecting from the device: {e}")
            raise

    async def get_status(self):
        try:
            # Get status data from the BLE device
            self.logger.info("Requesting status data...")
            self.future = asyncio.get_event_loop().create_future()
            await self.client.write_gatt_char(self.GET_STATUS_UUID, bytes.fromhex(self.GET_STATUS_PAYLOAD))
            status = await self.future

            # Parse status data and return as JSON
            return {
              "PekawayBLEMppt": {
                "soc": int.from_bytes(status[46:47], 'big'),
                "pv": {
                    "V": int.from_bytes(status[63:65], 'big') / 100,
                    "A": int.from_bytes(status[65:67], 'big', signed=True) / 100,
                    "W": int.from_bytes(status[67:69], 'big') / 100,
                    "total": int.from_bytes(status[73:75], 'big') / 100
                },
                "batt": {
                    "V": int.from_bytes(status[47:49], 'big') / 100,
                    "A": int.from_bytes(status[49:51], 'big', signed=True) / 100,
                    "temp": int.from_bytes(status[17:19], 'big') / 100
                },
                "load": {
                    "V": int.from_bytes(status[55:57], 'big') / 100,
                    "A": int.from_bytes(status[57:59], 'big', signed=True) / 100,
                    "W": int.from_bytes(status[59:61], 'big') / 100,
                    "total": int.from_bytes(status[79:81], 'big') / 100
                }
              }
            }
        except Exception as e:
            self.logger.error(f"Error getting status data: {e}")
            raise

    def __data_handler_cb(self, characteristic, value):
        # Callback function for handling incoming data notifications
        # print("Received data notification.")
        self.data += value
        if len(self.data) >= 91:
            self.future.set_result(self.data)
            self.__reset()

    def __reset(self):
        # Reset data storage
        self.data = b""
        self.future = None

Pekaway = None  # Define Pekaway at a higher scope

async def main(mac_address):
    global Pekaway  # Access the global Pekaway instance
    # Main function to run the script
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create an instance of PekawayBleMppt and connect to the device
    Pekaway = PekawayBleMppt(logger=logger)
    try:
        await Pekaway.connect(mac_address)
        logger.info("Connected to the device.")

        while True:
            # Get status data from the device and print it as JSON
            status = await Pekaway.get_status()
            print(json.dumps(status))

            # Wait for 30 seconds before requesting status data again
            await asyncio.sleep(33)
    except asyncio.CancelledError:  # Catch the CancelledError exception to handle Task cancellation
        pass  # Do nothing, this is expected when the asyncio task is cancelled
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    # Check if the script is run as main and the correct number of arguments is provided
    if len(sys.argv) != 2:
        print("Usage: python3 script.py <mac_address>")
        sys.exit(1)
    mac_address = sys.argv[1]
    
    # Set up signal handler for SIGINT
    signal.signal(signal.SIGINT, lambda sig, frame: asyncio.create_task(shutdown()))  # Register the handler for SIGINT
    
    # Define the shutdown coroutine
    async def shutdown():
        if Pekaway:
            print("Received keyboard interrupt, disconnecting...")
            await Pekaway.disconnect()
            raise KeyboardInterrupt
            # os.kill(os.getpid(), signal.SIGINT)  # Raise KeyboardInterrupt after cleanup
        
    asyncio.run(main(mac_address))

