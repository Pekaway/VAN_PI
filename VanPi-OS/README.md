# VanPi operating system

Files and scripts needed to make the VanPi OS work.

A quick overview about the files:

### [changelog](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/changelog.md)

The changelog of VanPi OS, refer to this file to keep track of latest changes, updates and error fixes.

### [config.json](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/config.json)

Configuration file for Homebridge, on the system this is located at */var/lib/homebridge/config.json*

### [configuration.yaml](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/configuration.yaml)

Configuration file for the zigbee2mqtt service, on the system this is located at */opt/zigbee2mqtt/data/configuration.yaml*

### [flows.json](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/flows.json)

The flows file containing all the flows/nodes for Node-RED. Basically the most important file, as it contains all (most of) the logic and calculations done.
It also contians the dashboard and UI functions. On the system this is located at */home/pi/.node-red/flows_pekaway.json*

### [home_pi_pekaway_files.zip](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/home_pi_pekaway_files.zip)

A .zip file containing some scripts (python and bash) to do some calculations and configurations. For example there are bash scripts to change between access point mode and client mode, or python scripts to read data from DS18B20 temperature sensors and the [VanPi Shunt](https://github.com/Pekaway/VAN_PI/blob/main/Hardware/Shunt/ENG_VanPiShunt_Quickstart_eng.pdf)
It also inherits the folder structure VanPi OS uses to access individual files and to save user configurations.
A precompiled .tft file for the Sonoff NS panel is available as well.

### [icons.zip](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/icons.zip)

This .zip file contains the icons VanPi OS uses to replace the default Node-RED icons. These icons are shown on the dashboard, for example when redeploying the flows.

### [package.json](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/package.json)

The package.json file for Node-RED. It defines the needed modules to run the NodeJS project (Node-RED).
Read more about what this file is used for here: [The basics of package.json](https://nodesource.com/blog/the-basics-of-package-json/#:~:text=The%20package.,modules%2C%20packages%2C%20and%20more).

### [package.txt](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/package.txt)

A file that contains all the packages VanPi OS currently uses to operate properly. Learn more about packages here: [Debian packages basics](https://www.debian.org/doc/manuals/debian-faq/pkg-basics.en.html)

### [pip3list.txt](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/pip3list.txt)

A file that contains all the python packages and python modules VanPi OS currently uses to operate python scripts properly. Learn more about python packages/modules here: [DPython modules packages](https://realpython.com/python-modules-packages/)

### [updatescript.sh](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/updatescript.sh)

This bash script is called when the update function from the frontend dashboard of VanPi OS is triggered. It will download and install any updates and restart the system.
**Keep in mind that this will replace your current flows file with the one from Github!** Make sure to create a backup of your flows before updating to a new version!

### [usbreset.c](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/usbreset.c)

A simply script to reset the USB ports. Will be triggered when the button "Reload USB" (Dashboard > Config > System) is pressed. Helps to regain connections to USB devices in case they are not displayed as connected anymore.

### [vanpi-init.sh](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/vanpi-init.sh)

This bash script is not used in VanPi OS itself, but rather for when you want to install VanPi OS manually.
Refer to this manual if you want to use the script: [VanPi init script](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/vanpi-init-manual.md)

### [zigbee2mqtt.service](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-OS/zigbee2mqtt.service)

A service file that will be used when zigbee2mqtt is activated. The service file makes sure that zigbee2mqtt will automatically start after a reboot.

### [Video (DE)](https://www.youtube.com/watch?v=0tOiUHZ6s-4)
