#!/usr/bin/env python3

# GOK Senso4s Plus
# Get Values from Senso4s Plus and print as hexadecimal integer
#
# Issues:
# Sometimes the connections does not work "connect error: Function not implemented (38)" : dont know why
# Sometimes there are no values "Characteristic value was written successfully" : dont know why
# Sometimes the connections does not work without any error : there might be another client connected
# "Device or resource busy" : there might be still an open connection on the client, restart your bluetooth if you can't find it
#

import argparse
import pexpect

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", required=True)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

# Connetion 1: Set handle 0x000b to value 0100 to enable notification (otherwise it'll always return the innitial value)
child = pexpect.spawn("gatttool -t random -b {0} --char-write-req --handle=0x000f --value=0100".format(args.device))


# await reponse:
for attempt in range(10):
    try:
        if args.v: print("Task1: Scale connecting (Try:", attempt+1, ")")
        child.expect("Characteristic value was written successfully", timeout=1)
    except pexpect.TIMEOUT:
        if args.v==2: print(child.before)
        continue
    else:
        if args.v: print("Notifications enabled on handle=0x000f")
        break
else:
    if args.v: print ("Scale Connect timeout! Exit")
    child.sendline("exit")
    print ("Connection timed out!")
    exit()

# Close connection 1:
if args.v: print("Task1 finished, disconnecting")
child.sendline("disconnect")
child.sendline("exit")

# Run gatttool interactively.
child = pexpect.spawn("gatttool -I -t random -b {0}".format(args.device))

# Connect to the device
for attempt in range(10):
    try:
        if args.v: print("Task2: Scale connecting (Try:", attempt+1, ")")
        child.sendline("connect")
        child.expect("Connection successful", timeout=1)
    except pexpect.TIMEOUT:
        if args.v==2: print(child.before)
        continue
    else:
        if args.v: print("Scale connection successful")
        break
else:
    if args.v: print ("Scale Connect timeout! Exit")
    child.sendline("exit")
    print ("Connection timed out!")
    exit()    


# Request data until data is recieved or max attempt is reached
# Voltage and other information
for attempt in range(1):
    try:
        resp=b''
        if args.v: print("Scale requesting data 1 (Try:", attempt+1, ")")
        child.sendline("char-read-uuid 00007082-a20b-4d4d-a4de-7f071dbbc1d8")
        child.expect("handle: 0x000e \t value: ", timeout=5)
        child.expect("\r\n", timeout=0)
        if args.v: print("Scale received data 1")
        if args.v==2: print("Scale answer 1: ", child.before)
        resp+=child.before
    except pexpect.TIMEOUT:
        continue
    else:
        break
else:
    resp=b''
    if args.v: print ("Scale Answering timeout!")
    if args.v==2: print(child.before)


# Close connection
if args.v: print("Scale disconnecting")
child.sendline("disconnect")
child.sendline("exit")


if args.v: print("Response 1:", resp)

resp = resp[:-1]

# Print response
print (resp)
