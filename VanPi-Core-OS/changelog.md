# Update 2.0.7 (18. Aug. 2025)
- added functions to support In-Out-X relays
- added functions to support dimmers and RGBW channels on DimmyPro
- added functions to support Truma Combi Heater using CI-Bus
- added binary ci2mqtt and corrosponding .env file
- added functions to support Truma Control from touchdisplay
- adjusted HTTP API to support new functions (smartphone app)
    - includes dimmyPro + rgbw stripes, In-Out-X, Truma Combi Heater control
- adjusted MQTT API to support new functions (smartphone app)
    - includes dimmyPro + rgbw stripes, In-Out-X, Truma Combi Heater  control
- fixed smaller mistakes in VE.Direct flow
- fixed small mistake when creating a new ssh hostkey
- rewrote "resize filesystem" function to properly display NVMe drive sizes
- rewrote functions to get key:value pairs for mcpinputs
- added SmartShunt 300A IP65 50mV 0xC039 to VE Direct flow
- swapped x- and y-angle for BMI270 to replicate GPU6050 data

# Update 2.0.6 (30. Jun. 2025)
- fixed replacement of the very first item in BLE scan array
- removed while loop in "check relays to set" for inputs (Relay Controller)
- fixed bug that sets back the variable for usage of older relayboard on boot
- added support for MaxxFan (Multicom) and Bayernluefter (HTTP)
- added functions to control new fans from Pekaway touchdisplay
- added http and mqtt functions to control new fans remotely
- renamed group "MaxxFan" to just "Fan"
- fixed error in display for victron ttgo
- fixed "all off" and "selected all off" http functions, they were applying double transitions that lead to flickering when turning off
- MCP input status changes are now pushed to MQTT on topic "pkw/tele/input"
- added uhubctl to restart USB ports on RPI5
- added calculations of absolute g_forces to mpu_angle.py
- added support for new BMI270 chip on VAN PI Core Pro (replaces MPU6050)
- changed autooff variables from integer to float to support sub-minute values
- fixed error not initializing BLE MPPT when set as only BLE device
- fixed function to set server time from browser time (client)
- fixed mqtt support for shelly gen.2
- added mqtt topic to show changes from tasmota relays
- fixed mqtt wrelays when set from Homebridge
- fixed a problem with filters after relays/wrealys/dimmers to fix problem with time schedulers
- changes to /boot/firmware/config.txt:
    - set arm_freq_min to 600MHz and arm_freq to 1500MHz to reduce cpu/power consumption and heat
    - set fixed gpu frequencies
    - added options to disable internal bluetooth (commented out by default)
    - disabled HDMI (!)
- changed act_led trigger to "heartbeat" for external act led on VAN PI core (and core pro)
- added new global variable "i2c_detect" to get available i2c_adresses on boot
- added new functions to retrieve data from Pekaway MQTT shunt
- reworked boiler control flow
    - added automatic temp control
    - added emergency limits for water level and temperatures
    - moved boiler control to new tab "Devices" in config
- added functions to use a 11-point calibration method for waterlevels (needs to be hardcoded!)

# Update 2.0.5 (13. Jan. 2025)
- fixed 2nd autoterm temp sensor for temp mode
- fixed userdata setting old version number when restoring userdata
- fixed Victron Shunt IP65 Rev.2 PID
- fixed Ruuvitags not being shown properly in touchdisplay homescreen
- fixed Apple Home dimmers not working
- fixed Votronic mppt not being shown in monitor
- fixed problem in routing Webasto heater to the correct USB port
- fixed heater not being shown when set as "relay connected heater" only
- fixed the standard name for "Relay 5" (was accidentally set to "Relay 4", only the name displayed)
- fixed errors when some heater values are not returning strings from API, which resulted in the app heater widget not being displayed
- fixed a minor error when sending the stop command to Autoterm 2
- set gps_updated variable for smartphone app to now show 01. Jan 1970 when no valid GPS data has been received
- updated NR to v4.0.8 (not when using updatescript!)
- fixed touchdisplay autoterm power mode always turning to 0 when decreasing power level
- set shelly gen.1 switches mqtt outputs to on/off instead of true/false, according to Shelly documentation
- rewrote calculations for voltage and ampere in web2.py for (older) wired shunt

