# Node-RED FLOW OVERVIEW

The VAN PI OS uses Node-RED as the main tool to control and manage the system. Around Node-RED several other programs and small helpers have been developed to use the free space. Why Node-RED? We love the freedom of Node-RED, the fast development and the easy customization for other developers. 

The different flows are briefly described here. Many flows are linked to each other by link nodes. To use the data in different places, we work a lot with global variables.


## Init_flow

Here mainly all settings and system parameters are stored. Most settings are simply written to files and then reloaded from them. Additionally the different UI elements are loaded.


## Connections

All serial connections are provided and set here. This includes the routing to the respective flow and the setting of the correct baud rate for the device.

All connections are 8N1, setting the connection type via "serial request" node is not possible. Therefore, for example with Webasto, the connection must be set manually to 8E1. All settings can be made in the web interface.

Please note that the USB ports are fixed via Udev rules (same assignment after reboot) and are blocked by Node-RED. If the connections are needed for another tool, they must be removed from Node-RED.

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

In this flow the protocol for Autoterm 4D and 2D is included. The control works via the HeaterControls flow and partly via special controls in the Autotermflow. The communication to the serial port is controlled by the Connections Flow.


## Heater China Diesel

In this flow the protocol for the China parking heater is implemented.

We use an Arduino NANO with a halfduplex softserial to communicate on USB to the "ONE-WIRE" bus of the China heater. Unfortunately there are connection problems after startup. More information about this can be found in the hardware folder "adapter".

## Heater Webasto

In this flow the protocol for the Webasto W-bus <3.5 heater is implemented.

k bus baudrate 2400 8E1 - OBD K-bus cable supported devices:

-   thermo top v (water heater)

the system activate the heater and set the runtime do 255min (max runtime). The temperature and power is then adjusted by the heater itself. When the water Temperature reaches 90°C the heater will shutdown. So you have to get enough heat out of the circuit to prevent this. The heater has two modes full load 5KW and part load 3.2KW.

You can use a normal USB K-BUS OBD Cable.

## JBD/Generic BMS

Evaluation of JBD BMS systems when wired.

## Tempsensor DS18B20

Reading the temperature sensors via Python script and setting the global variables.

We use a Python script because all DS18B20 nodes, Node-RED blocked for 2-3s and no further data was processed.



## Pekaway Shunt + Waterlevel Python

There is a Python script which takes over the evaluation of the ADS1115 and provides the data via bottle web server for Node-RED. So there is no write access to the system and the data stays in the working memory.

The data is read by Node-RED, stored globally and the actual Python script is started.
We don´t use PM2.

## HTTP API

Provides the API endpoints for http access.
https://github.com/Pekaway/VAN_PI/wiki/communication

## MQTT API

Provides the API endpoints for MQTT access.
https://github.com/Pekaway/VAN_PI/wiki/communication

## VE.Direct

Evaluates the ASCII string of the Ve.Direct interface and stores the values device-specific globally.


## WifiAP

Controls the WIFI AP and the access of the Wifi connection to other networks.

## Monit

Provides the monitor tab to display the most important values over the last 24 hours.

## BLE connections

Communication to the BLE devices:

- Gok Senso4s
- JBD BMS/Liontron etc.

The actual query is done in Python scripts via MAC address.

## Wifi TOUCHPANEL

Provides the data for the NS PANEL with our interface.

## Config

Provides the data for the NS PANEL with our interface.

## Debug

A few useful tools to find errors.

## Update

Here the update of the packages and flows is implemented. Also the backup of the user data is done here.

## new Version

A few tools we need when we release a new version.


## ONBOARD FLASHER

Node-RED restarts and loads our onboard flasher. This can then be used to flash various devices such as the Esp32/Esp8266 for the dimmy.

## LF BROS *obsolet*

Control of LF Bros heating via 433mhz. Is no longer active since we used "wiringPi" for this. This blocked us but the other UARTS from the RPI4 so we no longer have it as standard.

