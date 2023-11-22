#!/usr/bin/env python3

### originally written by BikeAtor, see https://github.com/BikeAtor/WoMoAtor

'''
connect to: 84:28:D7:8F:54:70
notificationhandler installed
services: 
Service <uuid=Generic Attribute handleStart=1 handleEnd=4>
Service <uuid=Generic Access handleStart=5 handleEnd=13>
Service <uuid=6e400001-b5a3-f393-e0a9-e50e24dcca9e handleStart=14 handleEnd=65535>

characteristics: 
Characteristic <Service Changed> uuid: 00002a05-0000-1000-8000-00805f9b34fb handle: 3 properties: INDICATE 
indicate enabled: 4
Characteristic <Device Name> uuid: 00002a00-0000-1000-8000-00805f9b34fb handle: 7 properties: READ 
length: 7 value: b'libatt\x00'
Characteristic <Appearance> uuid: 00002a01-0000-1000-8000-00805f9b34fb handle: 9 properties: READ 
length: 2 value: b'\x00\x00'
Characteristic <Peripheral Preferred Connection Parameters> uuid: 00002a04-0000-1000-8000-00805f9b34fb handle: 11 properties: READ 
length: 8 value: b'\x00\x00\x00\x00\x00\x00\x00\x00'
Characteristic <Central Address Resolution> uuid: 00002aa6-0000-1000-8000-00805f9b34fb handle: 13 properties: READ 
length: 1 value: b'\x00'
Characteristic <0002> uuid: 00000002-0000-1000-8000-00805f9b34fb handle: 16 properties: READ 
length: 2 value: b'\x01\x02'
Characteristic <6e400002-b5a3-f393-e0a9-e50e24dcca9e> uuid: 6e400002-b5a3-f393-e0a9-e50e24dcca9e handle: 19 properties: WRITE NO RESPONSE WRITE 
Characteristic <6e400003-b5a3-f393-e0a9-e50e24dcca9e> uuid: 6e400003-b5a3-f393-e0a9-e50e24dcca9e handle: 21 properties: NOTIFY 
send notify: desc: [<bluepy.btle.Descriptor object at 0xb655ae30>] handle[0]: 22
Characteristic <0001> uuid: 00000001-0000-1000-8000-00805f9b34fb handle: 24 properties: INDICATE 
indicate enabled: 25
'''
import sys
import time
import bluepy.btle
import threading
import logging
import os


