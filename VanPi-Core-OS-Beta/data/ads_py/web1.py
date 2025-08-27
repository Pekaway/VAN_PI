from bottle import route, run
from threading import Thread
import Adafruit_ADS1x15
import time 
import json
import sqlite3
import os
import random
from sqlite3 import Error

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

def thread1(threadname):
    
    @route('/setI/<factor>')
    def setFactor(factor=100):
        global factorI
        factorI=factor
        try:
         conn = sqlite3.connect(r"/home/pi/pekaway/pythonsqlite.db")
         cursorObj = conn.cursor()
         ssql= 'UPDATE tbl_default_val SET maxval = '+ int(factor)+' where id = 1'
         cursorObj.execute(ssql)
         conn.commit()
        except:
         print("errorUpdateShunt")
        return str(factor)
    
    @route('/setMaxWH/<MaxWH1>')
    def setMaxWH1(MaxWH1=1900000):
        global MaxWatthours
        MaxWatthours=MaxWH1
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
        


         ssql= 'UPDATE tbl_default_val SET maxval = '+ int(factor)+' where id = 3'
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
        global level1
        global level2
        global level3
        global level4
        retStr='{"level1":"'+str(level1)+'", "level2":"'+str(level2)+'","level3":"'+str(level3)+'","level4":"'+str(level4)+'"}'
        return retStr     
    
    @route('/shunt')
    def getShunt():
        global watthours
        global factorI
        global amps
        global volts
        global MaxWatthours

        retStr='{"volt":"'+str(volts)+'", "amps":"'+str(amps)+'","watthours":"'+str(watthours)+'","Shuntfaktor":"'+str(factorI)+'","MaxWatthours":"'+str(MaxWatthours)+'"}'
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
 
 
def thread2(threadname): 
    global VArr,watthours,timeDiff,factorI,MaxWatthours,level1,level2,level3,level4,count,volts,amps,checknumber 
    GAIN16 = 16
    GAIN2_3= 2/3
    # Create an ADS1115 ADC (16-bit) instance.
    #shunt  production board 4a  -  prototyp 4b  
    adc = Adafruit_ADS1x15.ADS1115(0x4a)
    #level   production board 48 - prototyp 48
    adc2 = Adafruit_ADS1x15.ADS1115(0x48)

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
        micros = int(round(time.time() * 1000000))
        Io = adc.read_adc_difference(0, gain=16)
        Vo = adc.read_adc_difference(3, gain=2)
        I = (0.256*Io/32767)*(int(factorI)/0.075)
        amps=I
        if(amps > 0):
              amps = 0 - amps
        else:
              amps = amps * -1

     

     
                
      



        
        
        
        V = (2.048*Vo/32767)*11.9
        V = V+0.6
        volts=V * -1
        
        watthours = watthours + V*amps*timeDiff/(1000000*60*60) #W=V*I*t      

        
        if(watthours > int(MaxWatthours)):
            watthours = MaxWatthours
            
        tVI = [micros, V, I]
       

      
        if(count > 5):
             level1 = adc2.read_adc(0, gain=1)
             level2 = adc2.read_adc(1, gain=1)
             level3 = adc2.read_adc(2, gain=1)
             level4 = adc2.read_adc(3, gain=1)
             count=0
             print("ads THREAD running")
             checknumber = random.randint(1, 1000000)
          

                
       
        
        time.sleep(0.1)
        count=count+1
        
        
 
        tLEV = [level1, level2]
         

        if len(VArr) > 10:
            VArr.pop(0)
        VArr.append(tVI)
      
 
        if len(VArr2) > 2:
            VArr2.pop(0)
        VArr2.append(tLEV)        
        
        totime= int(round(time.time() * 1000000))
        while ( totime - micros) < 125000: #8 samples/S = 125000 us
            totime = int(round(time.time() * 1000000))
        timeDiff =  totime - micros        
       
        
def thread3(threadname):
    global watthours,watthours2

    def sql_table(con):
      if os.path.isfile(r"/home/pi/pekaway/pythonsqlite.db"):
             print("Exists")
      else:
        cursorObj = con.cursor()
        cursorObj.execute('DROP table if exists tbl_energy')
        cursorObj.execute('DROP table if exists tbl_energy2')
        cursorObj.execute('DROP table if exists tbl_default_val')
        con.commit()
        cursorObj = con.cursor()
        cursorObj.execute("CREATE TABLE tbl_energy(id integer PRIMARY KEY, dateint integer, wh real)")
        cursorObj.execute("CREATE TABLE tbl_energy2(id integer PRIMARY KEY, dateint integer, wh real)")
        con.commit()
        cursorObj = con.cursor()
        cursorObj.execute("CREATE TABLE tbl_default_val(id integer PRIMARY KEY, maxval integer)")
        con.commit()
        cursorObj = con.cursor()
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
        
    def sql_update(con,t,wh,wh2):
        cursorObj = con.cursor()
        ssql= 'UPDATE tbl_energy SET dateint = '+ str(t)+',wh = '+ str(wh) +' where id = 1'
        cursorObj.execute(ssql)
        ssql= 'UPDATE tbl_energy2 SET dateint = '+ str(t)+',wh = '+ str(wh2) +' where id = 1'
        cursorObj.execute(ssql)
        con.commit()
      
        
    conn = sqlite3.connect(r"/home/pi/pekaway/pythonsqlite.db")
    sql_table(conn)
    
    
    while True:
        t= int(round(time.time() * 1000000))
        sql_update(conn,t,watthours,watthours2)
        print("DataBase THREAD running, write successful")
        time.sleep(100)  #5mins  
 
thread1 = Thread(target=thread1, args=("Thread-1",)) 
thread2 = Thread(target=thread2, args=("Thread-2",))
thread3 = Thread(target=thread3, args=("Thread-3",)) 
 
thread1.start() 
thread2.start()
thread3.start() 
 
thread1.join() 
thread2.join()
thread3.join()
