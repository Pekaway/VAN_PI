#!/bin/bash

########################################################
#														
# This script will install VanPi OS				 		
# on a clean and fresh 'Raspberry Pi OS (Buster)'!		
# Simply download the script and execute it.			
#														
#
#	This script still refers to the older gitlab repo
#	and will be updated with the next update of VanPi OS
#
########################################################

# create logfile and make it writable
LOG_FILE=/var/log/pekaway-install.log
sudo touch ${LOG_FILE}
sudo chmod 0666 ${LOG_FILE}

exec 3<&1
coproc mytee { tee ${LOG_FILE} >&3;  }
exec >&${mytee[1]} 2>&1

# define startdate
start=`date +%s`
startdate=`date`

# define server address
Server='https://raw.githubusercontent.com/Pekaway/VAN_PI/main/VanPi-Core-OS/'
ServerFiles='https://github.com/Pekaway/VAN_PI/raw/main/VanPi-Core-OS/'
LfsServerFiles='https://media.githubusercontent.com/media/Pekaway/VAN_PI/main/VanPi-Core-OS/'
GithubRepo='https://github.com/Pekaway/VAN_PI.git'

# define color variables
Cyan='\033[0;36m'
Red='\033[0;31m'
Yellow='\033[0;33m'
NC='\033[0m' #No Color

echo -e "${Yellow}Logfile will be ${LOG_FILE}${NC}"

#####################################################
# Compare OS version and kernel version
#
# Get the Debian codename from /etc/os-release
OS_CODENAME=$(grep "VERSION_CODENAME" /etc/os-release | cut -d'=' -f2)

# Get the current kernel version
KERNEL_VERSION=$(uname -r | cut -d'-' -f1)

# Get the current Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')

# Define the minimum required OS version (Debian Bookworm) and kernel version
MIN_VERSION="bookworm"
MIN_KERNEL_VERSION="6.1"

# Function to compare two version numbers
version_greater_equal() {
    # Compare version numbers
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" == "$2" ]
}

# Function to compare OS versions using codename
compare_os_versions() {
    # Array of Debian codenames in chronological order
    versions=("buster" "bullseye" "bookworm" "trixie" "forky")

    # Find the index of current and minimum versions
    for i in "${!versions[@]}"; do
        if [[ "${versions[$i]}" == "$1" ]]; then
            current_index=$i
        fi
        if [[ "${versions[$i]}" == "$2" ]]; then
            min_index=$i
        fi
    done

    # Compare the index values to determine if an update is needed
    if [[ "$current_index" -lt "$min_index" ]]; then
        echo "Error: System is running $1. Please upgrade to $2 or later." | sudo tee ${Progress}
        exit 1
    fi
}

# Check OS version
compare_os_versions "$OS_CODENAME" "$MIN_VERSION"

# Check Kernel version
if ! version_greater_equal "$KERNEL_VERSION" "$MIN_KERNEL_VERSION"; then
    echo "Error: Kernel version is $KERNEL_VERSION. Please upgrade to kernel $MIN_KERNEL_VERSION or newer." | sudo tee ${Progress}
    exit 1
fi

# Check Python version
if ! version_greater_equal "$PYTHON_VERSION" "$MIN_PYTHON_VERSION"; then
    echo "Your Python version is $PYTHON_VERSION. Please upgrade to Python $MIN_PYTHON_VERSION or newer." | sudo tee ${Progress}
    exit 1
fi

echo "Your system is running Debian $OS_CODENAME, kernel $KERNEL_VERSION, and Python $PYTHON_VERSION, all of which are up-to-date."
echo "Continuing..."
#####################################################

# get latest updates
# Update package list
echo -e "${Cyan}updating packages list${NC}"
# add the Homebridge Repository GPG key:
curl -sSfL https://repo.homebridge.io/KEY.gpg | sudo gpg --dearmor | sudo tee /usr/share/keyrings/homebridge.gpg  > /dev/null
echo "deb [signed-by=/usr/share/keyrings/homebridge.gpg] https://repo.homebridge.io stable main" | sudo tee /etc/apt/sources.list.d/homebridge.list > /dev/null
# add the log2ram Repository key:
echo "deb [signed-by=/usr/share/keyrings/azlux-archive-keyring.gpg] http://packages.azlux.fr/debian/ ${OS_CODENAME} main" | sudo tee /etc/apt/sources.list.d/azlux.list
sudo wget -O /usr/share/keyrings/azlux-archive-keyring.gpg  https://azlux.fr/repo.gpg
sudo apt update