# Update 2.0.4 (20. Dec. 2024)
- changed display baudrate to 115200
- rewrote heater flow
- rewrote autoterm flow for twinkit support
- rewrote china heater flow
- rewrote webasto flow
- rewrote bluetooth scan functions to use bluetoothctl instead of hcitool
    - known issue: sometimes names of discovered devices are not provided
    - duplicates in discovered devices are filtered out
    - discovered devices MAC adresses are sorted alphabetically
    - slightly rewrote RuuviBLE.py
    - slightly rewrote jbdBLE.py
    - RuuviTags flow has beend adjusted
- added a function to have a digital input turn selected relays off (but never/not back on)
- fixed digital inputs not turning on dimmer when set to switch
- altered ttgo function to show changes in math. sign (+/-) immediately
- dimmers will now dim up/down from current value to target value when set via API/Touchdisplay/UI instead of simply jumping to the target value (I2C Dimmy only)
- fixed a problem with restoring userdata
- set a function that prevents the touchdisplay from initializing data until Node-RED is fully loaded up
- added http endpoints to control two autotherm heaters individually
- altered function to built UI respectively
- added functions to use boiler via heater
- heater hysteresis can now be adjusted in steps of 0.5
- altered http endpoints for smoother experience with loading data in the Pekaway Connect app
- altered the update script to make to edit /etc/logrotate.conf, /etc/log2ram.conf and functionGlobalContext keys in .node-red/settings.js
- altered function to reconnect to remote MQTT broker to every 8 hours
- added support for Votronic MPPT (2014 or later) via MUART
- added a function to synchronize server time with client(browser)time
- added PekawayTouch.tft (v2.0.0) to /boot/

# Update 2.0.3 (17. October 2024) - Hotfix
- fixed function that sets GPIOs to low/high for waterlevels on RPI4
- fixed function to add Ruuvitags using the MAC-adress, when no RuuviTag was found in auto-mode
- removed a zigbee device that was left in the zigbee config after testing
- fixed dropdowns in Boiler Control menu that show levels, relays, temperatures
- removed function that dims LEDs down stepwise when using digital inputs for "alloff" and "selected alloff" options
    - dimming down stepwise potentially leads to leaving some LEDs above 0% on RPI4
    - Happens when using too many requests (etc. dimming all dimmers at once from 100 to 0)
    - dimmers are shut down to 0% immediately for now
- removed a connection that reinitialises all variables when pressing the button that updates the temp. names in the Pekaway touchdisplay
- added 0xA073 to VE.direct (SmartSolar MPPT 150/45 rev3)

# Update 2.0.2 (04 October 2024)
- inserted functions to set fixed positions for temp sensors
    - see Config > Sensors > Temp Sensor Positions
    - if new sensors are connected, the IDs for older sensors have to be removed manually
    - additional sensors will be shown in an extra group with their values and IDs
    - rewrote the ds18b20.py script to return the sensor IDs
- added global mptt variables to VE.Driect flow
- set interval to retrieve ip-address (wlan0 & eth0) to 20s for faster recognition on change
- added new mqtt message to dimmer section to pass states to Homebridge
- updated Homebridge to v1.8.4 and Homebridge UI to v4.5.8
- fixed temp automations trigger for "below"
    - (trigger did execute if the variable in question was undefined)
- new switch option to use the older (black) Relayboard
    - will show/hide wired shunt (under Wireless > Shunt)
    - rewrote flow/nodes that retrieve data from the wired shunt
    - option to read water levels every second will not work on older relayboard!
- new BETA(!) support for RPI5 
    - udev rules have been expanded 
    - Zigbee and GPS are switched (USB Port numbers) on RPI5!
        - Zigbee is now available on USB1 and GPS on USB2 (only RPI5!)
        - RPI4 is still GPS on USB1 and Zigbee on USB2
        - added an overview table to the config menu for RPI5 USB ports
    - added new global variable 'cpumodel' to check if we have RPI4 or RPI5
    - setting of GPIOs when waterlevels are initialised now uses 'pinctrl' instead of 'raspi-gpio'
        - only on RPI5 and only on the newer Core board, older ones still use the jumpers
    - enabled uart0 on RPI5 for the touchdisplay and added a new connection for ttyAMA0, to have the uart available. 
        - RPI4 uses ttyS0, RPI5 uses ttyAMA0
        - depending on the RPI model used, one of the ports will therefore always report that it can't connect 