# read data from notification
class SupervoltBatteryBluepy():
    pid = os.getpid()
    print ("PID: " + str(pid))
    verbose = False
    mac = None
    disconnectAfterData = False;
    updatetimeS = 1
    lastUpdatetime = time.time()
    lastResettime = time.time()
    maxtime = 70  # seconds
    peripheral = None
    callbackAfterData = None
    lastNotificationTime = time.time()
    
    data = None
    cellV = [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
    totalV = None
    soc = None
    workingState = None
    alarm = None
    chargingA = None;
    dischargingA = None;
    loadA = None
    tempC = [None, None, None, None]
    completeAh = None
    remainingAh = None
    designedAh = None
    
    sleepBetweenRequests = 0.2
    
    def __init__(self,
                 mac=None,
                 data=None,
                 verbose=False,
                 updatetimeS=1,
                 callbackAfterData=None,
                 disconnectAfterData=False):
        self.data = data
        self.verbose = verbose
        # self.parseData()
        self.mac = mac
        self.updatetimeS = updatetimeS
        self.maxtime = self.updatetimeS * 5
        self.callbackAfterData = callbackAfterData
        self.disconnectAfterData = disconnectAfterData
        # self.connect()
    
    def startReading(self):
        if self.mac is not None:
            # start reading values
            threading.Thread(target=self.requestAlways).start()
            if not self.disconnectAfterData:
                threading.Thread(target=self.stayConnected).start()
        else:
            logging.warning("no mac given")
            
    def connect(self):
        try:
            if self.peripheral is None:
                logging.info("connect to: {} (Supervolt)".format(self.mac))
                self.peripheral = bluepy.btle.Peripheral(self.mac, iface=0)
                # MTU must be set for notifications to 247
                # logging.info("mtu: {}".format(self.peripheral.getMTU()))
                self.peripheral.setMTU(246)
                self.peripheral.withDelegate(NotificationHandler(self, verbose=self.verbose))
                if self.verbose:
                    logging.info("notificationhandler installed")
                self.enableNotifications()
            else:
                logging.info("already connected")
        except:
            logging.error(sys.exc_info(), exc_info=True)
            self.disconnect()
    
    def enableNotifications(self):
        data = b"\x02\x00"
        ret = self.peripheral.writeCharacteristic(0x0004, data)
        if self.verbose:
            logging.info("0x0004: " + str(ret) + " " + str(data))
        data = b"\x01\x00"
        ret = self.peripheral.writeCharacteristic(0x0016, data)
        if self.verbose:
            logging.info("0x0016: " + str(ret) + " " + str(data))
        data = b"\x02\x00"
        ret = self.peripheral.writeCharacteristic(0x0019, data)
        if self.verbose:
            logging.info("0x0019: " + str(ret) + " " + str(data))
        if self.verbose:
            logging.info("notifications enabled")
        
    def stayConnected(self):
        try:
            while True:
                try:
                    if self.peripheral is None:
                        self.connect()
                except:
                    logging.error(sys.exc_info(), exc_info=True)
                
                time.sleep(10)
        except:
            logging.error(sys.exc_info(), exc_info=True)

    def disconnect(self):
        try:
            if self.peripheral is not None:
                logging.info("disconnect from: {}".format(self.mac))
                self.peripheral.disconnect()
            else:
                logging.info("not connected") 
        except:
            logging.error(sys.exc_info(), exc_info=True)
        self.peripheral = None
        
    # read data
    def setData(self, data):
        self.data = data
        self.parseData()
        
    # send request to battery for Realtime-Data
    def requestRealtimeData(self):
        data = bytes(":000250000E03~", "ascii")
        # 0x0013 -> 19 -> 6e400002-b5a3-f393-e0a9-e50e24dcca9e
        ret = self.peripheral.writeCharacteristic(0x0013, data)
        if self.verbose:
            logging.debug(":000250000E03~: " + str(ret) + " " + str(data))
    
    # send request to battery for Capacity-Data
    def requestCapacity(self):
        data = bytes(":001031000E05~", "ascii")
        # 0x0013 -> 19 -> 6e400002-b5a3-f393-e0a9-e50e24dcca9e
        ret = self.peripheral.writeCharacteristic(0x0013, data)
        if self.verbose:
            logging.debug(":001031000E05~: " + str(ret) + " " + str(data))

    # try to read values from data
    def parseData(self):
        output = ""
        error = ""
        if self.verbose:
            logging.debug("\nparseData")
        try:
            if self.data is not None:
                if len(self.data) == 128:
                    # print("parse: " + str(type(self.data)))
                    if type(self.data) is bytes:
                        # print("bytes")
                    
                        start = 1
                        end = start + 2
                        self.address = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("address: " + str(self.address))
                            output = self.appendState(output, "address: " + str(self.address))
                        
                        start = end
                        end = start + 2
                        self.command = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("command: " + str(self.command))
                            output = self.appendState(output, "command: " + str(self.command))
                        
                        start = end
                        end = start + 2
                        self.version = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("version: " + str(self.version))
                            output = self.appendState(output, "version: " + str(self.version))
                        
                        start = end
                        end = start + 4
                        self.length = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("length: " + str(self.length))
                            output = self.appendState(output, "length: " + str(self.length))
                        
                        start = end
                        end = start + 14
                        bdate = self.data[start: end]
                        if self.verbose:
                            logging.debug("date: " + str(bdate))
                            output = self.appendState(output, "date: " + str(bdate))
                    
                        start = end
                        end = start + 16 * 4
                        bvoltarray = self.data[start: end]
                        # print("voltarray: " + str(bvoltarray))
                        self.totalV = 0
                        for i in range(0, 11):
                            bvolt = self.data[(start + i * 4): (start + i * 4 + 4)]
                            self.cellV[i] = int(bvolt.decode(), 16) / 1000.0
                            self.totalV += self.cellV[i]
                            if self.verbose:
                                logging.debug("volt" + str(i) + ": " + str(bvolt) + " / " + str(self.cellV[i]) + "V")
                                output = self.appendState(output, "volt" + str(i) + ": " + str(self.cellV[i]) + "V")
                        
                        if self.verbose:
                            logging.debug("totalVolt: " + str(self.totalV))
                            output = self.appendState(output, "totalVolt: " + str(self.totalV))
                        
                        start = end
                        end = start + 4
                        bcharging = self.data[start: end]
                        self.chargingA = int(bcharging.decode(), 16) / 100.0
                        if self.verbose:
                            logging.debug("charging: " + str(bcharging) + " / " + str(self.chargingA) + "A")
                            output = self.appendState(output, "charging: " + str(self.chargingA) + "A")
                        if self.chargingA > 500:
                            # problem with supervolt
                            logging.info("charging too big: {}".format(self.chargingA))
                            error = self.appendState(error, "charging too big: {}".format(self.chargingA))
                            self.chargingA = 0.0
                            
                        start = end
                        end = start + 4
                        bdischarging = self.data[start: end]
                        self.dischargingA = int(bdischarging.decode(), 16) / 100.0
                        if self.verbose:
                            logging.debug("discharging: " + str(bdischarging) + " / " + str(self.dischargingA) + "A")
                            output = self.appendState(output, "discharging: " + str(self.dischargingA) + "A")
                        if self.dischargingA > 500:
                            # problem with supervolt
                            logging.info("discharging too big: {}".format(self.dischargingA))
                            error = self.appendState(error, "discharging too big: {}".format(self.dischargingA))
                            self.dischargingA = 0.0
                        
                        self.loadA = -self.chargingA + self.dischargingA
                        
                        for i in range(0, 4):
                            start = end
                            end = start + 2
                            btemp = self.data[start: end]
                            self.tempC[i] = int(btemp.decode(), 16) - 40
                            if self.verbose:
                                logging.debug("temp" + str(i) + ": " + str(btemp) + " / " + str(self.tempC[i]) + "°C")
                                output = self.appendState(output, "temp" + str(i) + ": " + str(self.tempC[i]) + "°C")
                        
                        start = end
                        end = start + 4
                        self.workingState = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("workingstate: " + str(self.workingState) + " / " + str(self.data[start: end])
                              +" / " + self.getWorkingStateTextShort() + " / " + self.getWorkingStateText())
                            output = self.appendState(output, "workingstate: " + str(self.workingState) + " / " + str(self.data[start: end])
                              +" / " + self.getWorkingStateTextShort() + " / " + self.getWorkingStateText())
                        
                        start = end
                        end = start + 2
                        self.alarm = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("alarm: " + str(self.alarm))
                            output = self.appendState(output, "alarm: " + str(self.alarm))

                        
                        start = end
                        end = start + 4
                        self.balanceState = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("balanceState: " + str(self.balanceState))
                            output = self.appendState(output, "balanceState: " + str(self.balanceState))
                        
                        start = end
                        end = start + 4
                        self.dischargeNumber = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("dischargeNumber: " + str(self.dischargeNumber))
                            output = self.appendState(output, "dischargeNumber: " + str(self.dischargeNumber))
                            
                        start = end
                        end = start + 4
                        self.chargeNumber = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("chargeNumber: " + str(self.chargeNumber))
                            output = self.appendState(output, "chargeNumber: " + str(self.chargeNumber))

                        
                        # State of Charge (%)
                        start = end
                        end = start + 2
                        self.soc = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("soc: " + str(self.soc))
                            output = self.appendState(output, "soc: " + str(self.soc))
                            logging.info("end of parse realtimedata")
                            print(output)

                elif len(self.data) == 30:
                    if self.verbose:
                        logging.debug("capacity") 
                    if type(self.data) is bytes:
                        start = 1
                        end = start + 2
                        self.address = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("address: " + str(self.address))
                            output = self.appendState(output, "address: " + str(self.address))
                        
                        start = end
                        end = start + 2
                        self.command = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("command: " + str(self.command))
                            output = self.appendState(output, "command: " + str(self.command))
                        
                        start = end
                        end = start + 2
                        self.version = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("version: " + str(self.version))
                            output = self.appendState(output, "version: " + str(self.version))
                        
                        start = end
                        end = start + 4
                        self.length = int(self.data[start: end].decode(), 16)
                        if self.verbose:
                            logging.debug("length: " + str(self.length))
                            output = self.appendState(output, "length: " + str(self.length))
                        
                        start = end
                        end = start + 4
                        breseved = self.data[start: end]
                        if self.verbose:
                            logging.debug("reseved: " + str(breseved))
                            output = self.appendState(output, "reseved: " + str(breseved))
                        
                        start = end
                        end = start + 4
                        self.remainingAh = int(self.data[start: end].decode(), 16) / 10.0
                        if self.verbose:
                            logging.debug("remainingAh: " + str(self.remainingAh) + " / " + str(self.data[start: end]))
                            output = self.appendState(output, "remainingAh: " + str(self.remainingAh))
                        
                        start = end
                        end = start + 4
                        self.completeAh = int(self.data[start: end].decode(), 16) / 10.0
                        if self.verbose:
                            logging.debug("completeAh: " + str(self.completeAh))
                            output = self.appendState(output, "completeAh: " + str(self.completeAh))
                        
                        start = end
                        end = start + 4
                        self.designedAh = int(self.data[start: end].decode(), 16) / 10.0
                        if self.verbose:
                            logging.debug("designedAh: " + str(self.designedAh))
                            logging.info("end of parse capacity")
                            output = self.appendState(output, "EndOfParse: true")
                            print(output)
                        
                else:
                    logging.warning("wrong length: " + str(len(self.data)))
        except:
            logging.error(sys.exc_info(), exc_info=True)
            
    def requestAlways(self):
        while True:
            try:
                if True:
                    # start in own thread (background)
                    threading.Thread(target=self.requestOnce).start()
                else:
                    # start in same thread
                    self.requestOnce()
                # wait before for next request
                if False and self.updatetimeS > 2 * self.sleepBetweenRequests:
                    time.sleep(self.updatetimeS - 2 * self.sleepBetweenRequests)
                if True:
                    if self.verbose:
                        logging.info("sleep: {}".format(self.updatetimeS))
                    time.sleep(self.updatetimeS)
            except:
                logging.error(sys.exc_info(), exc_info=True)
                # do not sleep to long after error
                time.sleep(max(2, self.updatetimeS / 2))
                
    def requestOnce(self):
        try:
            self.checkAgeOfValues()

            if self.peripheral is None:
                if self.verbose:
                    logging.info("not connected")
                self.connect()
            if self.peripheral is not None:
                if self.verbose:
                    logging.info("waitForNotifications")
                dataReceived = False
                self.requestRealtimeData()
                if self.peripheral.waitForNotifications(10.0):
                    dataReceived = True
                    # print("notification received")
                    time.sleep(self.sleepBetweenRequests)
                self.requestCapacity()
                if self.peripheral.waitForNotifications(10.0):
                    dataReceived = True
                    # print("notification received")
                    time.sleep(self.sleepBetweenRequests)
                if dataReceived and self.callbackAfterData is not None:
                    self.dataChanged()
                if self.disconnectAfterData:
                    if self.verbose:
                        logging.info("disconnectAfterData")
                    self.disconnect()
            else:
                logging.info("no peripheral")
                # logging.info("no peripheral. sleep {}".format(self.updatetimeS))
                # time.sleep(self.updatetimeS)
        except:
            logging.error(sys.exc_info(), exc_info=True)
            self.disconnect()
    
    def checkAgeOfValues(self):
        if (time.time() - self.lastUpdatetime) > self.maxtime:
            # data is old
            if (time.time() - self.lastResettime) > self.maxtime:
                # last time for reset is also too old, so it will be called every maxtime
                self.lastResettime = time.time()
                logging.info("reset values after time {}/{}".format(self.maxtime, (time.time() - self.lastUpdatetime)))
                self.resetValues()
                self.dataChanged(False)
            
    def resetValues(self):
        try:
            logging.info("reset")
            self.alarm = None
            self.balanceState = None
            for i in range(0, 11):
                self.cellV[i] = None
            self.chargeNumber = None
            self.chargingA = None
            self.completeAh = None
            self.designedAh = None
            self.dischargeNumber = None
            self.dischargingA = None
            self.loadA = None
            self.remainingAh = None
            self.soc = None
            for i in range(0, 4):
                self.tempC[i] = None
            self.totalV = None
            self.version = None
            self.workingState = None
        except:
            logging.error(sys.exc_info(), exc_info=True)
    
    def dataChanged(self, resetTime=True):
        if resetTime:
            self.lastUpdatetime = time.time()
            self.lastResettime = time.time()
        if self.callbackAfterData is not None:
            if self.verbose:
                logging.info("callbackAfterData")
            self.callbackAfterData()
            
    def getWorkingStateTextShort(self):
        if self.workingState is None:
            return "nicht erreichbar"
        if self.workingState & 0xF003 >= 0xF000:
            return "Normal"
        if self.workingState & 0x000C > 0x0000:
            return "Schutzschaltung"
        if self.workingState & 0x0020 > 0:
            return "Kurzschluss"
        if self.workingState & 0x0500 > 0:
            return "Überhitzt"
        if self.workingState & 0x0A00 > 0:
            return "Unterkühlt"
        return "Unbekannt"
        
    def getWorkingStateText(self):
        text = ""
        if self.workingState is None:
            return "Unbekannt"
        if self.workingState & 0x0001 > 0:
            text = self.appendState(text, "Laden")
        if self.workingState & 0x0002 > 0:
            text = self.appendState(text , "Entladen")
        if self.workingState & 0x0004 > 0:
            text = self.appendState(text , "Überladungsschutz")
        if self.workingState & 0x0008 > 0:
            text = self.appendState(text , "Entladeschutz")
        if self.workingState & 0x0010 > 0:
            text = self.appendState(text , "Überladen")
        if self.workingState & 0x0020 > 0:
            text = self.appendState(text , "Kurzschluss")
        if self.workingState & 0x0040 > 0:
            text = self.appendState(text , "Entladeschutz 1")
        if self.workingState & 0x0080 > 0:
            text = self.appendState(text , "Entladeschutz 2")
        if self.workingState & 0x0100 > 0:
            text = self.appendState(text , "Überhitzt (Laden)")
        if self.workingState & 0x0200 > 0:
            text = self.appendState(text , "Unterkühlt (Laden)")
        if self.workingState & 0x0400 > 0:
            text = self.appendState(text , "Überhitzt (Entladen)")
        if self.workingState & 0x0800 > 0:
            text = self.appendState(text , "Unterkühlt (Entladen)")
        if self.workingState & 0x1000 > 0:
            text = self.appendState(text , "DFET an")
        if self.workingState & 0x2000 > 0:
            text = self.appendState(text , "CFET an")
        if self.workingState & 0x4000 > 0:
            text = self.appendState(text , "DFET Schalter an")
        if self.workingState & 0x8000 > 0:
            text = self.appendState(text , "CFET Schalter an")
        
        return text

    def appendState(self, text, append):
        if text is None  or len(text) == 0:
            return append
        return text + " | " + append
    
    def toJSON(self, prefix="battery"):
        self.checkAgeOfValues()
        json = ""
        prefixText = ""
        if prefix is not None:
            prefixText = prefix + "_"
        try:
            if self.tempC[0] is not None:
                json += "\"" + prefixText + "temperature\": {}".format(self.tempC[0]) + ",\n"
            if self.totalV is not None:
                json += "\"" + prefixText + "voltage\": {}".format(self.totalV) + ",\n"
            if self.cellV[0] is not None:
                json += "\"" + prefixText + "voltage_cell0\": {}".format(self.cellV[0]) + ",\n"
            if self.cellV[1] is not None:
                json += "\"" + prefixText + "voltage_cell1\": {}".format(self.cellV[1]) + ",\n"
            if self.cellV[2] is not None:
                json += "\"" + prefixText + "voltage_cell2\": {}".format(self.cellV[2]) + ",\n"
            if self.cellV[3] is not None:
                json += "\"" + prefixText + "voltage_cell3\": {}".format(self.cellV[3]) + ",\n"
            if self.soc is not None:
                json += "\"" + prefixText + "soc\": {}".format(self.soc) + ",\n"
            if self.chargingA is not None:
                json += "\"" + prefixText + "chargingA\": {}".format(self.chargingA) + ",\n"
            if self.dischargingA is not None:
                json += "\"" + prefixText + "dischargingA\": {}".format(self.dischargingA) + ",\n"
            if self.loadA is not None:
                json += "\"" + prefixText + "loadA\": {}".format(self.loadA) + ",\n"
            if self.alarm is not None:
                json += "\"" + prefixText + "alarm\": {}".format(self.alarm) + ",\n"
            if self.workingState is not None:
                json += "\"" + prefixText + "workingState\": {}".format(self.workingState) + ",\n"
                withoutUmlaute = self.getWorkingStateText().replace("Ü", "Ue").replace("ü", "ue")
                json += "\"" + prefixText + "workingStateText\": \"{}\"".format(withoutUmlaute) + ",\n"
                withoutUmlaute = self.getWorkingStateTextShort().replace("Ü", "Ue").replace("ü", "ue")
                json += "\"" + prefixText + "workingStateTextShort\": \"{}\"".format(withoutUmlaute) + ",\n"
            if self.completeAh is not None:
                json += "\"" + prefixText + "completeAh\": {}".format(self.completeAh) + ",\n"
            if self.remainingAh is not None:
                json += "\"" + prefixText + "remainingAh\": {}".format(self.remainingAh) + ",\n"
            if self.designedAh is not None:
                json += "\"" + prefixText + "designedAh\": {}".format(self.designedAh) + ",\n"

        except:
            logging.warning(sys.exc_info(), exc_info=True)
        return json


class NotificationHandler(bluepy.btle.DefaultDelegate):
    notification = None
    verbose = False
    
    def __init__(self, notification, verbose=False):
        self.notification = notification
        self.verbose = verbose
        bluepy.btle.DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        if self.verbose:
            logging.debug("notification: " + str(data))
        self.notification.setData(data)


def main():
    try:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s')
        
        mac = "84:28:D7:8F:XX:XX"
        if len(sys.argv) > 1 and sys.argv[1] is not None:
            mac = sys.argv[1]
        else:
            logging.warning("usage: supervolt_flybat.py <BLE-Address>")
            return
        logging.info("connect to " + mac)
        bluepy.btle.Peripheral(mac, iface=0)
        battery = SupervoltBatteryBluepy(mac=mac, verbose=True, updatetimeS=10, disconnectAfterData=True)
        battery.startReading()
        while(True):
            time.sleep(10000)
    except:
        logging.error(sys.exc_info(), exc_info=True)


if __name__ == '__main__':
    main()
