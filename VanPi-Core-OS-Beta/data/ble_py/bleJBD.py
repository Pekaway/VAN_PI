import argparse
import pexpect
import json
import time
import signal
import sys

# Global variable for the BLE connection
child = None

# Signal handler to properly close the BLE connection
def handle_exit(signum, frame):
    global child
    if child:
        print("\nTerminating script, closing BLE connection...")
        try:
            child.sendline("disconnect")
            child.sendline("exit")
        except Exception as e:
            print(f"Error while disconnecting: {e}")
    sys.exit(0)

# Register signal handlers for SIGINT and SIGTERM
signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", required=True)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

while True:
    # Run gatttool interactively.
    child = pexpect.spawn("gatttool -I -b {0}".format(args.device))
    
    # Connect to the device
    for attempt in range(10):
        try:
            if args.v: print("BMS connecting (Try:", attempt+1, ")")
            child.sendline("connect")
            child.expect("Connection successful", timeout=3)
        except pexpect.TIMEOUT:
            if args.v==2: print(child.before)
            continue
        else:
            if args.v: print("BMS connection successful")
            break
    else:
        if args.v: print ("BMS Connect timeout! Exit")
        child.sendline("exit")
        print ("{}")
        sys.exit()    
    
    # Request data until data is received or max attempt is reached
    # Voltage and other information
    for attempt in range(10):
        try:
            resp=b''
            if args.v: print("BMS requesting data 1 (Try:", attempt+1, ")")
            child.sendline("char-write-req 0x0015 dda50300fffd77")
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v: print("BMS received data 1")
            if args.v==2: print("BMS answer 1: ", child.before)
            resp+=child.before
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v==2: print("BMS answer 2: ", child.before)
            resp+=child.before
        except pexpect.TIMEOUT:
            continue
        else:
            break
    else:
        resp=b''
        if args.v: print ("BMS Answering timeout!")
        if args.v==2: print(child.before)
    
    # Request data until data is received or max attempt is reached
    # Individual cell voltages
    for attempt in range(10):
        try:
            resp2=b''
            if args.v: print("BMS requesting data 2 (Try:", attempt+1, ")")
            child.sendline("char-write-req 0x0015 dda50400fffc77")
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v: print("BMS received data 2")
            if args.v==2: print("BMS answer 1: ", child.before)
            resp2+=child.before
        except pexpect.TIMEOUT:
            continue
        else:
            break
    else:
        resp2=b''
        if args.v: print ("BMS Answering timeout!")
        if args.v==2: print(child.before)
    
    # Request data until data is received or max attempt is reached
    # BMS Name in ASCII
    for attempt in range(10):
        try:
            resp3=b''
            if args.v: print("BMS requesting data 3 (Try:", attempt+1, ")")
            child.sendline("char-write-req 0x0015 dda50500fffb77")
            child.expect("Notification handle = 0x0011 value: ", timeout=1)
            child.expect("\r\n", timeout=0)
            if args.v: print("BMS received data 3")
            if args.v==2: print("BMS answer 1: ", child.before)
            resp3+=child.before
        except pexpect.TIMEOUT:
            continue
        else:
            break
    else:
        resp3=b''
        if args.v: print ("BMS Answering timeout!")
        if args.v==2: print(child.before)
    
    # Close connection
    if args.v: print("BMS disconnecting")
    child.sendline("disconnect")
    child.sendline("exit")
    
    # Build JSON
    if args.v: print("Response 1:", resp)
    if args.v: print("Response 2:", resp2)
    if args.v: print("Response 3:", resp3)
    
    resp = resp[:-1]
    resp2 = resp2[:-1]
    resp3 = resp3[:-1]
    
    response=bytearray.fromhex(resp.decode())
    response2=bytearray.fromhex(resp2.decode())
    response3=bytearray.fromhex(resp3.decode())
    
    rawdat={}
    if (1==1):
        response = response[4:]
    
        rawdat['Vmain']=int.from_bytes(response[0:2], byteorder = 'big',signed=True)/100.0
        rawdat['Imain']=int.from_bytes(response[2:4], byteorder = 'big',signed=True)/100.0 #current [A]
        rawdat['RemainAh']=int.from_bytes(response[4:6], byteorder = 'big',signed=True)/100.0 #remaining capacity [Ah]
        rawdat['NominalAh']=int.from_bytes(response[6:8], byteorder = 'big',signed=True)/100.0 #nominal capacity [Ah]
        rawdat['SoC']=round(rawdat['RemainAh']/rawdat['NominalAh']*100.0, 2) #remaining capacity [%]
        rawdat['TempMOS']=(int.from_bytes(response[23:25],byteorder = 'big',signed=True)-2731)/10.0
        rawdat['TempC1']=(int.from_bytes(response[25:27],byteorder = 'big',signed=True) -2731)/10.0
        rawdat['TempC2']=(int.from_bytes(response[27:29],byteorder = 'big',signed=True) -2731)/10.0
        rawdat['NumberCycles'] = int.from_bytes(response[9:10], byteorder='big', signed=True)  # number of cycles
        rawdat['ProtectState']=int.from_bytes(response[16:18],byteorder = 'big',signed=False) #protection state
        rawdat['ProtectStateBin']=format(rawdat['ProtectState'], '016b') #protection state binary
    
    
        if (rawdat['ProtectStateBin'][0:13]) == '0000000000000':
            rawdat['ProtectStateText']="ok";
        if (rawdat['ProtectStateBin'][0]) == "1":
            rawdat['ProtectStateText']="CellBlockOverVolt";
        if (rawdat['ProtectStateBin'][1]) == "1":
            rawdat['ProtectStateText']="CellBlockUnderVol";
        if (rawdat['ProtectStateBin'][2]) == "1":
            rawdat['ProtectStateText']="BatteryOverVol";
        if (rawdat['ProtectStateBin'][3]) == "1":
            rawdat['ProtectStateText']="BatteryUnderVol";
        if (rawdat['ProtectStateBin'][4]) == "1":
            rawdat['ProtectStateText']="ChargingOverTemp";
        if (rawdat['ProtectStateBin'][5]) == "1":
            rawdat['ProtectStateText']="ChargingLowTemp";
        if (rawdat['ProtectStateBin'][6]) == "1":
            rawdat['ProtectStateText']="DischargingOverTemp";
        if (rawdat['ProtectStateBin'][7]) == "1":
            rawdat['ProtectStateText']="DischargingLowTemp";
        if (rawdat['ProtectStateBin'][8]) == "1":
            rawdat['ProtectStateText']="ChargingOverCurrent";
        if (rawdat['ProtectStateBin'][9]) == "1":
            rawdat['ProtectStateText']="DischargingOverCurrent"; 
        if (rawdat['ProtectStateBin'][10]) == "1":
            rawdat['ProtectStateText']="ShortCircuit";
        if (rawdat['ProtectStateBin'][11]) == "1":
            rawdat['ProtectStateText']="ForeEndICError";
        if (rawdat['ProtectStateBin'][12]) == "1":
            rawdat['ProtectStateText']="MOSSoftwareLockIn";
    
    if (response2.endswith(b'w')) and (response2.startswith(b'\xdd\x04')):
        response2=response2[4:-3]
        cellcount=len(response2)//2
        if args.v==2: print ("Detected Cellcount: ",cellcount)
        for cell in range(cellcount):
            #print ("Cell:",cell+1,"from byte",cell*2,"to",cell*2+2)
            rawdat['Vcell'+str(cell+1)]=int.from_bytes(response2[cell*2:cell*2+2], byteorder = 'big',signed=True)/1000.0
    
    if (response3.endswith(b'\x77')) and (response3.startswith(b'\xdd\x04')):
        rawdat['Vcell1']=int.from_bytes(response3[4:6], byteorder = 'big',signed=True)/1000.0
        rawdat['Vcell2']=int.from_bytes(response3[6:8], byteorder = 'big',signed=True)/1000.0
        rawdat['Vcell3']=int.from_bytes(response3[8:10], byteorder = 'big',signed=True)/1000.0
        rawdat['Vcell4']=int.from_bytes(response3[10:12], byteorder = 'big',signed=True)/1000.0
        
    # Print JSON
    print (json.dumps(rawdat, indent=1, sort_keys=False))

    # Wait for 18 seconds before requesting data again
    time.sleep(18)