- when using dimmers on the functions for 'alloff' and 'selected alloff' (digital inputs), they will now dim down to 0 instead of just shutting down
    - only works on dimming down, not when triggering the 'dim back up' function
- digital inputs set to dimmers will now only dim (long push) to a minimum level of 5% instead of 0%
    - use a short push to completely turn off dimmers
    - if saved value is below 10% and dimmer is currently off, a short push will always dim up to 20%
    - values are only saved when using short pushes on the digital inputs, not when dimming down from dashboard/touchdisplay/app
- boiler functions got a slight rework:
    - boiler settings have been moved to Config > Boiler Control
    - dropdowns do now show the names for relays etc. 
    - added a function to set a water level, so that the boiler is only triggered if the water level is above a set threshhold (optional)
    - an error from a tempsensor will turn off the boiler (when auto temp control enabled) and also the auto temp control settings!
- fixed the initialization of inputs 7 & 8 on boot
- fixed triggering of MainBattData notification when updating temp names
- fixed some NaN warnings from monitor flow (which were visible in system/NR log)
- fixed RuuviTags not showing in touchdisplay when set as inside temp sensor
- reduced max_old_space_size for NR to 512 to reduce risk for OOM error
- CPU temp in monitor tab now ranges in green color up to 65°C

# Update 2.0.1 (19 July 2024)
- fixed the function that initializes the autoturnoffs on boot
- autoturnoffs do now show actual relay names instead of placeholders
- if an autoturnoff is running, it will restart the timer on reboot
- changed the function that kills all BLE scripts to use '&' instead of '&&' to stop the function from stopping on an errors
- changed the initialization of switches names
- added a function to show at which time switches will automatically turn off (autoturnoffs)
- changed the autooffslider to an numeric input (0-300 minutes)
- rewrote the function that initializes the autooff timings
- removed the check for I2C-address of PCA9685@0x55 on dimmer usage
    - invalid inputs will just go "into the void"
- added a gamma correction value to the dimmers, which allows for higher precision on lower dimmer values
- rewrote the function that executes dimmer commands from digital inputs
    - dimmers are now much smoother
    - dimmers can be combined (might be laggy on wireless dimmy connections)
- rewrote the functions that initializes relays, w-relays and dimmers
- added a function to turn everything off and back on from digital inputs (set the input type to button!)
- added a function to turn off only the selceted relays/dimmers on an input (set the input type to button!)
    - mcpinput_types are not set on freshly flashed images!
- added info the where GPS (USB1) and Zigbee (USB2) have to be connected
- added RuuviTags to monitor flow
- added a function to show Temperatures and RuuviTags in combined charts instead of single charts for every sensor
- fixed function to show inside temp sensor on touchdisplay when a RuuviTag is set
- copied the ACT LED to the external LED on the VAN PI Core PCB on GPIO22
    - THIS MAY LEAD TO UNEXPECTED BEHAVIOUR ON OLDER BOARDS (the blue one), IF GPIOs ARE USED TO TRIGGER RELAYS
    - (VAN PI Core and the black VAN PI Relayboard use the MCP23017)
    - (only the older blue Relayboard uses GPIOs!)
- slightly reworked the python script that reads out the MPU6050 to use atan2 function instead of atan for more precision
- the z-angle will be printed out as well now
- added options to swap X or Y with the Z axis (to ensure corrections on different installation angles)
- moved the switch to activate position sensor tab to the Sensors Config menu
    - moved the config for the position sensor to Sensors > Position Sensor Config to avoid accidental recalibrations
- Position Sensor is now active by default on new images
- added I2C-check for 0x69 on boot to automatically show/hide Position Sensor tab
- added another check to solar_surplus_consumption (experimental)
    - relays will only turn on if mppt_data is not older than 15min
    - relays will turn off (if turned on from mppt_data) if mppt_data is older than 15min
