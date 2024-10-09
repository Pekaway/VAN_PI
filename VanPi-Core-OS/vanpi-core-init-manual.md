## Manually installing the VanPi system

- Get a Raspberry Pi 4 or Raspberry Pi 5
- Get a clean install of Raspberry Pi OS (Debian 12 Bookworm) on a MicroSD-card - ([download here](https://www.raspberrypi.com/software/operating-systems/))

 - Using the Raspberry Pi Imager ([download here](https://www.raspberrypi.com/software/)), set the following options
    - Hostname: pekaway.local
    - activate ssh
    - username: pi
    - password: raspberry
    - wifi:
        - Your wifi SSID and passphrase
        - change wifi country if needed
    - change language if needed
    - change keyboardlayout if needed

- Flash the operating system to your sd card


- Put the SD-card into the RPI and power it on (first boot may take a few minutes)
- Wait until it shows up in your network and login via SSH with the credentials you just set
- Once logged in do
```
cd ~/ &&
wget https://raw.githubusercontent.com/Pekaway/VAN_PI/main/VanPi-Core-OS/vanpi-core-init.sh &&
chmod +x vanpi-core-init.sh &&
bash vanpi-core-init.sh
```

- The script will take about 10-20min to run through, depending on bandwith and hardware, several 100s of megabytes may be downloaded, as we're updating/upgrading and installing packages
- Confirm if inputs are needed
- Sit back and relax

Once done, the RPI will power up in Access Point Mode, connect to it and proceed from there
(Or use a wired connection)

Homebridge needs to be setup, you can do that when accessing RPI-IP:8581 or pekaway.local:8581 - set admin:pekawayfetzt (or whatever you prefer) and continue from there, config should already be there (or you can find it [here](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-Core-OS/homebridge/config.json)) - not further tested!!
May need a reset through the Node-RED frontend to generate a new Frandom MAC adress before it can be connected to Apple Home

Go to the frontend of the VanPi system > Config > Wifi and click on reset Homebridge. That will generate a new random MAC address, a new Pin code and it'll download the latest homebridge config from our server and deploy it. Remember that you need to be connected to the internet for Apple Home to work (and for downloading the config files, obviously)

## **THROUBLESHOOTING**

In case some symbols in the frontend are not displayed correctly (eg. "°C"), download the flows_pekaway.json from the VanPi-Core-OS folder ([here](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-Core-OS/node-red/flows_pekaway.json)).
On your RPI open ~/.node-red/flows_pekaway.json and manually replace its content with the content from the file you just downloaded from the server. Then restart Node-RED with "sudo systemctl restart nodered.service".

Alternatively, go into the Node-RED backend and replace non-formatted characters by hand:
 - flow Sensor-Dashboard, on the very top there are 4 text nodes displaying the temp sensors
 - flow Monit, again there are 4 nodes for the temp sensors and 1 gauge node for the CPU-temp
 - flow Config, at "system settings" 4 text nodes for the four temp sensors
 - probably in somre more places...