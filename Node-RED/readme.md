# Node-Red FLOW OVERVIEW

The VAN PI OS uses Node-Red as the main tool to control and manage the system. Around Node-Red several other programs and small helpers have been developed to use the free space. Why Node-Red? We love the freedom of Node-Red, the fast development and the easy customization for other developers. 

The different flows are briefly described here. Many flows are linked to each other by link nodes. To use the data in different places, we work a lot with global variables. 


## Init_flow 

Here mainly all settings and system parameters are stored. Most settings are simply written to files and then reloaded from them. Additionally the different UI elements are loaded. 


## Connections

All serial connections are provided and set here. This includes the routing to the respective flow and the setting of the correct baud rate for the device. 

All connections are 8N1, setting the connection type via "serial request" node is not possible. Therefore, for example with Webasto, the connection must be set manually to 8E1. All settings can be made in the web interface. 

Please note that the USB ports are fixed via Udev rules (same assignment after reboot) and are blocked by Node-Red. If the connections are needed for another tool, they must be removed from Node-Red. 

[Wiki Connections](https://github.com/Pekaway/VAN_PI/wiki/communication)


## Sensor-Dashboard
The sensor dashboard gets the data from the global variables and displays them bundled. Also the "MainBatt" are copied here. This data is then displayed for example for the IOT bridge or on the touchscreen. 

## Pekaway Display 1
VAN PI works partially directly with the closed source Pekaway hardware. This includes the Pekaway Touchdisplay. 
The communication to the display is quite simple and can be easily read out in the flow. So if you want to program your own Nextion display you should have a look at this flow. 

## PekawayDisplay UserData

Various parameters can be sent to the Pekaway touch display here. 

*there are some problems now, will be fixed soon. 

## Relay Controller

Our relays can be switched at various points. To monitor all these places and finally to switch the relays safely we have built this flow. 

The relays are switched via a MCP23017. 
The MCP inputs are also controlled and recorded here in this flow. 

## Wifi Relay

VAN PI Supports Tasmota and Shelly Relays. 
This flow takes care of this. 


## Dimmer Controller

Our Dimmy PCB can be connected via Mqtt and directly via I2C.  This flow provides the control of the actual mosfets. 


## Daly BMS

Here the communication to the Daly BMS is controlled. All request frames are sent and the data is received and written to the global variables. 

## HeaterControls + MaxxFann

The HeaterControls are placed as a layer above the actual heater and control the main functions. At the same time, the connection to other points (API, touch display, etc.) is established. 

The Maxxfan is also controlled and evaluated here. For this, there is a tutorial on how to control the MaxxFan with the help of an Arduino and a program from us. 
Unfortunately there are still problems with the serial connection. 

## Heater Autoterm

## Heater China Diesel 

## Heater Webasto

## JBD/Generic BMS

## Tempsensor DS18B20

## Pekaway Shunt + Waterlevel Python

## HTTP API

## MQTT API

## VE.Direct

## WifiAP

## Monit

## BLE connections

## Wifi TOUCHPANEL

## Config 

## Debug

## Update

## new Verion 

## ONBOARD FLASHER 

## LF BROS *obsolet* 

