#########################
#                       #
#       Script by       #
#      Pekaway GmbH     #
#                       #
#########################

import argparse
import pexpect
import json
import time

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest="device", help="Specify remote Bluetooth address", metavar="MAC", required=True)
parser.add_argument("-v", "--verbose", dest="v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

while True:
    # Run gatttool interactively.
    child = pexpect.spawn("gatttool -I -b {0}".format(args.device))

    # Connect to the device
    for attempt in range(10):
        try:
            if args.v:
                print("BMS connecting (Try:", attempt + 1, ")")
            child.sendline("connect")
            child.expect("Connection successful", timeout=1)
        except pexpect.TIMEOUT:
            if args.v == 2:
                print(child.before)
            continue
        else:
            if args.v:
                print("BMS connection successful")
            break
    else:
        if args.v:
            print("BMS Connect timeout! Exit")
        child.sendline("exit")
        print("{}")
        exit()

    # Request data until data is received or max attempt is reached
    # Voltage and other information
    for attempt in range(10):
        try:
            resp = b''
            if args.v:
                print("BMS requesting data 1 (Try:", attempt + 1, ")")
            child.sendline("char-write-req 0x0015 dda50300fffd77")
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v:
                print("BMS received data 1")
            if args.v == 2:
                print("BMS answer 1: ", child.before)
            resp += child.before
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v == 2:
                print("BMS answer 2: ", child.before)
            resp += child.before
        except pexpect.TIMEOUT:
            continue
        else:
            break
    else:
        resp = b''
        if args.v:
            print("BMS Answering timeout!")
        if args.v == 2:
            print(child.before)

    # Request data until data is received or max attempt is reached
    # individual cell voltages. Each voltage is a 16 bit number
    for attempt in range(10):
        try:
            resp2 = b''
            if args.v:
                print("BMS requesting data 2 (Try:", attempt + 1, ")")
            child.sendline("char-write-req 0x0015 dda50400fffc77")
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v:
                print("BMS received data 2")
            if args.v == 2:
                print("BMS answer 1: ", child.before)
            resp2 += child.before
        except pexpect.TIMEOUT:
            continue
        else:
            break
    else:
        resp2 = b''
        if args.v:
            print("BMS Answering timeout!")
        if args.v == 2:
            print(child.before)

    # Request data until data is received or max attempt is reached
    # BMS Name in ASCII
    for attempt in range(10):
        try:
            resp3 = b''
            if args.v:
                print("BMS requesting data 3 (Try:", attempt + 1, ")")
            child.sendline("char-write-req 0x0015 dda50500fffb77")
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v:
                print("BMS received data 3")
            if args.v == 2:
                print("BMS answer 1: ", child.before)
            resp3 += child.before
        except pexpect.TIMEOUT:
            continue
        else:
            break
    else:
        resp3 = b''
        if args.v:
            print("BMS Answering timeout!")
        if args.v == 2:
            print(child.before)

    # Close connection
    if args.v:
        print("BMS disconnecting")
    child.sendline("disconnect")
    child.sendline("exit")

    # Build JSON
    if args.v:
        print("Response 1:", resp)
        print("Response 2:", resp2)
        print("Response 3:", resp3)

    resp = resp[:-1]
    resp2 = resp2[:-1]
    resp3 = resp3[:-1]

    response = bytearray.fromhex(resp.decode())
    response2 = bytearray.fromhex(resp2.decode())
    response3 = bytearray.fromhex(resp3.decode())

    rawdat = {}
    if (response.endswith(b'w')) and (response.startswith(b'\xdd\x03')):
        response = response[4:]

        rawdat['Vmain'] = int.from_bytes(response[0:2], byteorder='big', signed=True) / 100.0  # total voltage [V]
        rawdat['Imain'] = int.from_bytes(response[2:4], byteorder='big', signed=True) / 100.0  # current [A]
        rawdat['RemainAh'] = int.from_bytes(response[4:6], byteorder='big', signed=True) / 100.0  # remaining capacity [Ah]
        rawdat['NominalAh'] = int.from_bytes(response[6:8], byteorder='big', signed=True) / 100.0  # nominal capacity [Ah]
        rawdat['NumberCycles'] = int.from_bytes(response[8:10], byteorder='big', signed=True)  # number of cycles
        rawdat['ProtectState'] = int.from_bytes(response[16:18], byteorder='big', signed=False)  # protection state
        rawdat['ProtectStateBin'] = format(rawdat['ProtectState'], '016b')  # protection state binary
        rawdat['SoC'] = int.from_bytes(response[19:20], byteorder='big', signed=False)  # remaining capacity [%]
        rawdat['TempC1'] = (int.from_bytes(response[23:25], byteorder='big', signed=True) - 2731) / 10.0
        rawdat['TempC2'] = (int.from_bytes(response[25:27], byteorder='big', signed=True) - 2731) / 10.0

        if (rawdat['ProtectStateBin'][0:13]) == '0000000000000':
            rawdat['ProtectStateText'] = "ok";
        if (rawdat['ProtectStateBin'][0]) == "1":
            rawdat['ProtectStateText'] = "CellBlockOverVolt";
        if (rawdat['ProtectStateBin'][1]) == "1":
            rawdat['ProtectStateText'] = "CellBlockUnderVol";
        if (rawdat['ProtectStateBin'][2]) == "1":
            rawdat['ProtectStateText'] = "BatteryOverVol";
        if (rawdat['ProtectStateBin'][3]) == "1":
            rawdat['ProtectStateText'] = "BatteryUnderVol";
        if (rawdat['ProtectStateBin'][4]) == "1":
            rawdat['ProtectStateText'] = "ChargingOverTemp";
        if (rawdat['ProtectStateBin'][5]) == "1":
            rawdat['ProtectStateText'] = "ChargingLowTemp";
        if (rawdat['ProtectStateBin'][6]) == "1":
            rawdat['ProtectStateText'] = "DischargingOverTemp";
        if (rawdat['ProtectStateBin'][7]) == "1":
            rawdat['ProtectStateText'] = "DischargingLowTemp";
        if (rawdat['ProtectStateBin'][8]) == "1":
            rawdat['ProtectStateText'] = "ChargingOverCurrent";
        if (rawdat['ProtectStateBin'][9]) == "1":
            rawdat['ProtectStateText'] = "DischargingOverCurrent";
        if (rawdat['ProtectStateBin'][10]) == "1":
            rawdat['ProtectStateText'] = "ShortCircuit";
        if (rawdat['ProtectStateBin'][11]) == "1":
            rawdat['ProtectStateText'] = "ForeEndICError";
        if (rawdat['ProtectStateBin'][12]) == "1":
            rawdat['ProtectStateText'] = "MOSSoftwareLockIn";

    if (response2.endswith(b'w')) and (response2.startswith(b'\xdd\x04')):
        response2 = response2[4:-3]
        cellcount = len(response2) // 2
        if args.v == 2:
            print("Detected Cellcount: ", cellcount)
        for cell in range(cellcount):
            # print ("Cell:",cell+1,"from byte",cell*2,"to",cell*2+2)
            rawdat['Vcell' + str(cell + 1)] = int.from_bytes(response2[cell * 2:cell * 2 + 2], byteorder='big',
                                                             signed=True) / 1000.0

    if (response3.endswith(b'w')) and (response3.startswith(b'\xdd\x05')):
        response3 = response3[4:-3]
        rawdat['Name'] = response3.decode("ASCII")

    # Print JSON
    print(json.dumps(rawdat, indent=1, sort_keys=False))

    # Wait for 15 seconds before requesting data again
    time.sleep(18)