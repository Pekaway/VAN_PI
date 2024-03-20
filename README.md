



<p align="center">
    <img src="https://raw.githubusercontent.com/Pekaway/VAN_PI/main/assets/logo/vanpi_logo.png" alt="Logo" width="250" >

  <p align="center">
    ALL IN ONE RASPBERRY BASED MOBILE SMART HOME ENVIRONMENT
    <br/>
    <br/>
    <a target="_blank" href="https://github.com/Pekaway/VAN_PI/wiki"><strong>Explore the docs</strong></a>
    <br/>
    <br/>
    <a target="_blank" href="https://demo.pekaway.de/">View Frontend Demo</a>
    <br/>
    <br/>
    <a target="_blank" href="https://forum.pekaway.de/">Forum</a>
  </p>

  <p align="center">### This repository is currently under construction and not yet finished!</p>

## Table Of Contents

* [About the Project](#about-the-project)
* [Releases](#Releases)
* [Getting started](#getting-started)
* [Supported Devices](#Supported-Devices)
* [VAN PI Hardware](#VAN-PI-Hardware)
* [Software](#Software)
* [Flashtools](#flashtools)
* [Support the Project](#patreon)




## About The Project

This project has resulted from a hobby DIY VAN project to combine the variety of displays and hardware in the VAN and caravan area and to make the easy installation possible.

Everything is built around the Raspberry PI, both software and hardware.


We took care of a simple startup to make this project also accessible for non-programmers. Take a look at the Quickstarts.

For the developers is a Node-RED backend and various Python scripts for expansion and improvement ready.

 
**you can find the hardware for this project in our store, or just built it yourself**

<p align="left">
    <a href="https://vanpi.de"><img src="https://github.com/Pekaway/VAN_PI/blob/main/assets/shop.png?raw=true" alt="Logo" width="100"> </a>
 </p>
 
[SHOP NOW](https://www.vanpi.de)


# Releases

## VAN PI OS 2.0.0
- [Download](https://links.vanpi.de/downloads.html)

## Installation Script

If you don't want to use the system as a headless system you can use our installation script.


# Pekaway Hardware for VAN PI 

## VAN PI CORE

Core of the system that brings all devices together. 

[Pekaway/VAN-PI-CORE (github.com)](https://github.com/Pekaway/VAN-PI-CORE)
## VAN PI DIMMY

7 Channel PWM Dimmer Board 
Works wired without an extra chip. 
You can use it with an ESP32 (wemos) as a standalone Board and you can also use connect it via PekawayMOTA (Tasmota) per Wifi/MQTT to the VAN PI OS. 

[Pekaway/DIMMY: dc PWM LED Controller (github.com)](https://github.com/Pekaway/DIMMY)
## Pekaway Smart Shunt ESP32-C3

ESP32-C3 INA2226 200A Shunt. 
Works with the VAN PI OS via BLE but you can also use it standalone. 

[Pekaway/ESP32-BLE-WIFI-SHUNT: ESP32-C3 Battery Monitor Shunt (github.com)](https://github.com/Pekaway/ESP32-BLE-WIFI-SHUNT)



## Pekaway Touchscreen

7" capactive Touchscreen. 
Based on Nextion and the Nextion Studio. 
Connect to the System VAN PI System via "RJ45 UART" 

Advantages compared to an Andorid/IOS tablet. -> much lower standby power, fast wake-up time, easy integration, is permanently installed and can therefore not be used for other things and is therefore always in the same place. 

[Pekaway Touchdisplay](https://pekaway.de/collections/alle-produkte/products/pekaway-touchdisplay)




## Pekaway IOT Bridge

Connect the system via Wifi to the Mobilnetwork. Comes with build in SIM.
The Bridge uses the local http api. So also here if you want your own software stack. You only have to provide the VAN PI OS API to use the bridges to. 


- 2G Version
	- entry variant 
	- fast enough to read the data from the system. 
Good network coverage. Switching off 2G will still take a while (EU)

- 4G Version
	- uses the normal LTE 4G network. 
LTE-M is still not available in many countries. 
NB-IOT is not stable for our application due to the high latency. 
	- GPS
	- GPS ALARM possible 


- 4G+  
	- same functionality as the 4G version, but with battery backup. The system continues to run even if the main battery is switched off. 





# Supported Devices

 ## Battery
  - Bluetooth BMS:<br>
    - JBD BMS SYSTEMS e.g. Liontron Batterys
		    - dual setup possible check our tutorial page
    - DALY BMS (in development)
    - VICTRON SMART SHUNT BLE **in development**
  - wired:<br>
    - VICTRON SMART SHUNT VE.Direct
    - DALY BMS UART BLUETOOTH (6pin)
    - DALY BMS UART MONIT (3pin)
    - JBD BMS UART PORT
  
  - [analog Shunt](https://cdn.shopify.com/s/files/1/0755/7287/1503/files/VPI-SHU_Quickstart.pdf?v=1685610402)
<br>
    - Measuring the voltage drop across a SHUNT using the ads1115 on the VAN PI relayboard and the VAN PI HAT. Voltage measurement is done using a voltage divider. A Python script reads the data and makes it accessible by providing a Bottle webserver (port 8080), Node-RED then checks the endpoint(s) to get the values. Data remains in the RAM and is written to the SD-Card every 5min.
  
  
- [Pekaway Smart Shunt ESP32-C3](https://github.com/Pekaway/ESP32-BLE-WIFI-SHUNT)


  ## Solarcharger 

  - Renogy:<br>
    - [cyrils/renogy-bt: Python library to read Renogy compatible BT-1 or BT-2 bluetooth modules using Raspberry Pi. (github.com)](https://github.com/cyrils/renogy-bt) 
    - not yet installed in VAN PI OS 

- Pekaway MPPT S20 - via Python Bluetooth read out
	- SHOP LINK

  
  
  ## Water

  - resistance sensor:<br>
  on the Relayboard and the HAT is a voltage divider section to read the variable resistance of any resistance sensor you want to use. It uses the same ADS1115 as the analog shunt. The shunt Pythonscript also reads the ads1115 fot the waterlevels. 
  - capacitve sensor:<br>
  The Relayboard and the HAT have a jumper section to remove the voltage divider section to read voltage directly up to 3.3V to the ADS1115. 
  typical sensors:
    - [Votronic FL](https://vanpi.de/products/votronic-tanksensor-fl-5530)
    - [Votronic 15-50K, 12-24K](https://vanpi.de/products/votronic-tankelektrode-15-50k-5545)
    - CBE sensors
    
  - [Flow sensors](https://pekaway.de/blogs/tutorials/flowsensoren-in-van-pi-einbinden-filter-durchfluss-messen):<br>
  you can also connect flow sensors with gpio. Node-RED will then access the sensors directly).
  We have examples in our tutorial collection. Maybe there will be a fixed integration in the VAN PI OS soon. 
 
  
  - other: <br>
    - Gobius Pro **in development**
   
- Calibration methods:
   - top/bottom calibration,
   - Votronic direct calibration (2,4V)
   - set resistance
   - 10 point calibration **in development**
    
  
 ## Heater
  
 -  Autoterm 2D/4D
 -  Autoterm 2D/4D (twin kit **in development**)
 - Webasto W-Bus <=3.5 - *tested with a Thermo Top V water heater*
 - [Chinese Diesel Heater *blue wire* - Arduino NANO Serial Interface](https://vanpi.de/blogs/tutorials/china-diesel-heater-adapter-bauen)
 - Truma via [danielfett/inetbox.py: A software implementation of something similar to a Truma iNet box (github.com)](https://github.com/danielfett/inetbox.py)
 - [LF BROS via 433mhz (needs to be activated in the backend since v1.1.0, WiringPI may need to be installed)](https://vanpi.de/blogs/tutorials/lfbros-heizung-mit-433mhz-steuern)
 
   
  ## Displays
  
  - Web interface: <br>

Using the Node-RED web interface, any device can be used as a display. Here it can be reached under http://"IP":1880/ui or alternatively under http://van.pi.
  
  - HDMI: <br>
  VAN PI OS is based on a headless Debian/Raspbian image. You can install the software stack on Ubuntu/Debian based desktop versions with the install script and then use the normal webinterface as your display. Please be aware that manual adjustments may need to be done.
  
  - Nextion via UART:<br>
  
  With the RJ45 UART adapter we can connect a Nextion display to the Relayboard/HAT via an RJ45 ethernet cable. It provides 5V DC and 3.3V UART for communication. We do not have an official VAN PI Nextion image yet. You can find information about the protocol in the docs to build your own .tft file. 
  Or just use our Pekaway Touchscreen 
  [Pekaway Touchdisplay](https://pekaway.de/collections/alle-produkte/products/pekaway-touchdisplay)
  
  - [Sonoff NS Wifi Panel:](https://pekaway.de/blogs/tutorials/sonoff-ns-panel-wifi-touchscreen-v1-0) <br>
   We support the NS Panel and have prepared a VAN PI tft file for it. The data is send with MQTT. Please check this installation quide **in development**
   
  - [Pekaway APP](https://pekaway.de/blogs/tutorials/sonoff-ns-panel-wifi-touchscreen-v1-0) <br>
Control the device via our App.  The App is using the http&MQTT API. So if you planing your own software stack. If you provide our API (build in Node-Red) The app will also work on your software. 


 ## GPS
  - GPS via RJ45UART <br>
	  - You can connect a GPS module to the VAN PI Core using the RJ45 UART. All you need is a 3.3V module and a 12V -> 3.3V voltage converter. The module then sends the data to UART1 and is evaluated in Node-Red. Pay attention to the baud rate and check it in the connections Flow if necessary. 


  - GPS via USB 
  - GPS via Pekaway IOT Bridge 4G and 4G+ 

## Other
 
 - MaxxFan
	 - wired -> 
	 - IR -> [Pekaway/maxx-wifi-controller: Maxx Remote Wifi Controller (github.com)](https://github.com/Pekaway/maxx-wifi-controller)

- [Pekaway/I2C-GPIO-extension: I2C Extension for the VAN PI CORE (github.com)](https://github.com/Pekaway/I2C-GPIO-extension)


- GOK Senso4s via Bluetooth read out

- RUUVI TAG BLE Temp and Humidity 
 



# Software

## Node-RED

Node-RED is used as the backend, doing all the calculations and connections. It also serves the frontend dashboard on port 1880. Check the [Wiki](https://github.com/Pekaway/VAN_PI/wiki) to get an overview on how the system works.

## Python

Using some python scripts we can evaluate data coming from the shunt and different sensors. We decided to use Python instead of Node-RED itself to make use of another CPU core, since Node-RED, being a NodeJS application, only uses a single thread.
Get more information about the Python scripts [here](https://github.com/Pekaway/VAN_PI/wiki/shunt). The scripts are included in the "home_pi_pekaway_files.zip" in the [VanPi-OS folder](https://github.com/Pekaway/VAN_PI/tree/main/VanPi-OS) if you want to read through them.

## Communication

VanPi OS offers a HTTP and a MQTT API, which can be used to read and write data. See [Communication](https://github.com/Pekaway/VAN_PI/wiki/communication). Please be advised to not change the existing API functions in Node-RED, because several other hardware/software parts we offer use the API too, such as the IoT Bridge. Feel free to add more endpoints though, in case you need to.

# FLASHTOOLS

Here you can flash your ESPs with our preconfigured software [pekawayMOTA](https://github.com/Pekaway/VAN_PI/wiki/pekawaymota) .

[Online flasher](https://flashesp.pekaway.de) - connect your ESP via USB to your computer and use Google Chrome to flash the device using the online flasher.

Onboard Flasher - You'll find it in the webinterface of the VanPi OS, go to config > system > flashtool. It'll start a different set of flows which will allow you to flash your ESP device when it is connected directly to the Raspberry Pi.

## SD IMAGE flash
We recommend to flash the images with either [Balena Etcher](https://www.balena.io/etcher/) or [Win32DiskImager](https://sourceforge.net/projects/win32diskimager/)



# OTHER SOFTWARE STACKS

Software stack based on VAN PI OS Node-red "Core" functions, supports also the RPI5 and a lot of cool other Features. 

- [nomadPi](https://nomadpi.com/)



MQTT Connector for HomeAssistant etc. 
- [schroeder-robert/vantelligence_connector: A MQTT connector for devices in your camper! (github.com)](https://github.com/schroeder-robert/vantelligence_connector)




# Support the Project

This project lives from its community. We look forward to your support. Only with your support can the project continue to grow and offer you exciting hardware and software. 

## Patreon

We run a german patreon account on which we publish further tutorials. These tutorials will be uploaded to our public homepage about 6 months later.

If you like our project feel free to support it:

[VAN PI by Pekaway | All In One Campercontrol System | Patreon](https://www.patreon.com/vanpibypekaway)

## Links
<a target="_blank" href="https://forum.pekaway.de/">Forum</a> --- <a target="_blank" href="https://instagram.com/peka.way">Instagram</a> --- <a target="_blank" href="https://vanpi.de">Homepage</a> --- <a href="https://www.youtube.com/@VANPIbyPekaway">YouTube</a> --- <a href="https://vanpi.de/pages/contact">Contact</a>