# Upgrade all installed packages while keeping existing configuration files
echo -e "${Cyan}upgrading packages${NC}"
sudo apt upgrade -y -o Dpkg::Options::="--force-confold"

# install git and other packages
echo -e "${Cyan}Installing git${NC}"
sudo apt install -y git make build-essential jq log2ram

# enable I2C and 1-Wire
echo -e "${Cyan}Enabling I2C and 1-Wire Bus${NC}"
sudo raspi-config nonint do_i2c 0
echo -e "dtoverlay=w1-gpio\ndtoverlay=uart5\ndtoverlay=uart0-pi5\ndtoverlay=uart4-pi5\nenable_uart=1\n\n# copy act led to external led on Van Pi Core board\ndtoverlay=gpio-led,gpio=22,label=vpicore_act_led,trigger=mmc0" | sudo tee -a /boot/firmware/config.txt

# Set iptables-persistent to true
sudo debconf-set-selections <<EOF
iptables-persistent iptables-persistent/autosave_v4 boolean true
iptables-persistent iptables-persistent/autosave_v6 boolean true
EOF

# set hostname to pekaway
echo -e "${Cyan}Set hostname to pekaway${NC}"
echo "pekaway" | sudo tee /etc/hostname

# clone archive from github to get data files
echo -e "${Cyan}Cloning data from github repository${NC}"
cd ~
sudo apt install git-lfs # use git lfs for larger files like .json files etc
git lfs install
git clone --filter=blob:none --no-checkout ${GithubRepo}
cd VAN_PI
git sparse-checkout set VanPi-Core-OS
git checkout


# get packages list from server and install and keep old config files
echo -e "${Cyan}Get packages.txt from server and install while keeping old config files${NC}"
sudo apt install -y -o Dpkg::Options::="--force-confold" $(cat VanPi-Core-OS/packages.txt)

# save needed resources to ~/pekaway
echo -e "${Cyan}creating default values for pekaway/vanpi resources ~/pekaway${NC}"
mkdir ~/pekaway
cd ~/pekaway

