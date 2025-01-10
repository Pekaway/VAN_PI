# original script to read shunt (RJ11) data and water levels on Pekaway VANPI OS v2.x.x (Debian Bookworm)

import json
import os
import random
import sqlite3
import time
from threading import Thread

import adafruit_ads1x15.ads1115 as ADS
import board
import busio
from adafruit_ads1x15.analog_in import AnalogIn
from bottle import route, run

# Initialize variables
a = 0  # global variable 
VArr = []
VArr2 = []

timeDiff=0.0
watthours=0.0
MaxWatthours=1950
watthours2=0.0
MaxWatthours2=1900000
factorI=200
level1=0
level2=0
level3=0
level4=0
amps=0
volts=0
count=0
checknumber=0

# Initialize I2C bus and ADC instances
i2c = busio.I2C(board.SCL, board.SDA)
adc = ADS.ADS1115(i2c, address=0x4a)
adc1 = ADS.ADS1115(i2c, address=0x4a)
adc2 = ADS.ADS1115(i2c, address=0x48)

# Gain settings for ADS1115 (these are approximate, check your exact requirements)
gains = [2/3, 1, 2, 4, 8, 16]

# Check for existing database and load initial data
if os.path.isfile(r"/home/pi/pekaway/pythonsqlite.db"):
    try:
        cn = sqlite3.connect(r"/home/pi/pekaway/pythonsqlite.db")
        cur = cn.cursor()
        cur.execute("SELECT * FROM tbl_energy")
        rows = cur.fetchall()
        for row in rows:
            watthours = row[2]
        
        cur.execute("SELECT * FROM tbl_energy2")
        rows = cur.fetchall()
        for row in rows:
            watthours2 = row[2]
    except:
        print("no data")

# Web server and routes
def thread1(threadname):
    @route('/setI/<factor>')
    def setFactor(factor=100):
        global factorI
        factorI=int(factor)
        try:
            conn = sqlite3.connect(r"/home/pi/pekaway/pythonsqlite.db")
            cursorObj = conn.cursor()
            ssql= 'UPDATE tbl_default_val SET maxval = {} where id = 1'.format(factorI)
            cursorObj.execute(ssql)
            conn.commit()
        except:
            print("errorUpdateShunt")
        return str(factor)

    @route('/setMaxWH/<MaxWH1>')
    def setMaxWH1(MaxWH1=1900000):
        global MaxWatthours
        MaxWatthours=int(MaxWH1)
        try:
            conn = sqlite3.connect(r"/home/pi/pekaway/pythonsqlite.db")
            cursorObj = conn.cursor()
            cursorObj.execute('DROP table if exists tbl_default_val')
            conn.commit()
            cursorObj.execute("CREATE TABLE tbl_default_val(id integer PRIMARY KEY, maxval integer)")
            conn.commit()
            entities2 = (3, MaxWatthours)
            cursorObj.execute('INSERT INTO tbl_default_val(id, maxval) VALUES(?, ?)', entities2)
            conn.commit()
            ssql= 'UPDATE tbl_default_val SET maxval = {} where id = 3'.format(MaxWatthours)
            cursorObj.execute(ssql)
            conn.commit()
        except:
            print("error")
        return str(MaxWH1)

    @route('/setWH/<setWH>')
    def setWH(setWH=1900000):
        global watthours
        watthours=float(setWH)
        return str(setWH)

    @route('/levels')
    def getLevel():
        global level1, level2, level3, level4
        retStr = json.dumps({"level1": level1, "level2": level2, "level3": level3, "level4": level4})
        return retStr

    @route('/shunt')
    def getShunt():
        global watthours, factorI, amps, volts, MaxWatthours
        retStr = json.dumps({"volt": volts, "amps": amps, "watthours": watthours, "Shuntfaktor": factorI, "MaxWatthours": MaxWatthours})
        return retStr

    @route('/WH')
    def WH2():
        global watthours
        WH2_object = json.dumps(watthours)
        return str(WH2_object)

    @route('/tVA')
    def tVA():
        global VArr
        VArr_object = json.dumps(VArr)
        return str(VArr_object)

    @route('/level')
    def tVA2():
        global VArr2
        VArr2_object = json.dumps(VArr2)
        return str(VArr2_object)

    @route('/check')
    def tVA2():
        global checknumber
        VArr2_object = json.dumps(checknumber)
        return str(VArr2_object)

    run(host='localhost', port=8080, debug=True)