- added temperature automations to trigger relays when sensors hit certain threshholds
- added function to switch to a "Modern Dark" theme
- added RAM info to debug menu
- added function that stops requests hitting the public Pekaway server for remote access when no username/password is provided
- added function to show time to go in real time (rather than only average value calculated over the last 5min)

# Update 2.0.0 (14 May 2024)
- added an i2c check t boot to automatically turn on/off dimmers in frontend
- renamed MCP input section to "Switches Inputs"
- added an notification to show which input has been triggered when focus is on Switches Input screen
- added reminder to restart ESP32 wireless shunt before setting values
- rewrote python script to set shunt data to be more reliable
- prepared support for 2nd generation Shellie Switches ("Plus", experimental)
- added udev rules to differentiate between zigbee dongles (USB2) and GPS usb mouse (USB1)
- activated zram and log2ram, purged dphys-swapfile to reduce SD-card wear
- minor bug fixes and additions (notification pop-ups etc.)

# Update 2.0.0 BETA2 (10 May 2024)
- upgraded to latest Raspi OS (Debian 12 Bookworm)
- upgraded NodeJS to v22.0.0 with npm v10.6.0 and Node-RED v3.1.9
- upgraded Homebridge to v1.8.1
- upgraded Python to v3.11.2 with pip v23.0.1
- switched to NetworkManager for Wifi-Management, reworked the whole Wifi-Flow
- dropped the ble_manager.py script
- updated BLE scripts for the Pekaway Wireless Shunt, Pekaway MPPT S20 and JBD BMS to keep connections open (Bluetooth adapter restarts every 20min)
- added functions to keep track of latest ble data, if a device didn't response for 4min Bluetooth will be restarted completely
- added functions to use RuuviTags as the inside temp sensor to control the heating system
- added a function to use a USB GPS mouse
- reworked the automatic switching from RJ45 Touchdisplay (38400 baud) to RJ45 GPS adapter (9600 baud)
- reworked the ds18b20.py script to keep running with a restart every 20min, values are read every 15sec
- added a function to read ds18b20 values every second for easier mapping during setup, slightly reworked the corresponding flow to have more stable data responses
- reworked the script that reads water levels to keep running with a restart every 10min, values are read every 15sec
- added mppt data to the MQTT API
- reworked the calculation of time to go
- reworked the BLE connections flow to have more stable connections to the Pekaway Wireless Shunt, Pekaway MPPT S20 and RuuviTags
- added functions to the MPU6050 flow to determine routes from the client to the Nginx server to load van images for the frontend dynamically
- slightly reworked the Debug flow to keep up with the changes made to the underlying operating system
- changed the upgrade flow to use a different folder for updates on the GitHub server (using the new VAN PI OS on older Relayboards (from before April 2024) will need manual adjustments to the backend, or the system will not function properly!)
- updated the config flow to represent the changes
- reworked the frontend for better overview
- minor changes in notification nodes

# Update 2.0.0 BETA1 (17 April 2024)
## Changing to VAN PI Core with this Version!
- added a new function for DS18B20 sensors that will change the delay between requests to 1h if no values have been seen after 10 tries (3h after 34 tries) to reduce cpu consumption
- added a new section that will request values from a Pekaway MPPT Solar Charger (S20) via BLE
- added a new section to add RuuviTags Pro 3in1 to the system via BLE
- added a new section to add a Pekaway Wireless shunt to the system via BLE
- added a new "Wireless" section and moved every Wifi and BLE associated settings there
- added a new section "Position Sensor" to visualize the MPU6050 data
- added new global variable for MPU6050 temp, displayed in monitor tab
- added new global variables for ttgo and overall cpu usage
- added a new python script "ble_manager.py" to queue all the scripts using BLE (scripts will be delayed if another script is still running)
- added a new function to read GPS data from a UART RJ45 GPS Adapter
- added functions to set the UART RJ45 baud rate automatically (9600 for GPS, 38400 for touchdisplay), depending on how frequently data arrives
- added node-red-contrib-nmea (for gps data)
- added a new section with a worldmap (random gps data can be activated in the backend)
- added new HTTP endpoints:
  /gps
  /app_home (only needed for the new Pekaway Control app)
  /position_sensor
  /mppt
