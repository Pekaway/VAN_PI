import os
import time
import argparse

tempSensorBezeichnung = []
tempSensorAnzahl = 0
tempSensorWert = []

def ds1820einlesen():
    global tempSensorBezeichnung, tempSensorAnzahl
    try:
        for x in os.listdir("/sys/bus/w1/devices"):
            if x.split("-")[0] in ["28", "10"]:
                tempSensorBezeichnung.append(x)
        tempSensorAnzahl = len(tempSensorBezeichnung)
    except OSError as e:
        print("Received error:", e)

def ds1820auslesen():
    global tempSensorBezeichnung, tempSensorWert
    try:
        for sensor in tempSensorBezeichnung:
            with open(f"/sys/bus/w1/devices/{sensor}/w1_slave") as file:
                filecontent = file.read()
            stringvalue = filecontent.split("\n")[1].split(" ")[9]
            sensorwert = float(stringvalue[2:]) / 1000
            temperatur = '%6.2f' % sensorwert
            tempSensorWert.append(temperatur)
    except (OSError, IndexError) as e:
        print(f"Couldn't read DS18B20 sensors: {e}")

def main(interval):
    ds1820einlesen()
    while True:
        tempSensorWert.clear()  # Clear previous readings
        ds1820auslesen()
        for idx, temp in enumerate(tempSensorWert):
            print(f"{idx}: {temp}")
        time.sleep(interval)  # Dynamic sleep time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read DS18B20 sensors and output temperatures.")
    parser.add_argument("--time", type=int, default=10, help="Interval between sensor readings in seconds (default: 10)")
    args = parser.parse_args()
    main(args.time)