# create folder structure:
cp -r ~/VAN_PI/VanPi-Core-OS/data/* ~/pekaway/

# creating needed files (empty ones)
touch btbmstype van_name dimmeripaddr MACliontron LFBRosON LFBrosOFF LFBrosPLUS LFBrosMINUS installdate boiler_Relay boilertemp_sensor espshuntmac ruuvitag_0_name ruuvitag_1_name ruuvitag_2_name MACmppt ttgoinfo

# wget -O ~/VAN_PI/VanPi-Core-OS/misc/defaultvalues.json ${ServerFiles}misc/defaultvalues.json
json_file="${HOME}/VAN_PI/VanPi-Core-OS/misc/defaultvalues.json"
# Loop through the keys in the JSON file and create files with default values
jq -r 'to_entries | .[] | "\(.key)=\(.value)"' "$json_file" | while IFS='=' read -r filename value; do
    echo "$value" > "$filename"
done

sudo apt install python3-pip -y

# install python modules locally (user pi) and globally (root)
echo "Installing Python modules with --break-system-packages, please stand by..."
sudo -H pip3 install --upgrade pip --break-system-packages
sudo pip3 install -r ~/VAN_PI/VanPi-Core-OS/piplist.txt --break-system-packages
sudo pip3 install bottle --break-system-packages
pip3 install -r ~/VAN_PI/VanPi-Core-OS/piplist.txt --break-system-packages
pip3 install bottle --break-system-packages

# Intalling powersave mode systemd service for wifi connection 
echo "Installing powersave mode for wifi connection"
show_progress "checking powersave mode for wifi"

SERVICE_NAME="wifi-powersave-off.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

# Detect RPi model
PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
echo "Detected model: $PI_MODEL"

# Optional: skip for non-Raspberry Pi systems
if [[ "$PI_MODEL" != Raspberry* ]]; then
    echo "Not a Raspberry Pi. Skipping WiFi power save config."
    exit 0
fi

# Check if service already exists
if [ ! -f "$SERVICE_PATH" ]; then
    echo "Installing $SERVICE_NAME..."

    cat <<EOF | sudo tee "$SERVICE_PATH" > /dev/null
[Unit]
Description=Disable WiFi Power Save Mode
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/sbin/iw dev wlan0 set power_save off
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reexec
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"

    echo "$SERVICE_NAME installed and started."
else
    echo "$SERVICE_NAME already installed. Ensuring it's enabled and started..."
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
fi


# install Node-RED including Node and npm
echo -e "${Cyan}Installing/updating Node-RED, NodeJS and npm${NC}"
cd ~/
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered) --node20 --confirm-install --confirm-pi --no-init
sudo systemctl enable nodered.service
echo -e "${Cyan}Starting Node-RED for initial setup...${NC}"
sudo systemctl start nodered.service
echo -e "${Cyan}Sleeping for 20s to let Node-RED do it's thing...${NC}"
sleep 20
echo -e "${Cyan}Stopping Node-RED${NC}"
sudo systemctl stop nodered.service

# install Node-RED modules
echo -e "${Cyan}Installing/updating Node-RED modules...${NC}"
cd ~/.node-red
rm package.json
rm package-lock.json
cp ~/VAN_PI/VanPi-Core-OS/node-red/package.json .
echo -e "${Cyan}Please stand by! This may take a while!${NC}"
echo -e "${Yellow}It may look frozen, but it is not! Please leave it running and wait patiently.${NC}"
echo -e "${Yellow}Go grab a coffee and relax for a while, I'll take care of the rest :)${NC}"
npm install
npm update
# install Node-RED Pekaway VanPi flows
echo -e "${Cyan}Installing/updating Node-RED Pekaway VanPi flows...${NC}"
rm ~/.node-red/flows.json
cd ~/pekaway
cp ~/VAN_PI/VanPi-Core-OS/node-red/flows_pekaway.json ~/.node-red/flows_pekaway.json
cd ~/.node-red/node_modules/node-red-dashboard/dist
cp ~/VAN_PI/VanPi-Core-OS/node-red/icons.zip .
mv ~/.node-red/node_modules/node-red-dashboard/dist/icon64x64.png ~/.node-red/node_modules/node-red-dashboard/dist/icon64x64_old.png
mv ~/.node-red/node_modules/node-red-dashboard/dist/icon120x120.png ~/.node-red/node_modules/node-red-dashboard/dist/icon120x120_old.png
mv ~/.node-red/node_modules/node-red-dashboard/dist/icon192x192.png ~/.node-red/node_modules/node-red-dashboard/dist/icon192x192_old.png
unzip icons.zip

# install usbreset.c
echo -e "${Cyan}Installing and compiling usbreset.c...${NC}"
cd ~/
cp ~/VAN_PI/VanPi-Core-OS/misc/usbreset.c .
sudo gcc usbreset.c -o usbreset
sudo mv usbreset /usr/local/sbin/

# install and configure Access Point
# Access Point is configured with NR during first startup after installing

# install and configure Nginx
echo -e "${Cyan}Installing and configuring Nginx${NC}"
sudo apt update && sudo apt install nginx -y
sudo cp ~/VAN_PI/VanPi-Core-OS/nginx/pekaway1 /etc/nginx/sites-available/pekaway1
sudo ln -s /etc/nginx/sites-available/pekaway1 /etc/nginx/sites-enabled/
# remove the "default_server" statement fomr the default server block
sudo sed -i 's/default_server//g' /etc/nginx/sites-available/default
sudo systemctl reload nginx
sudo systemctl enable nginx


MOSQUITTO_CONFIG_FILE="/etc/mosquitto/mosquitto.conf"
MOSQUITTO_KEYWORD="allow_anonymous"

# install Mosquitto MQTT Server (probably already installed from packages.txt)
echo -e "${Cyan}Installing Mosquitto MQTT broker${NC}"
sudo apt install mosquitto mosquitto-clients -y
sudo mkdir -p /var/log/mosquitto
sudo touch /var/log/mosquitto/mosquitto.log
sudo chmod 0666 /var/log/mosquitto/mosquitto.log

# Check if the file already contains the allow_anonymous setting
if grep -q "^$MOSQUITTO_KEYWORD" "$MOSQUITTO_CONFIG_FILE"; then
    # Update the line if it's not set to true
    if ! grep -q "^$MOSQUITTO_KEYWORD true" "$MOSQUITTO_CONFIG_FILE"; then
        sed -i "s/^$MOSQUITTO_KEYWORD .*/$MOSQUITTO_KEYWORD true/" "$MOSQUITTO_CONFIG_FILE"
        echo "Updated: $MOSQUITTO_KEYWORD set to true in $MOSQUITTO_CONFIG_FILE"
    else
        echo "No changes needed: $MOSQUITTO_KEYWORD is already set to true in $MOSQUITTO_CONFIG_FILE"
    fi
