# Update 1.1.1 (05 May 2023)
- fixed mcp inputs not being displayed correctly
- fixed water level 1 error which kept it from taking other values than 0
- fixed error which prevented "main battdata" to be initialised on boot
- changed sampling frequency of PCA9685 to 200 (dimmer section)
- changed http request nodes in Pekaway Shunt flow to use 127.0.0.1 instead of localhost
- added function to start a second Node-RED instance, using a backup flows file
- added a timezone picker in Frontend (Config > System)
- added function that displays the system time in the info tab & altered format of system time in frontend (Config)
______________________________________________________________________________________________________________

# Update 1.1.0 (31 Mar 2023) >> changes mentioned here also include BETA updates for this version!
- added a precompiled .tft file (VanPI_NSPANEL.tft) for the Sonoff NS Panel to ~/pekaway together with the berry driver (autoexec.be), which is needed for the flashing process
    > quickstart NSPanel:
        > install Tasmota via https://tasmota.github.io/install/ (choose "Tasmota32 Sonoff-NSPanel(englisch)" to be flashed)
        > connect the panel to the wifi accesspoint of your RPI
        > use configs as described here: https://docs.nspanel.pky.eu/prepare_nspanel/
        > set MQTT-Broker to "pekaway.local" and topic to "WifiTouch" (case sensitive)
        > go back to the console in tasmota and type:
            > "Backlog UrlFetch http://pekaway.local/autoexec.be; Restart 1" -> downloads the driver from the local filestorage via nginx
            > "FlashNextion http://pekaway.local/nspaneltft" -> flashes the precompiled .tft file
    > a new flow "Wifi TOUCHPANEL" has been added to Node-RED, which also includes examples for the two hardware buttons on the panel
    > added a function to upload your own .tft file to the raspberry (Config > System > System Update > NS Panel)
    > added functions to install the berry driver and flash the .tft file (Config > System System Update > NS Panel)
- added code to the nginx server block to make the berry driver and the .tft file accessible via http
- added check for i2c devices in dimmer flow to prevent showing error messages if Dimmy is not hardwired
    > messages to PCA9865-Node are limited to 10msg/s (1msg every 0.1s)
- added slider to set max_pwm in % as overvoltage protection (config > switches > dimmer section)
- added dimmytemp sensor data to http endpoint /temp (only when set to active in config)
- reworked the function that generates the default wifi ssid to be a bit more randomized
- reworked the function to reset the wifi to use the same process that generates the default wifi ssid
- reworked the update function 
    > it will now download a script from the Pekaway servers and execute to keep it seperated from Node-RED
    > the script can be found at git.pekaway.de
- fixed error that sometimes displayed ble-bms info in textfield for "currently set battery" (config)
- fixed error with libevdev2:armhf package
______________________________________________________________________________________________________________
# Update 1.1.0 BETA2 (09 Feb 2023)
- added functions to control MaxxAir MaxxFan via IR-Transmitter in combination with ESP device
    > Arduino code still needs to be finalized and published
- disabled all LFBros functions systemwide and purged WiringPi to make UART-Port available
- disabled "gpio readall" function from debug tab
- disabled Dimmer 8 (Dimmy board has only 7 channels available)
- added "dimmytemp1/2" to be set as option for inside temp sensor (2 DS18B20 sensors can be connected to the Dimmy board and will sent their data via MQTT)
- added a PCA9865 node to the dimmer section >> Dimmy can now be connected hardwired without the need for an extra Microcontroller (Wemos)
    > if you want to, you can disable the mqtt outputs for the dimmers and set the slider to send data continously instead of "only on release"
- added function to insert SSID for existing Wifi manually
- fixed errors in ~/ble_py/goksens4s.py (was only showing initial values before)
- fixed function to initialise GokSenso4S on startup
- disabled update via USB function in frontend (was leading to errors in some cases)
- added function to turn off BLE Bat/BMS if not reachable
    > will turn off after 6 failed attempts, then try again after 1 hour (can be turned on again by setting the MAC-adress in the config settings)
    > info: if BLE cannot establish a connection, it will kick out Wifi-clients and block new wifi connections as long as the BLE-requests is running