# ADC and data handling
def thread2(threadname):
    global VArr, watthours, timeDiff, factorI, MaxWatthours, level1, level2, level3, level4, count, volts, amps, checknumber
    #GAIN16 = 16
    #GAIN2_3= 2/3
    # Create an ADS1115 ADC (16-bit) instance.
    #shunt  production board 4a  -  prototyp 4b  
    #adc = Adafruit_ADS1x15.ADS1115(0x4a)
    #level   production board 48 - prototyp 48
   # adc2 = Adafruit_ADS1x15.ADS1115(0x48)

    if os.path.isfile(r"/home/pi/pekaway/pythonsqlite.db"):
     try:
        cn = sqlite3.connect(r"/home/pi/pekaway/pythonsqlite.db")
        cur = cn.cursor()
        cur.execute("SELECT * FROM tbl_energy")
        rows = cur.fetchall()
        for row in rows:
           watthours = row[2]
           
        cur.execute("SELECT * FROM tbl_energy2")
        rows = cur.fetchall()
        for row in rows:
           watthours2 = row[2]
           
        cur.execute("SELECT * FROM tbl_default_val")
        rows = cur.fetchall()
        for row in rows:
          if(row[0]== 1):
             factorI=row[1]
          elif(row[0]== 3):        
             MaxWatthours=row[1]
         
     except:
        print("error")
    while True:
    
        chan = AnalogIn(adc, ADS.P0, ADS.P1)
        print(f"Channel 0: {chan.value} {chan.voltage}")
        micros = int(round(time.time() * 1000000))
        #adc1.gain = 2#gains[0]
        #adc.gain = 16#gains[5]
        Io = AnalogIn(adc, ADS.P0, ADS.P1)
        #print(f"Io: {Io}")
        #print(f"gain Vo: {adc.gain}")
        print(f"factorI: {factorI}")
        adc.gain = 16  # Set the gain for the ADC
        I = (0.256*Io.value/32768)*(int(factorI)/0.075)
        amps = I
        if(amps > 0):
              amps = 0 - amps
        else:
              amps = amps * -1
        print(f"ampere: {amps}")
        adc1.gain = 2  # Set the gain for the ADC
        Vo = AnalogIn(adc1, ADS.P2, ADS.P3)
        print(f"Channel 3: {Vo.value} {Vo.voltage}")
        V = ((2.048*Vo.value/32768)*11.9)+0.6
        #V += 0.6
        volts = V*-1
        print(f"Volt V: {V}")
        watthours = watthours + V*amps*timeDiff/(1000000*60*60) #W=V*I*t 
        #watthours += V * amps * timeDiff / (1000000 * 60 * 60)  # W=V*I*t

        if watthours > MaxWatthours:
            watthours = MaxWatthours

        tVI = [micros, V, I]

        if count > 5:
            level1 = AnalogIn(adc2, ADS.P0).value
            level2 = AnalogIn(adc2, ADS.P1).value
            level3 = AnalogIn(adc2, ADS.P2).value
            level4 = AnalogIn(adc2, ADS.P3).value
            count = 0
            print("ads THREAD running")
            checknumber = random.randint(1, 1000000)

        time.sleep(0.5)
        count += 1

        if len(VArr) > 10:
            VArr.pop(0)
        VArr.append(tVI)

        tLEV = [level1, level2]

        if len(VArr2) > 2:
            VArr2.pop(0)
        VArr2.append(tLEV)

        totime = int(round(time.time() * 1000000))
        while (totime - micros) < 125000:  # 8 samples/S = 125000 us
            totime = int(round(time.time() * 1000000))
        timeDiff = totime - micros

# Database handling
def thread3(threadname):
    global watthours, watthours2

    def sql_table(con):
        if os.path.isfile(r"/home/pi/pekaway/pythonsqlite.db"):
            print("Exists")
        else:
            cursorObj = con.cursor()
            cursorObj.execute('DROP table if exists tbl_energy')
            cursorObj.execute('DROP table if exists tbl_energy2')
            cursorObj.execute('DROP table if exists tbl_default_val')
            con.commit()
            cursorObj.execute("CREATE TABLE tbl_energy(id integer PRIMARY KEY, dateint integer, wh real)")
            cursorObj.execute("CREATE TABLE tbl_energy2(id integer PRIMARY KEY, dateint integer, wh real)")
            con.commit()
            cursorObj.execute("CREATE TABLE tbl_default_val(id integer PRIMARY KEY, maxval integer)")
            con.commit()
            entities = (1, 0, 0)
            cursorObj.execute('INSERT INTO tbl_energy(id, dateint, wh) VALUES(?, ?, ?)', entities)
            cursorObj.execute('INSERT INTO tbl_energy2(id, dateint, wh) VALUES(?, ?, ?)', entities)
            entities2 = (1, 100)
            cursorObj.execute('INSERT INTO tbl_default_val(id, maxval) VALUES(?, ?)', entities2)
            entities2 = (2, 800000)
            cursorObj.execute('INSERT INTO tbl_default_val(id, maxval) VALUES(?, ?)', entities2)
            entities2 = (3, 7000000)
            cursorObj.execute('INSERT INTO tbl_default_val(id, maxval) VALUES(?, ?)', entities2)
            con.commit()

    def sql_update(con, t, wh, wh2):
        cursorObj = con.cursor()
        ssql = 'UPDATE tbl_energy SET dateint = {}, wh = {} where id = 1'.format(t, wh)
        cursorObj.execute(ssql)
        ssql = 'UPDATE tbl_energy2 SET dateint = {}, wh = {} where id = 1'.format(t, wh2)
        cursorObj.execute(ssql)
        con.commit()

    conn = sqlite3.connect(r"/home/pi/pekaway/pythonsqlite.db")
    sql_table(conn)

    while True:
        t = int(round(time.time() * 1000000))
        sql_update(conn, t, watthours, watthours2)
        print("DataBase THREAD running, write successful")
        time.sleep(100)  # 5mins

# Start threads
thread1 = Thread(target=thread1, args=("Thread-1",)) 
thread2 = Thread(target=thread2, args=("Thread-2",))
thread3 = Thread(target=thread3, args=("Thread-3",)) 

thread1.start() 
thread2.start()
thread3.start() 

thread1.join() 
thread2.join()
thread3.join()
