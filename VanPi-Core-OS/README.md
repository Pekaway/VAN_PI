## Precompiled Image for Raspberry Pi 4 and Raspberry Pi 5

**Head over to** [links.pekaway.de](https://links.pekaway.de/downloads.html), download the latest precompiled image (it's a headless system, so no desktop environment) and flash it to your SD-card.
Start up your Raspberry Pi, wait a few minutes for the boot process to finish and you're good to go.

## Manually Installing the VanPi System

1. **Get a Raspberry Pi 4 or Raspberry Pi 5.**
2. **Obtain a clean install of Raspberry Pi OS (Debian 12 Bookworm) on a MicroSD card** - ([download here](https://www.raspberrypi.com/software/operating-systems/)).
   - (Can be a full setup with desktop environment)
   - The script checks if the OS is at least Debian 12 Bookworm, with Linux kernel 6.1+ and Python 3.11+.

3. **Use the Raspberry Pi Imager** ([download here](https://www.raspberrypi.com/software/)), and set the following options:
    - Hostname: `pekaway.local`
    - Activate SSH
    - Username: `pi`
    - Password: `raspberry`
    - Wi-Fi:
        - Set your Wi-Fi SSID and passphrase
        - Change Wi-Fi country if needed
    - Change language if needed
    - Change keyboard layout if needed

4. **Flash the operating system to your SD card.**

5. **Insert the SD card into the Raspberry Pi and power it on** (the first boot may take a few minutes).
6. **Wait until it appears on your network, then log in via SSH** using the credentials you set.
7. **Once logged in, run the following commands:**
    ```bash
    cd ~/
    wget https://raw.githubusercontent.com/Pekaway/VAN_PI/main/VanPi-Core-OS/vanpi-core-init.sh
    chmod +x vanpi-core-init.sh
    bash vanpi-core-init.sh
    ```

8. **The script will take about 10-20 minutes to complete**, depending on your bandwidth and hardware. Several hundred megabytes may be downloaded as the script updates, upgrades, and installs packages.
   - The script will install Node.js 20 and the latest Node-RED. Note that the original VanPi OS image runs Node.js 22 and may not have the most recent Node-RED version.
9. **Confirm if any inputs are required** (typically none, everything should run automatically until you're asked to reboot and the end of the script).
10. **Sit back and relax** while the installation proceeds.

Once the process is complete, the Raspberry Pi will power up in Access Point Mode (only if no wired connection can be established). Connect to it and proceed from there, or use a wired connection.

### **Setting Up Homebridge**

You will need to configure Homebridge by accessing `http://RPI-IP:8581` or `http://pekaway.local:8581`. Set the username to `admin` and the password to `pekawayfetzt` (or another preferred password) and continue. The configuration should already be present, or you can find it [here](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-Core-OS/homebridge/config.json). (Note: This is not fully tested yet!)
- You may need to reset Homebridge through the Node-RED frontend to generate a new random MAC address before it can be connected to Apple Home.

Go to the VanPi system frontend, navigate to **Config > Wi-Fi**, and click on **Reset Homebridge**. This will generate a new random MAC address, a new pin code, and download the latest Homebridge configuration from our server and deploy it. Ensure that you're connected to the internet for Apple Home and the configuration download to work.

---

## **TROUBLESHOOTING**

### Symbols Not Displayed Correctly (e.g., "°C")
If symbols are not displayed correctly in the frontend, download the `flows_pekaway.json` from the VanPi-Core-OS folder ([download here](https://github.com/Pekaway/VAN_PI/blob/main/VanPi-Core-OS/node-red/flows_pekaway.json)).

On your Raspberry Pi, open `~/.node-red/flows_pekaway.json` and manually replace its content with the content from the downloaded file. Then restart Node-RED using the following command:
```bash
sudo systemctl restart nodered.service
```

Alternatively, go into the Node-RED backend and replace non-formatted characters by hand:
 - flow Sensor-Dashboard, on the very top there are 4 text nodes displaying the temp sensors
 - flow Monit, again there are 4 nodes for the temp sensors and 1 gauge node for the CPU-temp
 - flow Config, at "system settings" 4 text nodes for the four temp sensors
 - probably in somre more places...