- prepared flows to use a custom cloud mqtt server (see the flow "MQTT API" at the bottom) 
- added Autoterm 4D to the list of supported heaters (not all status info is delivered via the protocol though)
- added a one-time runtimer to the heater controls >> Start the heater, set the timer, heater will stop when time is over
- changed some settings in the "Chinese Diesel Heater" flow, it now works properly with both types of USB-connectors
- reworked display communication to reduce bandwith
- new beta file for touchdisplay (1.0.3B) is also available

#    new packages/installations
    - node-red-contrib-PCA9865
    - node-red-contrib-countdown-2
______________________________________________________________________________________________________________
# Update 1.1.0 BETA (02 Dec 2022)
- Updated Node-RED core to latest version v3.0.2
 > NOTICE: Node-RED hast to be updated manually ("bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)") when using the update function!
- updated npm packages for Node-RED to latest versions
- updated rpi packages to latest versions ("sudo apt upgrade")
- added link in update checker to read full changelog
- set global variable BatteryDataDelivery to empty ("") on first boot
- added some logic to improve the function that rebuilds the UI
- slightly altered notification message when MainBattData is set to "off"
- fixed error when searching for bluetooth battery (liontron/JBD) automatically (the found battery will now also be set automatically)
- added functions to switch relays when using MCP input to have an option to add hardwired buttons/switches to the board
- changed title "WasserLevel Names" to "Water Level Names"
- reworked system time in toolbar to show client time instead of system time (JS function that executes on the client browser)
- changed request interval for bluetooth scale from 20 seconds to 180 minutes so that the scale's battery will not be drained that heavily
- added function to convert the data from gok-senso4s from hexadecimal to decimal
- created HTTP endpoint to set the system time (preparation for IoT-bridge update)
- created HTTP endpoint to turn everything off (relays, w-relays, dimmers)
 > added UI button to turn everything off in Switches Settings
 > added function to save current state before turning everything off in preparation for function to turn everything back on in last known state
 > added MQTT topic to turn everything off
- added switch to enable/disable Zigbee2MQTT
- added button to reach Zigbee2MQTT dashboard directly from NR-Frontend (Wifi Config)
- Zigbee2MQTT dashboard is available on port 8099 (Zigbee2mQTT service will fail to start if no coordinator is connected! It will try to restart every 10s, check the systemd.service for details)
- the auto turn off function in Switch Scheduler/Timer tab now shows the values of the gobal variables as names, instead of "Relay 1, Relay 2...""
- dimmer names now default to "Dimmer 1, Dimmer 2, etc." if names are left empty in frontend
- deactivated USB-update function
- added endpoints to get software version in http/mqtt
- changed monitor chart ranges for temperatures from 6h to 10h
- updated Homebridge to version 1.6.0, updated plugins to latest versions
- fixed error that stopped the update function from working
- fixed error on wifi-relays and homebridge (when firmware is set to shelly, then hb was not notified when w-relay is switched in NR frontend)
- fixed error that last temperature value was kept after sensor was removed, value is now set to "" after removing the sensor
- changed global variable "version" to "currentVersion"
- added two more temperature sensors to be used with the Dimmy board. They can be activated and named in Config -> Sensors tab
 > check flow "Temperature/DS18B20" in Node-RED Backend for details
- error generating new hostkeys on firstboot may appear in v1.0.4 -> fixed by adding a button ("Generate new SSH hostkey") to Config -> Debug -> RPI general information
- disabled swapping system-wide and deleted swapfile /var/swap
- added function to save install date of current version to file and retrieve when checking for updates