- added MQTT functions for remote access
- added a function to set username and password to connect the Pekaway app to the system
- added 2 more switches inputs (VAN PI Core has 8 inputs)

- renamed "MCP Inputs" to "Switches Inputs"
- changed waterlevels configuration to use a different python script (no more http requests)
- deactivated the old shunt python script
- rewrote calculation of ttgo (monit tab)
- rewrote nginx pekaway1 serverblock and default serverblock to deliver the images for the position sensor
- minor changes

# Update 1.1.2 (21 November 2023)
- changed wifi firmware to firmware-brcm80211_20190114-1+rpt4_all.deb to increase stability when bluetooth is used
- changed the delay that checks the second NR instance from 10s to 15s
- added a function to switch between wifis and delete configured wifis (does not work in access point mode!)
- added a function that shows the connected SSID when checking IP-address
- added a function that checks if the configured wifi access point passphrase is between 8 and 63 characters
- added http endpoint /reset_wifiAP/true to reset the access point
- added http endpoint /network to show network info
- added http endpoint /update_wifi_ap/:ssid/:wpa to update the wifi access point
- added http endpoint /activate_wifi_ap/:input (:input has to be true or false) to de-/activate the wifi access point
- added a sleep 1s function to the NonAPtoAP.sh script to compare old/new access point mode status (active/inactive, used in http endpoint /activate_wifi_ap)
- added the possibility to use hidden networks when inserting wifi data manually
- added a funtion that initialises the dropdown value for Main battdata
- added a function to show the van name in the title bar
- changed the charts in the Monitor tab for better visibility:
    > chart titles always show current values accordingly
    > temp charts now draw one point for every 15 incoming values (mean value)
    > SoC chart now draws one point for every 5 incoming values (lowest value seen)
    > Volt chart now draws one point for every 3 incoming values (mean value)
    > Amp chart now draws one point for every 3 incoming values (mean value)
    > CPU usage chart now draws one point for every 3 incoming values (highest value seen)
    > TTGO field now shows the mean value for every 5 incoming values and minutes are rounded to the nearest quarter hour (15min)
- removed dimmer 8 from the switch schedulers (Dimmy supports only 7 dimmer channels)
- changed appendix for wifi SSID from "_VanPI" to "_pekaway.com"
- rewrote the relay controller to only switch relays on actual change instead of constant updating
- added a sleep timer in loops of python ads script to reduce CPU usage
- added the option to show ttgo on the info tab (see Config > System)
- switched groups RPI and BLE in System Config
- added a function that shows overall CPU usage since boot in Monitor tab
- fixed the tempsensor function not showing doubledigit numbers when temperature is below zero
- fixed the default baudrate not being 115200 for MaxxFan UART
- added a function to use a variable baudrate on USB4 (will reset on reboot)
- fixed the function that hides Dimmers & W-Relays on first boot
- added a function to controll dimmers via the MCP inputs
- added offsets to all 4 temp and 2 dimmytemp sensors, so that displayed temps can be adjusted individually
- added a function thats asks to turn everything off before shutting down (relays, w-relays & dimmers)
- added a function to control a boiler with a relay and DS18B20 tempsensor
- changed all groups in the frontend to now be collapsible
- changed the update functions to use https://github.com/Pekaway/VAN_PI as server instead of git.pekaway.de
- added a function that shows the state of the update process
- added new HTTP and MQTT endpoints to set autoterm specific heatingpower and ventilation
- deactivated automatic search for BMS (too many errors)
- added support for SuperVolt & FlyBat Batteries (BLE)
- fixed BLE scan function, was sometimes showing results as buffer instead of string
- added .bin files to be flashed to ESP devices for dimmy (now supports ESP8266 & ESP32, Dimmy for VANPI & Standalone)

# Update 1.1.1 (12 May 2023)
- fixed mcp inputs not being displayed correctly
- fixed water level 1 error which kept it from taking other values than 0
- fixed error which prevented "main battdata" to be initialised on boot
- changed sampling frequency of PCA9685 to 200 (dimmer section)
- changed http request nodes in Pekaway Shunt flow to use 127.0.0.1 instead of localhost
- added function to start a second Node-RED instance, using a backup flows file (Config > System > System Update)
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

