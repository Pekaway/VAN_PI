
<p align="center">
    <img src="https://raw.githubusercontent.com/Pekaway/VAN_PI/main/assets/logo/vanpi_logo.png" alt="Logo" >

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

## VAN PI OS 1.1.0
- [Download](https://links.vanpi.de/downloads.html)

 
# Getting started

## Quickstart

- [QUICKSTART HAT](https://github.com/Pekaway/VAN_PI/blob/main/Hardware/HAT/ENG_VanPiHat_Quickstart.pdf)
- [QUICKSTART Relayboard](https://github.com/Pekaway/VAN_PI/blob/main/Hardware/Relayboard/ENG_VanPiRelayboard_Quickstart.pdf)
- QUICKSTART Dimmy [Standalone](https://cdn.shopify.com/s/files/1/0755/7287/1503/files/VPI-DIM-PCB_Standalone_Quickstart.pdf?v=1689619188) | [Wired](https://cdn.shopify.com/s/files/1/0755/7287/1503/files/VPI-DIM-PCB_Wired_Quickstart.pdf?v=1689619212) | [WiFi](https://cdn.shopify.com/s/files/1/0755/7287/1503/files/VPI-DIM-PCB_WiFi_Quickstart.pdf?v=1689619206)
- [QUICKSTART Shunt Wired](https://cdn.shopify.com/s/files/1/0755/7287/1503/files/VPI-SHU_Quickstart.pdf?v=1685610402)






## Manual

- [VAN PI SYSTEM MANUAL](https://github.com/Pekaway/VAN_PI/blob/main/Manual/Manuel%20VANPI%201.2.pdf)


## Installation Script

If you don't want to use the system as a headless system you can use our installation script.


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
:<br>
    - Measuring the voltage drop across a SHUNT using the ads1115 on the VAN PI relayboard and the VAN PI HAT. Voltage measurement is done using a voltage divider. A Python script reads the data and makes it accessible by providing a Bottle webserver (port 8080), Node-RED then checks the endpoint(s) to get the values. Data remains in the RAM and is written to the SD-Card every 5min.
  
  
  - ESP32-C3 INA226 SHUNT: <br>
    - standalone Esp32-c3 based WIFI Shunt. Measures the current, SOC, Battery Voltage. MQTT and BLE will be supported  **in development** [Check our Patreon](https://www.patreon.com/posts/wir-suchen-fur-91149815)
  
  
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
  
 - Autoterm 2D/4D (twin kit **in development**)
 - Webasto W-Bus <=3.5 - *tested with a Thermo Top V water heater*
 - [Chinese Diesel Heater *blue wire* - Arduino NANO Serial Interface](https://vanpi.de/blogs/tutorials/china-diesel-heater-adapter-bauen)
 - Truma INET **in development**
 - [LF BROS via 433mhz (needs to be activated in the backend since v1.1.0, WiringPI may need to be installed)](https://vanpi.de/blogs/tutorials/lfbros-heizung-mit-433mhz-steuern)
 
   
  ## Displays
  
  - Web interface: <br>

Using the Node-RED web interface, any device can be used as a display. Here it can be reached under http://"IP":1880/ui or alternatively under http://van.pi.
  
  - HDMI: <br>
  VAN PI OS is based on a headless Debian/Raspbian image. You can install the software stack on Ubuntu/Debian based desktop versions with the install script and then use the normal webinterface as your display. Please be aware that manual adjustments may need to be done.
  
  - Nextion via UART:<br>
  
  With the RJ45 UART adapter we can connect a Nextion display to the Relayboard/HAT via an RJ45 ethernet cable. It provides 5V DC and 3.3V UART for communication. We do not have an official VAN PI Nextion image yet. You can find information about the protocol in the docs to build your own .tft file. 
  
  - [Sonoff NS Wifi Panel:](https://pekaway.de/blogs/tutorials/sonoff-ns-panel-wifi-touchscreen-v1-0) <br>
   We support the NS Panel and have prepared a VAN PI tft file for it. The data is send with MQTT. Please check this installation quide **in development**

## Other
 
 - [MaxxFan](https://pekaway.de/blogs/tutorials/maxxfan-uber-infrarot-steuern)
	 - wired
	 - IR

- GOK Senso4s
 

# VAN PI Hardware

## [Relayboard PCB](https://vanpi.de/products/van-pi-relayboard)

## [HAT PCB](https://vanpi.de/products/van-pi-hat)

## [SHUNT](https://vanpi.de/products/van-pi-messshunt) [100A](https://vanpi.de/products/van-pi-messshunt?variant=46638228209999)/[200A](https://vanpi.de/products/van-pi-messshunt?variant=46638228242767)/[300A](https://vanpi.de/products/van-pi-messshunt?variant=46638228275535)

## [RJ45 UART](https://vanpi.de/products/van-pi-rj45-uart-adapter)

## [USB AUTOTERM](https://vanpi.de/products/van-pi-usb-jst-fur-autoterm)

## [USB K-Line](https://vanpi.de/products/van-pi-usb-k-bus-fur-webasto)

## [USB JST](https://vanpi.de/products/van-pi-usb-jst-fur-autoterm)

## [Dimmy PCB](https://vanpi.de/products/van-pi-dimmy-pcb)

## ESP32-C3 Shunt **in development**

## ESP32-C3 LIN BUS **in development**


## Hardware/Project-Overview

| Hardware | Satus | Software | compatible devices | current stable version | current beta |
|----------|----------|----------|----------|----------| ----------|
| VAN PI RELAY BOARD | actice | VAN PI OS | all VAN PI Hardware  | v1.1.1 | v1.1.0b2 |
| VAN PI HAT | active |- | all VAN PI Hardware | v1.1.1 | v1.1.0b2 |
| VAN PI SHUNT | active | - | VAN PI OS & VAN PI HAT <br> VAN PI RELAYBOARD | - | - |
| VAN PI RJ45 UART | active |  - | VAN PI OS | - | - |
| VAN PI JST USB AUTOTERM  | actice | - | VAN PI OS | - | v1.1.0b2 |
| VAN PI USB K-line  (Webasto)| actice | - | VAN PI OS | - | v1.1.0b2 |
| VAN PI USB UART JST (Victron)| actice | - | VAN PI OS |
| VAN PI Dimmy | active | PekawayMota / I2C / Standalone | VAN PI OS / MQTT | PekawayMota 1.1 |  -
| DS18B20 | active | VAN PI OS  |  one wire bus - Rasbpberry |
| resistance tank sensor | active | VAN PI OS | VAN PI HAT <br> VAN PI RELAYBOARD |  - | - |
| capacitve tank sensor | active | VAN PI OS | VAN PI HAT <br> VAN PI RELAYBOARD |  - | - |
| ESP32-c3 LIN BUS | in development | VAN PI LIN32 | VAN PI OS / MQTT |  - | - |
| VAN PI ESP32-c3 Shunt | in development | VAN PI SHUNT32  | VAN PI OS / MQTT | VANPI SHUNT32 1.0

## compatible PEKAWAY hardware
- Pekaway Touchdisplay
- Pekaway IOT Bridge



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


# Support the Project

## Patreon

We run a german patreon account on which we publish further tutorials. These tutorials will be uploaded to our public homepage about 6 months later.

If you like our project feel free to support it:

[VAN PI by Pekaway | All In One Campercontrol System | Patreon](https://www.patreon.com/vanpibypekaway)

## Links
<a target="_blank" href="https://forum.pekaway.de/">Forum</a> --- <a target="_blank" href="https://instagram.com/peka.way">Instagram</a> --- <a target="_blank" href="https://vanpi.de">Homepage</a> --- <a href="https://www.youtube.com/channel/UCS6Vaan7JFox6euCvOEycmA">YouTube</a> --- <a href="https://vanpi.de/pages/contact">Contact</a>
