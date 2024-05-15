import argparse
import time
import json
import busio
import board
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

def main(sleep_time):
    # Create the I2C bus
    i2c = busio.I2C(board.SCL, board.SDA)

    # Create an ADS1115 ADC (16-bit) instance.
    ads = ADS.ADS1115(i2c)

    # Main loop.
    while True:
        # Read all the ADC channel values and store them in a list.
        values = [(AnalogIn(ads, i).value, AnalogIn(ads, i).voltage) for i in (ADS.P0, ADS.P1, ADS.P2, ADS.P3)]
        # Create a dictionary to hold the channel values.
        values_dict = {'channel{}'.format(i): {'value': value[0], 'voltage': value[1]} for i, value in enumerate(values)}
        # Serialize the dictionary to JSON format.
        json_data = json.dumps(values_dict)
        # Print the JSON data.
        print(json_data)
        # Pause for the specified number of seconds.
        time.sleep(sleep_time)

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Read analog sensor data from ADS1115 ADC.')
    parser.add_argument('--time', type=int, default=15, help='Sleep time in seconds between readings (default: 15)')
    args = parser.parse_args()

    # Call the main function with the specified sleep time
    main(args.time)