else
    # Add the setting to the configuration file
    echo "$MOSQUITTO_KEYWORD true" >> "$MOSQUITTO_CONFIG_FILE"
    echo "Added: $MOSQUITTO_KEYWORD set to true in $MOSQUITTO_CONFIG_FILE"
fi

# implementing new udev rules and restarting udev service
echo -e "${Cyan}Implementing udev rules for serial connections{NC}"
sudo mv ~/VAN_PI/VanPi-Core-OS/misc/98-pekaway-tty.rules /etc/udev/rules.d/98-pekaway-tty.rules;
sudo udevadm control --reload-rules & sudo systemctl restart udev.service

# install Homebridge
echo -e "${Cyan}Installing and configuring Homebridge for Apple Homekit${NC}"
sudo chown -R 1000:1000 "${HOME}/.npm"
sudo apt install homebridge
echo -e "${Cyan}Installing Mqttthing for Homebridge${NC}"
sudo -E -n npm install -g homebridge-mqttthing@latest
cd ~/pekaway
sudo cp -r ~/VAN_PI/VanPi-Core-OS/homebridge/config.json /var/lib/homebridge/config.json

# install Zigbee2MQTT
echo -e "${Cyan}Installing Zigbee2MQTT${NC}"
sudo mkdir /opt/zigbee2mqtt
sudo chown -R ${USER}: /opt/zigbee2mqtt
sudo chown -R 1000:1000 "${HOME}/.npm"
git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git /opt/zigbee2mqtt
cd /opt/zigbee2mqtt && npm ci
echo -e "${Cyan}Downloading config files for Zigbee2MQTT${NC}"
cd ~/pekaway
sudo cp -r ~/VAN_PI/VanPi-Core-OS/zigbee/configuration.yaml /opt/zigbee2mqtt/data/configuration.yaml
sudo cp -r ~/VAN_PI/VanPi-Core-OS/zigbee/zigbee2mqtt.service /etc/systemd/system/

# Intalling powersave mode systemd service for wifi connection 
echo "Installing powersave mode for wifi connection"
show_progress "checking powersave mode for wifi"

SERVICE_NAME="wifi-powersave-off.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

# Detect RPi model
PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
echo "Detected model: $PI_MODEL"

# Optional: skip for non-Raspberry Pi systems
if [[ "$PI_MODEL" != Raspberry* ]]; then
    echo "Not a Raspberry Pi. Skipping WiFi power save config."
    exit 0
fi

# Check if service already exists
if [ ! -f "$SERVICE_PATH" ]; then
    echo "Installing $SERVICE_NAME..."

    cat <<EOF | sudo tee "$SERVICE_PATH" > /dev/null
[Unit]
Description=Disable WiFi Power Save Mode
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/sbin/iw dev wlan0 set power_save off
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reexec
    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"

    echo "$SERVICE_NAME installed and started."
else
    echo "$SERVICE_NAME already installed. Ensuring it's enabled and started..."
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
fi