#    new packages/installations
    - node-red-node-ui-list
    - node-red-contrib-zigbee2mqtt
    - zigbee2mqtt (https://www.zigbee2mqtt.io/guide/installation/01_linux.html)
______________________________________________________________________________________________________________
# Update 1.0.4 (07 Sep 2022)
- added callback query when resetting water level calibration
- fixed function "searching for backup files" when folder is empty
- reworked upload/download UserData functions
- fixed function for relays "autoturnoff" to work properly after rebooting (delay restarts at time of boot)
- fixed relay tabs showing up properly when deploying while Switches tab is in focus
- fixed function sending MQTT stats every 5min (Wifi-Config -> "Send stats via MQTT")
______________________________________________________________________________________________________________
# Update 1.0.3
- fixed monitoring waterlevels to not show more than 100%
- changed touchdisplay switch (page) from number to string
- reworked building of UI to be more stable
- changed temp2 global variable to be stored as string (fixed to be shown in mobile app, was integer before)
- added global variables to show BMSmax/min data in mobile app from JBD BL/UART BMS
- JBD BMS is now available for usage on all 4 USB ports
- fixed JBD BMS settings (UART)
- fixed JBD BMS calculations for USB and BL connections
- changed Daly BMS flow to show capacity in ampere hours
- added function to generate a new ssh host key on first boot
- added function to clear bash history when generating new image
- added function to clear system volume information when generating new image
- added function to show/hide system time in the toolbar
- changed uptime function for better visibility in monitor tab
- deactivated function that updates relay/wifi-relay labels every 3min
- reworked functions that update switches labels in frontend (update happens when changing to switches tab)
- switches labels now return to default value when names are deleted (instead of showing nothing)
- added function to automatically turn off respective switches after a custom set time
- added schedulers for relays, wifi-relays and dimmers (automatically turn on/off at given times) -> remember to set system time properly or synchronize it automatically (internet access needed)
    - for dimmer events use true/false for fully on/off, or set a value from 0 to 100
- prepared "autooff" variable in HTTP endpoints (not yet in use, will be used when code for IoT-bridge is updated)
- prepared new HTTP endpoint "relayiot" to be used in futere IoT-bridge code update
- added usability off payloads "true"/"false" to be used when switching states of relays/w-relays/dimmers via MQTT
- fixed PIN numbers in "/home/pi/pekaway/433Utils/RPi_utils/codesend.cpp" (line 27) to PIN 4 and "/home/pi/pekaway/433Utils/RPi_utils/RFSniffer.cpp" (line 26) to PIN 3 for 433MHz sender/receiver to work with VANPI Relayboard
______________________________________________________________________________________________________________
# Update 1.0.2
- changed relative paths to absolute paths in ~/pekaway/ads_py/web1.py to resolve issues with database
- created files "ohm1empty" & "ohm1full" (up to #4) to fix error when calibrating water tank sensors
- added function to write ohm data before using the adjustment slider
- changed function to hide/show bms info to fix error when updating UI
______________________________________________________________________________________________________________
# Update 1.0.1
- downgraded OS back to Debian 10 Buster due to problems with ADS packages
- changed user back to pi to simplify filepaths
- changed DHCP range to 192.168.4.2-192.168.4.50
- added van.pi to dnsmasq.conf
- installed bottle webserver (python) as user pi
- fixed paths in wifi-scripts (to be used via NR frontend)
- changed ads_py script to use relative paths
- renamed button "Relays" to "Switches" in config menu
- fixed udev rules (usb connection status)
- minor bugfixes
______________________________________________________________________________________________________________
# Major Update 1.0.0
- updated OS to Debian 11 Bullseye
- updated Node-Red to version 2.2.2
- removed function to auto rebuilt  UI when changing to info tab
- added function to rebuilt UI when changing to config tab
- added query for bluetooth battery to built UI accordingly
- fixed battery (bluetooth) function to correctly show/hide bms info
- added function to automatically update relay names when entering tabs (debug, heater, settings, switches)
- changed absolute paths to relative paths in .sh files
- changed monitor timestamp interval to 60s for waterlevels and 30s for rpi usage
- added bms info to HTTP API and MQTT API
- added reboot function to HTTP API
- added topic 'conniot' to HTTP API for IoT Bridge
- added topic 'wrelayiot' to HTTP API for IoT Bridge (same as 'wrelay' but without firmware info)
- optimized dimmer label functions
- optimized wrelay I/O for touchdisplay
- added option to reset bluetooth devices
- removed DS18B20 node and added DS18B20.py instead
______________________________________________________________________________________________________________
# Update 0.9.1
- bug fixes from v0.9.0
- change Temperature node
- DALY MONIT Issuse solved
- name PKW Shunt to VANPI SHUNT

# Update 0.9.0 
- Display Version 0.6b - improved communication
- Heater hysteresis is working
- added reset waterlevel calibration
- fixed cell voltage for daly
- changed Victron name in the UART menus to "Ve.Direct"
- added wemos d1 flasher
- added names api
- added flows to rebuild ui when opening tabs
- seperated config into tabs for better overview
- rearranged all nodes in all flows for better backend overview
- source folder for pekaway data changed to /home/pi/pekaway
- seperated init_flow >> init_flow and connections (USB/UART connections)
- added new global variables "MainBattAmps", "MainBattVolts" & "MainBattSoc", battery values from all source destinations will be copied into these variables
- added new option to set battery stats in the config (frontend) for "MainBattDelivery" - HAS TO BE SET!!
- Display flow is now seperated into two flows for better overview
- Dimmer Controller for Mosfetboard (to be released soon -> 7 mosfets for dimmable lights etc.)
- integrated flasher mode to easily flash Wemos D1 directly from the Pi
- integrated JDB/GENERIC BMS to be used with the system
- new "ConnectedRelay" variable for turning heater on/off via relay (including hysteresis check)
- added LFBros Heater (433Mhz remote control), 433Mhz receiver and sender for raspberry needed! installed WiringPi for realisation
- included HTTP API to toggle relays get information about the system, rename names, set heater etc.
- included MQTT API to toggle relays get information about the system, rename names, set heater etc.
- changed the timing interval for monitor tab from 20s to 25s and less datapoints in charts (from 1000 to 600)
- added a new flow BLE Connections to connect BLE devices, currently supported: LIONTRON/JBD bluetooth Battery, GOK Senso4s Bluetooth scale
- added options in config to set dimmer names, added a debug option for Mosfetboard to show connection and MQTT stats
- added toggable function to send all stats via MQTT every 5min
- added template controls to open desired tabs when pressing buttons (menu navigation) leading to better overview
- added a debug tab with several functions to get information about the system and the Raspberry Pi itself
- update function is now capable of installing new packages via apt-get/apt and npm (lists are publicly available at git.pekaway.de, please make sure to read through them before using any download automations)
- wifi relays do now support tasmota and shelly
- the protocol used for the touchdisplay has been changed to run more smoothly and stable, already set names have to be set again as they will show weird stuff when upgrading from the old version
- touchdisplay v0.6b only compatible with RPI-Image v0.9.0 BETA and above!!
- buttons and waterlevels that are not being used can be disabled on the touchdisplay
- Votronic tank sensors can be calibrated directly (up to 2.4V max!)
- Water tank calibrations can be resetted
- serial USB connections are fixed via a new set of udev rules

# Update 0.8.0
- added package esptool
	new package "esptool" can be installed with `sudo apt-get install esptool`
- added ESP32&ESP8266 Tasmota Mosfet bins to disk
- added Flashermode to Node-Red -> enables flashing of ESP32/ESP8266 directly on the pi with the tasmota bins to control the mosfetboard (upcoming)
- added a "restart web1.py after crash" function
- added flow Dimmer Controller (controls dimmers in dashboard and Homebridge)
- added dimmer logic in config flow (hide/show dimmers and debug mode)
- added watchdog for mosfetboard (ESP32/8266)
- added Homebridge support for dimmers
- updated Homebridge to v1.4.0
- added npm install node-red-contrib-mcp23017chip
- added bmv 712 victron pid
- added pekaway display 2 -> add slider to display
- added jbd/generic BMS (basic)
- added LionTron Battery Bluetooth
- remove new version from PID Controll Autoterm
- add connection flow for all serial/bluetooth connections
- add rules for portbinding serialconnections
- remove usb serial swap 
- 

# Update 0.7.4
- improved PID Controll Autoterm
- added "check for update" button in update flow to check if an update is available
- hotfix for the Wifi scan problem from v0.7.3


# Update 0.7.3
- added PID Controller npm install node-red-contrib-pid-controller
	New npm module needed! Use `cd .node-red && npm install node-red-contrib-pid-controller`
- PID Heatcontroller Autoterm
- added backup and restore userData
	new packages "zip" & "unzip" are required! Use `sudo apt-get install zip unzip` to install them
- added Nest-style heattemperature-Widget


# Update 0.7.2
 - add pekawaydisplay UserData Flow
 - improve DisplaySettings -> show ips
 - new display version 0.4



# Update 0.7.1
 - update tab fix
 - autoterm temperaturemode added


# Update 0.7.0
- webasto flow improvements 
- autoterm improvements
- SET PARITY WEBASTO not fixed
- display switch error fix


# Update 0.6.9
- added homebridge reset function
- fixed voltage calibration function

# Update 0.6.8
- calbriate voltfactor function
- integrated update notification
- remove redbot and telegram flow (flow to be found on gitlab )
- added MQTT Broker to switch relays via Tasmota/Apple Home
- added homebridge support to use Apple Home via MQTT (homebridge running on port 8581 with login admin:pekawayfetzt)
- added function to resize filesystem in config (if SD-card not using full size for some reason)
- added rpi monitoring to the monitor tab
- added button to show ip-adress of both, wlan0 and eth0


image 0.6.7
- added possibilities to update the flows with USB-device and/or with internet connection (via curl git.pekaway.de/...)
- added option to create backups manually
- added option to delete existing backups to save space
- added a function to load existing backups
- added delay before restarting hostapd and dnsmasq when switching between Access Point modes
- change Heater flow - each heater has now one flow
- relayorder issue solved
- usb swap detection 


image 0.6.6

- add watchdog to shunt script
- increase voltage reading
- add custom batterySize (watthours)
- load shunt config after start
- add Monitor Tab for Battery and Temperatur
- reload old relay status after reboot
- remove network time snyc -> time from display or realtime clock 
      ->sudo systemctl stop systemd-timesyncd
      ->sudo systemctl disable systemd-timesyncd
- add telegram bot flow


image 0.6.5

- adjusted timezone to CEST/Berlin
- solved issue with custom wifi connection not working because of double quotation marks
- removed duplicate textfield of version info in config tab
- changed slider to set state of charge to dropdown menu
- changed methods to calibrate water sensors to have better feedback visibility (pop-up) on smaller displays


image 0.6.4

- ADS1115 gain change -> Votronic Sensor
- Level2 issue solved
- VersionInfo -> config


image 0.6.3

### Major Changes ###
- updated Node-Red to v2.0.6
- updated dashboard to v3.0.4
- added template node to generate stylesheet for the dashboard
- added control for autoterm heater

### Minor Changes ###
- changed width of battery widget to 6
- cleaned flow 'VE.Direct' in backend
- access point name will now include parts (3 chars) of the RPI's hardware serial, so AP-names will be  unique
--> AP-name is set on first boot only
- unchecked 'send to all browser sessions' on all notification nodes
- added a version number with changelog to the 'init' flow
- changed baudrate on china heater to 9600
- added favicon for dashboard
- changed a line of text in index.html (appears when the dashboard is loading)
- added connection status of USB ports to dashboard config
