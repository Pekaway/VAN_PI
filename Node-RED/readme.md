# Node-RED FLOW OVERVIEW

The VanPi OS uses Node-RED as the main tool to control and manage the system. Around Node-RED several other programs and small helpers have been developed and deployed to use the free resources. Why Node-RED? We love the freedom of Node-RED, the fast development and the easy customization for further developments.

The different flows are briefly described here. Many flows are linked to each other by link nodes. To use the data in different places, many global variables are used.


## Init_flow

Here mainly all settings and system parameters are stored. Most settings are simply written to files and then reloaded from them when doing a reboot. Additionally the different UI elements are loaded in this section, some functions do control which parts are displayed in the UI according to the users needs.

## Connections

All serial connections are provided and set here. This includes the routing to the respective flow and the setting of the correct baud rates for the connected devices.

All connections are 8N1, setting the connection type via "serial request" node is not possible. Therefore, for example with Webasto, the connection must be set manually to 8E1. All settings can be made in the web interface (frontend).

Please note that the USB ports are fixed via so called UDEV rules (these make sure to assigne the correct USB-ports after each reboot) and are blocked by Node-RED. If the connections are needed for another tool, they must be removed from Node-RED.

[Wiki Connections](https://github.com/Pekaway/VAN_PI/wiki/communication)


## Sensor-Dashboard
The sensor dashboard gets the data from the global variables and displays them on the frontend. Also the "MainBatt" data is copied here. This data is is then provided for example to the IoT bridge or the touchscreen.

## Pekaway Display 1
VanPi works partially directly with the closed source Pekaway hardware. This includes the Pekaway Touchdisplay.
The communication to the display is quite simple and can be easily read out in the flow. So if you want to program your own Nextion display you should have a look at this flow.

## PekawayDisplay UserData

Various parameters can be sent to the Pekaway touch display.

*there are some problems now, will be fixed soon.

## Relay Controller

Our relays can be switched at various points. To monitor all these places and finally to switch the relays safely we have built this flow.

The relays are switched via a MCP23017.
The MCP inputs are also controlled and recorded in this flow.

## Wifi Relay

VanPi Supports Tasmota and Shelly Relays.
This flow takes care of this.

## Dimmer Controller

Our Dimmy PCB can be connected via Mqtt or directly via I2C.  This flow provides the control of the actual mosfets.

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

We use an Arduino NANO with a halfduplex softserial to communicate on USB to the "one-wire" bus of the China heater. Unfortunately there are connection problems after startup.

## Heater Webasto

In this flow the protocol for the Webasto W-bus <3.5 heater is implemented.

k bus baudrate 2400 8E1 - OBD K-bus cable supported devices:

-   thermo top v (water heater)

The system activates the heater and sets the runtime to 255min (max runtime). The temperature and power is then adjusted by the heater itself. When the water temperature reaches 90°C the heater will shutdown. So you have to get enough heat out of the circuit to prevent this. The heater has two modes: Full load 5KW and part load 3.2KW.

You can use a normal USB K-BUS OBD Cable.

## JBD/Generic BMS

Evaluation of JBD BMS systems when wired.

## Tempsensor DS18B20

A python script is called from this flow that reads DS18B20 sensors and sets the global variables accordingly.

## Pekaway Shunt + Waterlevel Python

A python script takes over the evaluation of the ADS1115 and provides the data via a bottle web server to Node-RED. So there is no write access to the hard drive/SD-card and the data stays in the working memory.

The scirpt is started from Node-RED, the responses are stored globally and the script will be shut down to be requested again after some time.

## HTTP API

Provides the API endpoints for http access.
https://github.com/Pekaway/VAN_PI/wiki/communication

## MQTT API

Provides the API endpoints for MQTT access.
https://github.com/Pekaway/VAN_PI/wiki/communication

## VE.Direct

Evaluates the ASCII string of the Ve.Direct interface and stores the values device-specific globally.


## WifiAP

Controls the WiFi access point and the access of the Wifi connection to other networks.

## Monit

Provides the monitor tab to display some values and system health information.

## BLE connections

Communication to the BLE devices:

- Gok Senso4s
- JBD BMS (Liontron etc.)

The actual query is done in python scripts using the MAC address of the device in use.

## Wifi TOUCHPANEL

Provides the data for the NS PANEL with the Pekaway/VanPi interface.

## Config

The config flow inherits functions for the main configuration, as the name suggests. For example to update the names for the relays or temperature sensors in the frontend, to enable/disable Homebridge and Zigbee and provide buttons to navigate around in the frontend.

## Debug

A few useful tools to find errors and get information about the system.

## Update

Functions to update system packages and flows are implemented here. These will be called when a new release is available and an update is triggered. Also a backup of the user data can be done.

## new Version

A few tools we need when we release a new version. Basically, these are used to clean the system before taking a snapshot of the images, which we provide to download and flash onto the user's system.

## ONBOARD FLASHER

Node-RED restarts and loads a new set of nodes. This can then be used to flash various devices such as the ESP32/ESP8266 for the Dimmy PCB.

# obsolete
## Heater LFBros

Control of LFBros heating device using 433MHz. It is no longer active since we used "WiringPi" for this, which blocked the UART ports from the RPI4, therefore it is no longer available in the default VanPi OS image. The flow is deactivated but left in the VanPi OS image in case someone still wants to use it.