# get and move tft files for NSPanel and touchdisplay to the correct destination
echo -e "${Cyan}Downloading .tft files for NSPanel and Pekaway Touchdisplay${NC}"
mv ~/VAN_PI/VanPi-Core-OS/data/userdata/NSPanel/VanPI_NSPANEL.tft ~/pekaway/userdata/NSPanel/VanPI_NSPANEL.tft
mv ~/VAN_PI/VanPi-Core-OS/data/userdata/NSPanel/autoexec.be ~/pekaway/userdata/NSPanel/autoexec.be
sudo rm /boot/*.tft
sudo chown root:root ~/VAN_PI/VanPi-Core-OS/touchdisplay/PekawayTouch.tft # cannot preserve ownership in root directory
sudo mv ~/VAN_PI/VanPi-Core-OS/touchdisplay/PekawayTouch.tft /boot/PekawayTouch.tft

# move the original pythonsqlite.db file to the correct location
mv ~/VAN_PI/VanPi-Core-OS/misc/pythonsqlite.db ~/pekaway/pythonsqlite.db

## create the initial Hotspot.nmconnection file
echo -e "${Cyan}Creating the initial Hotspot.nmconnection file${NC}"
# Extracting the serial number from the device and taking the characters from position 9 to the random MAX value
MAX=$(shuf -i 12-14 -n 1)
SERIAL_NUMBER=$(cat /sys/firmware/devicetree/base/serial-number | cut -c 9-$MAX)
# Combining the base SSID "VanPiControl_" with the extracted serial number
SSID="VanPiControl_${SERIAL_NUMBER}"
# Variables for hotspot configuration
PASSWORD="pekawayfetzt"      # Set your hotspot password
INTERFACE="wlan0"          # Wireless interface to use (change if necessary)
#UUID=$(cat /proc/sys/kernel/random/uuid) # Generate a UUID from the kernel
echo -e "${Yellow}Initial SSID ${SSID} with password '${PASSWORD}'${NC}"
echo -e "${Yellow}The SSID '${SSID}' will change on the next boot process! (Only this one time, not on every boot process)'${NC}"
# Creating the  with the required hotspot configuration
sudo nmcli con add type wifi ifname wlan0 mode ap con-name Hotspot ssid ${SSID} autoconnect false
sudo nmcli con modify Hotspot 802-11-wireless.band bg ipv4.method shared ipv4.address 192.168.4.1/24
sudo nmcli con modify Hotspot ipv6.method disabled
sudo nmcli con modify Hotspot wifi-sec.key-mgmt wpa-psk
sudo nmcli con modify Hotspot wifi-sec.psk "pekawayfetzt"
sudo nmcli con up Hotspot

# Set permissions for the .nmconnection file
sudo chmod 600 "$FILE_PATH"
# clear files
echo -e "${Cyan}Clearing folders and files...${NC}"
sudo rm -rf ~/VAN_PI

# make all .sh files executable
find ~/pekaway -type f -name "*.sh" -exec chmod +x {} \;
# set 0755 permissions on all python files
find ~/pekaway -type f -name "*.py" -exec chmod 0755 {} \;
# restart Services
echo -e "${Cyan}Restarting services...${NC}"
sudo systemctl daemon-reload
echo -e "${Cyan}zigbee2mqtt.service is not started/enabled by default!${NC}"
sudo systemctl restart nginx.service homebridge.service mosquitto.service nodered.service bluetooth NetworkManager
sudo chmod 0755 ~/pekaway/ds18b20_py/ds18b20.py
sudo systemctl enable bluetooth
echo -e "${Cyan}Turning off swapfile!${NC}"
sudo swapoff -a
sleep 5
sudo service dphys-swapfile stop
sudo systemctl disable dphys-swapfile

# configure /boot/firmware/cmdline.txt
echo -e "${Cyan}Configuring cmdline.txt...${NC}"
sudo sed -i 's/^.*root=PARTUUID/root=PARTUUID/' /boot/firmware/cmdline.txt
sed -i 's/flows.json/flows_pekaway.json/g' ~/.node-red/settings.js
sed -i 's/theme: "",/theme: "",\n        header: {\n            title: "Pekaway VAN PI Campercontrol",\n        },/g' ~/.node-red/settings.js
sudo systemctl restart nodered.service

# Clean up unnecessary package files to free space
echo -e "${Cyan}Cleaning up unnecessary package files to free space${NC}"
sudo apt clean

# Remove unused packages and dependencies
sudo apt autoremove -y

end=`date +%s`
enddate=`date`
runtime=$((end-start))
echo -e "-----------------------------------------"
echo -e "${Cyan}Script started: ${NC}${startdate}"
echo -e "${Cyan}Script ended: ${NC}${enddate}"
echo -e "${Red}Script runtime in Seconds: ${NC}${runtime}"

# reboot Raspberry Pi
echo -e "${Yellow}Installation done, reboot needed!${NC}"
echo -e "${Red}If connection is lost, RPI will reboot into Access Point Mode automatically, \nPlease connect to the access point (VanPiControl_xxx) and proceed from there. Or use a wired connection instead${NC}"
echo -e "${Red}Or use a wired connection instead, which is always preferred${NC}"
echo -e "${Red}--> logfile is saved at ${LOG_FILE}${NC}"
echo "yes" > ~/pekaway/firstboot

while true; do
	read -r -p "Do you want to reboot now? [y/n]" input
	 
	case $input in
		  [yY][eE][sS]|[yY])
				sudo reboot
				break;;
		  [nN][oO]|[nN])
				echo "Reboot cancelled, please remember to reboot for the VanPi system to work properly!"
				exit
				;;
		  *)
				echo "Invalid input... please type 'y' (yes) or 'n' (no)"
				;;
	esac
done
