<br/>
<p align="center">
    <img src="https://odoo15.pekaway.de/docimages/logo/vanpi_logo.png" alt="Logo" >

  <p align="center">
    ALL IN ONE RASPBERRY BASED MOBILE SMART HOME ENVIRONMENT 
    <br/>
    <br/>
    <a href="https://pekaway.de/docs"><strong>Explore the docs »</strong></a>
    <br/>
    <br/>
    <a href="https://demo.pekaway.de/">View Frontend Demo</a>
  </p>
</p>



## Table Of Contents

* [About the Project](#about-the-project)
* [Getting started](#getting-started)
  * [Quickstart](#prerequisites)
  * [Manual](#manual)
  * [Installation Script](#installation)
* [Software Stack](#usage)
  * [Node-Red]
  * [Python]
  * [communications]
* [Hardware](#Hardware)
  * [Introduction]
  * [HAT]
  * [Relayboard]
  * [Dimmy]
  * [GPIO expander]
  * [WIFI Relays]
* [Supported Devices](#devices)
  * [Battery]
  * [Water]
  * [Heater]
  * [other]
 * [Mobile App](#mobile APP)

* [Hardware/Project-Overview](#Hardware/Project-Overview) 
* [License](#license)
* [Authors](#authors)
* [Acknowledgements](#acknowledgements)


## About The Project

This project has resulted from a hobby DIY VAN project to combine the variety of displays and hardware in the VAN and caravan area and to make the easy installation possible. 

We took care of a simple startup to make this project also accessible for non-programmers. Take a look at the Quickstarts. 

For the developers is a Node-Red backend and various Python scripts for expansion and improvement ready. 

<p align="left">
    <a href="https://vanpi.de"><img src="https://github.com/KarlPekaway/VAN-PI/blob/main/assets/shop.jpg" alt="Logo" width="100"> </a>
 </p>
 
**you can find the hardware for this project in our store, or just built it yourself**
 
# Getting started
## Quickstart

- [QUICKSTART HAT](https://github.com/KarlPekaway/VAN-PI/blob/main/Quickstarts/ENG_VanPiHat_Quickstart.pdf)
- [QUICKSTART Relayboard](https://github.com/KarlPekaway/VAN-PI/blob/main/Quickstarts/ENG_VanPiRelayboard_Quickstart.pdf)
- [QUICKSTART Dimmy](https://github.com/KarlPekaway/VAN-PI/blob/main/Quickstarts/ENG_PekawayDIMMY_Quickstart.pdf)
- [QUICKSTART Dimmy](https://github.com/KarlPekaway/VAN-PI/blob/main/Quickstarts/ENG_VanPiShunt_Quickstart.pdf)





## Manual

- [VAN PI SYSTEM MANUAL](https://github.com/KarlPekaway/VAN-PI/blob/main/Manual/Manuel%20VANPI%201.2.pdf)


## Installation Script

# Supported Devices
  ## Battery
  - Bluetooth BMS:<br>
    - JBD BMS SYSTEMS e.g. Liontron Batterys 
    - DALY BMS (in development)
    - VICTRON SMART SHUNT BLE **in development**
  - wired:<br>
    - VICTRON SMART SHUNT VE.Direct
    - DALY BMS UART BLUETOOTH (6pin)
    - DALY BMS UART MONIT (3pin)
    - JBD BMS UART PORT
  
  - analog Shunt:<br>
    - Measuring the voltage drop across a SHUNT using the ads1115 on the VAN PI relay board and the VAN PI HAT. Voltage measurement via a voltage divider. Readout via Pythonscript, data is sent to Node-Red via a BottleWebserver. (data remain in the RAM and are written to the SD only every 5min).  
  
  
  - ESP32-C3 INA226 SHUNT: <br>
    - standalone Esp32-c3 based WIFI Shunt. Measure the current, SOC, Battery Voltage. MQTT and BLE are to be supported  **in development**
  
  
  ## Water
  - resistance sensor:<br>
  on the Relayboard and the HAT is a voltage divider section to read the variable resistance of any resistance Sensor you want. It uses the same ads1115 as the analog shunt. The Shunt Pythonscript reads also the ads1115 fot the waterlevel. 
  - capacitve sensor:<br>
  The Relayboard and the HAT has a jumper section to remove the voltage divider section to read directly voltage up to 3.3V to the ADS1115. 
  typical sensors:
    - Votronic FL
    - Votronic 15-50K, 12-24K 
    - CBE sensors
    
  - Flow sensors:<br>
  you can also connect flowsensors to the system via a gpio. it is read out in Node-Red directly
  
  - other: <br>
    - Gobius Pro **in development** 
    
  - TOP/Bottom calibration, Votronic direct calibration (2,4V), 10 Point Calibration **in development**
    
  
  ## Heater
  
 - Autoterm 2D/4D (twin kit **in development**)
 - Webasto W-Bus <=3.5 - *tested with a Thermo Top V water heater* 
 - Chinese Diesel Heater *blue wire* - Arduino NANO Serial Interface
 - Truma INET **in development**
 - LF BROS via 433mhz 
 
   
  ## Displays
  
  - HDMI: <br>
  we are using a headless system on the official release. But you can install our system on any desktop version via the install script and then use the normal webinterface as your display 
  
  - Nextion via UART:<br>
  
  with our RJ45 UART adapter we can connect a Nextion display to the system via an RJ45 ethernet cable. It provides 5V DC and the 3.3V UART for the communication. We do not have an official VAN PI Nextion Image yet. You can find information about the protocol in the docs to build your own .tft file. 
  
  - Sonoff NS Wifi Panel: <br>
   We support the NS Panel and hat setup a special VAN PI TFT file for. The Data is send via MQTT. Please check this installation quide **in development**
 
 

# VANPI HARDWARE

## Rekayboard

## HAT

## SHUNT

## RJ45 UART

## USB AUTOTERM

## USB K-Line

## USB JST

## ESP32-C3 Shunt

## Dimmy Mosfetboard

## Touchsreen

## ESP32-C3 LIN BUS


## Hardware/Project-Overview

| Hardware | Satus | Software | compatible devices | current stable version | current beta | 
|----------|----------|----------|----------|----------| ----------|
| VAN PI RELAY BOARD | actice | VAN PI OS | all VAN PI Hardware  | V 1.0.4 | V1.1.0b2 |
| VAN PI HAT | active |- | all VAN PI Hardware | - | V1.1.0b2 |
| VAN PI SHUNT | active | - | VAN PI OS & VAN PI HAT <br> VAN PI RELAYBOARD | - | - |
| VAN PI RJ45 UART | active |  - | VAN PI OS | - | - |
| VAN PI USB AUTOTERM  | actice | - | VAN PI OS | - | V1.1.0b2 |
| VAN PI USB K-line  (Webasto)| actice | - | VAN PI OS | - | V1.1.0b2 |
| VAN PI USB UART JST (Victron)| actice | - | VAN PI OS |
| VAN PI ESP32-c3 Shunt | in development | VAN PI SHUNT32  | VAN PI OS / MQTT | VANPI SHUNT32 1.0 |
| VAN PI Dimmy | active | PekawayMota / I2C | VAN PI OS / MQTT | PekawayMota 1.1 |  -
| VAN PI Touchscreen (nextion)| in development | VAN PI NEXTSCREEN |VAN PI OS <br> Node-red <br> Nextion HMI | - | - |
| DS18B20 | active | VAN PI OS  |  one wire bus - Rasbpberry |
| resistance tank sensor | active | VAN PI OS | VAN PI HAT <br> VAN PI RELAYBOARD |  - | - |
| capacitve tank sensor | active | VAN PI OS | VAN PI HAT <br> VAN PI RELAYBOARD |  - | - |
| ESP32-c3 LIN BUS | in development | VAN PI LIN32 | VAN PI OS / MQTT |  - | - |



#Software

## Node-Red

## Python 

## Communictation

## Other 


# FLASHTOOLS

Here you can find some tools to flash your Hardware. 
 
## Online Flasher

## Onboard Flasher

## SD IMAGE burn 



