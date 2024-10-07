###################################
# created by Vincent Gloß 09.2024 #
###################################

import os
import time
import argparse

# Delay to ensure sensors are initialized
time.sleep(2)

def read_ds18b20_sensors():
    """
    Reads the directory /sys/bus/w1/devices/ to find all connected DS18B20 sensors.
    DS18B20 sensors have IDs that start with "28" or "10".
    
    Returns:
        list: A list of sensor IDs found in the directory.
    """
    try:
        # Get a list of directories (sensor IDs) that start with "28" or "10"
        sensors = [x for x in os.listdir("/sys/bus/w1/devices") if x.split("-")[0] in ["28", "10"]]
        return sensors
    except OSError as e:
        # Handle any OS-related errors, such as the directory not being found
        print("Received error while reading sensors:", e)
        return []

def read_sensor_values(sensors):
    """
    Reads the temperature from each DS18B20 sensor by accessing its 'w1_slave' file.
    
    Args:
        sensors (list): List of sensor IDs to read from.
    
    Returns:
        dict: A dictionary mapping sensor IDs to their respective temperature readings.
    """
    sensor_values = {}
    try:
        for sensor_id in sensors:
            try:
                # Open the w1_slave file for the sensor to read its data
                with open(f"/sys/bus/w1/devices/{sensor_id}/w1_slave") as file:
                    file_content = file.read()
                
                # Extract the temperature from the file content
                string_value = file_content.split("\n")[1].split(" ")[9]
                sensor_value = float(string_value[2:]) / 1000  # Convert to Celsius
                sensor_values[sensor_id] = f'{sensor_value:6.2f}'
            except (OSError, IndexError) as e:
                # If there's an error reading the sensor, mark it as "N/A"
                sensor_values[sensor_id] = "N/A"
                print(f"Error reading sensor {sensor_id}: {e}")
    except (OSError, IndexError) as e:
        print(f"Couldn't read DS18B20 sensors: {e}")
    
    return sensor_values

def main(interval):
    """
    Main loop that continuously reads the sensors and prints their values at specified intervals.
    
    Args:
        interval (int): Time interval (in seconds) between each sensor reading.
    """
    while True:
        # Read the list of connected sensors
        sensors = read_ds18b20_sensors()
        
        if sensors:
            # If sensors are found, read their temperature values
            sensor_values = read_sensor_values(sensors)
            
            # Print the index, temperature, and ID for each sensor
            for index, (sensor_id, temperature) in enumerate(sensor_values.items()):
                print(f"{index}: {temperature} {sensor_id}")
        else:
            # If no sensors are found, print a message
            print("No sensors found.")
        
        # Wait for the specified interval before reading again
        time.sleep(interval)

if __name__ == "__main__":
    # Set up argument parser for optional time interval
    parser = argparse.ArgumentParser(description="Read DS18B20 sensors and output temperatures.")
    parser.add_argument("--time", type=int, default=10, help="Interval between sensor readings in seconds (default: 10)")
    args = parser.parse_args()
    
    # Start the main loop with the specified time interval
    main(args.time)
