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
Server='https://git.pekaway.de/Vincent/vanpi/-/raw/main/pi4/'

# define color variables
Cyan='\033[0;36m'
Red='\033[0;31m'
Yellow='\033[0;33m'
NC='\033[0m' #No Color

# define os-release version
OSRELEASE=`cat /etc/os-release`

echo -e "${Yellow}Logfile will be ${LOG_FILE}${NC}"
# get latest updates
echo -e "${Cyan}updating packages list${NC}"
sudo apt update
echo -e "${Cyan}upgrading packages${NC}"
sudo apt upgrade -y

# enable I2C and 1-Wire
echo -e "${Cyan}Enabling I2C and 1-Wire Bus${NC}"
sudo raspi-config nonint do_i2c 0
echo -e "dtoverlay=w1-gpio\ndtoverlay=uart5\nenable_uart=1" | sudo tee -a /boot/config.txt
sudo debconf-set-selections <<EOF
iptables-persistent iptables-persistent/autosave_v4 boolean true
iptables-persistent iptables-persistent/autosave_v6 boolean true
EOF

# set hostname to pekaway
echo -e "${Cyan}Set hostname to pekaway${NC}"
echo "pekaway" | sudo tee /etc/hostname

# save needed resources to ~/pekaway
echo -e "${Cyan}saving needed resources to ~/pekaway${NC}"
mkdir ~/pekaway
cd pekaway
wget ${Server}home_pi_pekaway_files.zip
unzip ~/pekaway/home_pi_pekaway_files.zip
echo -e "${Cyan}making scripts executable${NC}"
find ~/pekaway/ -type f -iname "*.sh" -exec chmod +x {} \;
chmod 0744 ~/pekaway/availableWifi.txt
chmod 0777 ~/pekaway/pythonsqlite.db
chmod 0755 ~/pekaway/raspi-blinka.py
echo "100" > ~/pekaway/dimmer_maxpercent
echo "yes" > ~/pekaway/firstboot

# get and install needed packages list
echo -e "${Cyan}Saving list with needed packages${NC}"
cd ~/pekaway
wget ${Server}packages_bullseye.txt
wget ${Server}packages_buster.txt
echo -e "${Cyan}Installing needed packages${NC}"

if grep -q "buster" <<< "$OSRELEASE"; then
  echo -e "Installing packages for buster"
  sudo apt-get update
  sudo apt-get upgrade -y
  sudo apt-get install $(cat ~/pekaway/packages_buster.txt) -y
else
  echo -e "Installing packages for bullseye"
  sudo apt install $(cat ~/pekaway/packages_bullseye.txt) -y
  sudo apt install iotop -y
fi
wget ${Server}pip3list.txt
sudo apt install python3-pip -y

# install python modules locally (user pi) and globally (root)
sudo pip3 install -r ~/pekaway/pip3list.txt
sudo pip3 install bottle pexpect argparse gatt
pip3 install -r ~/pekaway/pip3list.txt
pip3 install bottle pexpect argparse gatt

# download files for NSPanel
cd ~/pekaway
wget ${Server}NSPanel/VanPI_NSPANEL.tft
wget ${Server}NSPanel/autoexec.be
mkdir -p ~/pekaway/userdata/NSPanel
cp ~/pekaway/VanPI_NSPANEL.tft ~/pekaway/userdata/NSPanel/VanPI_NSPANEL.tft
cd ~/

# install git
echo -e "${Cyan}Installing git${NC}"
sudo apt install git make build-essential

# install Node-RED including Node and npm
echo -e "${Cyan}Installing/updating Node-RED, NodeJS and npm${NC}"
cd ~/
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered) --node18 --confirm-install --confirm-pi
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
wget ${Server}package.json
echo -e "${Cyan}Please stand by! This may take a while!${NC}"
echo -e "${Yellow}It may look frozen, but it is not! Please leave it running and wait patiently.${NC}"
echo -e "${Yellow}Go grab a coffee and relax for a while, I'll take care of the rest :)${NC}"
npm install

# install Node-RED Pekaway VanPi flows
echo -e "${Cyan}Installing/updating Node-RED Pekaway VanPi flows...${NC}"
cd ~/pekaway
wget ${Server}flows.json
cp flows.json ~/.node-red/flows_pekaway.json
cd ~/.node-red/node_modules/node-red-dashboard/dist
wget ${Server}icons.zip
mv ~/.node-red/node_modules/node-red-dashboard/dist/icon64x64.png ~/.node-red/node_modules/node-red-dashboard/dist/icon64x64_old.png
mv ~/.node-red/node_modules/node-red-dashboard/dist/icon120x120.png ~/.node-red/node_modules/node-red-dashboard/dist/icon120x120_old.png
mv ~/.node-red/node_modules/node-red-dashboard/dist/icon192x192.png ~/.node-red/node_modules/node-red-dashboard/dist/icon192x192_old.png
unzip icons.zip

# install usbreset.c
echo -e "${Cyan}Installing and compiling usbreset.c...${NC}"
cd ~/
wget ${Server}usbreset.c
sudo gcc usbreset.c -o usbreset
sudo mv usbreset /usr/local/sbin/

# install and configure Access Point
echo -e "${Cyan}Installing and configuring Access Point mode...${NC}"
cd ~/
sudo apt install hostapd dnsmasq -y
sudo systemctl unmask hostapd
sudo systemctl enable hostapd
sudo DEBIAN_FRONTEND=noninteractive apt install -y netfilter-persistent iptables-persistent
sudo cp /etc/dhcpcd.conf /etc/dhcpcd_nonap.conf
echo -e "\n interface wlan0 \n   static ip_address=192.168.4.1/24 \n   nohook wpa_supplicant" | sudo tee -a /etc/dhcpcd.conf
sudo cp /etc/dhcpcd.conf /etc/dhcpcd_ap.conf
echo -e "# https://www.raspberrypi.org/documentation/configuration/wireless/access-point-routed.md \n# Enable IPv4 routing \nnet.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/routed-ap.conf
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
sudo netfilter-persistent save
echo -e "# Listening interface\ninterface=wlan0\n# Pool of IP addresses served via DHCP\ndhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h\n# Local wireless DNS domain\ndomain=wlan\n# Alias for this router\naddress=/van.pi/192.168.4.1\naddress=/peka.way/192.168.4.1" | sudo tee /etc/dnsmasq.conf
sudo rfkill unblock wlan
echo -e "country_code=DE\ninterface=wlan0\n\nssid=PeKaWayControl\nhw_mode=g\nchannel=6\nmacaddr_acl=0\nauth_algs=1\nwpa=2\nwpa_passphrase=pekawayfetzt\nwpa_key_mgmt=WPA-PSK\nwpa_pairwise=TKIP\nrsn_pairwise=CCMP\n" | sudo tee /etc/hostapd/hostapd.conf

# install and configure Nginx
echo -e "${Cyan}Installing and configuring Nginx${NC}"
sudo apt update && sudo apt install nginx -y
echo -e "server {\n   listen 80;\n   server_name peka.way pekaway.local vanpi.local van.pi;\n   location / {\n      proxy_pass http://127.0.0.1:1880/ui/;\n   }\n}\nserver {\n   listen 80;\n   server_name homebridge.peka.way hb.peka.way homebridge.van.pi hb.van.pi;\n   location / {\n      proxy_pass http://127.0.0.1:8581/;\n   }\n}" | sudo tee /etc/nginx/sites-available/pekaway1
sudo ln -s /etc/nginx/sites-available/pekaway1 /etc/nginx/sites-enabled/
sudo systemctl reload nginx
sudo systemctl enable nginx

# install Mosquitto MQTT Server (probably already installed from packages.txt)
echo -e "${Cyan}Installing Mosquitto MQTT broker${NC}"
sudo apt install mosquitto mosquitto-clients -y
sudo mkdir -p /var/log/mosquitto
sudo touch /var/log/mosquitto/mosquitto.log
sudo chmod 0666 /var/log/mosquitto/mosquitto.log

# implementing new udev rules and restarting udev service
echo -e "${Cyan}Implementing udev rules for serial connections{NC}"
sudo touch /etc/udev/rules.d/98-pekaway-tty.rules
echo -e 'KERNEL=="ttyUSB*", KERNELS=="1-1.1", SYMLINK+="ttyPKW1"\nKERNEL=="ttyUSB*", KERNELS=="1-1.2", SYMLINK+="ttyPKW2"\nKERNEL=="ttyUSB*", KERNELS=="1-1.3", SYMLINK+="ttyPKW3"\nKERNEL=="ttyUSB*", KERNELS=="1-1.4", SYMLINK+="ttyPKW4"' | sudo tee /etc/udev/rules.d/98-pekaway-tty.rules
sudo cp /etc/udev/rules.d/98-pekaway-tty.rules /lib/udev/rules.d/98-pekaway-tty.rules
sudo udevadm control --reload-rules & sudo systemctl restart udev.service

# install Homebridge
echo -e "${Cyan}Installing and configuring Homebridge for Apple Homekit${NC}"
sudo npm install -g --unsafe-perm homebridge homebridge-config-ui-x
sudo hb-service install --user homebridge
echo -e "${Cyan}Installing Mqttthing for Homebridge${NC}"
sudo -E -n npm install -g homebridge-mqttthing@latest
cd ~/pekaway
wget -q ${Server}config.json -O ~/pekaway/config.json
sudo cp -r ~/pekaway/config.json /var/lib/homebridge/config.json

# install Zigbee2MQTT
echo -e "${Cyan}Installing Zigbee2MQTT${NC}"
sudo mkdir /opt/zigbee2mqtt
sudo chown -R ${USER}: /opt/zigbee2mqtt
git clone --depth 1 https://github.com/Koenkk/zigbee2mqtt.git /opt/zigbee2mqtt
cd /opt/zigbee2mqtt && npm ci
echo -e "${Cyan}Downloading config files for Zigbee2MQTT${NC}"
cd ~/pekaway
curl ${Server}configuration.yaml > /opt/zigbee2mqtt/data/configuration.yaml
sudo wget ${Server}zigbee2mqtt.service
sudo mv zigbee2mqtt.service /etc/systemd/system/

# clear files
echo -e "${Cyan}Clearing folders and files...${NC}"
sudo rm ~/pekaway/home_pi_pekaway_files.zip
sudo rm ~/pekaway/packages.txt
sudo rm ~/pekaway/packages_bullseye.txt
sudo rm ~/pekaway/packages_buster.txt
sudo rm ~/pekaway/pip3list.txt
sudo rm ~/pekaway/flows.json

# restart Services
echo -e "${Cyan}Restarting services...${NC}"
sudo systemctl daemon-reload
echo -e "${Cyan}zigbee2mqtt.service is not started/enabled by default!${NC}"
sudo systemctl restart nginx.service homebridge.service mosquitto.service nodered.service bluetooth
sudo chmod 0755 ~/pekaway/ds18b20_py/ds18b20.py
sudo systemctl enable bluetooth
echo -e "${Cyan}Turning off swapfile!${NC}"
sudo swapoff -a
sleep 5
sudo service dphys-swapfile stop
sudo systemctl disable dphys-swapfile

# configure /boot/cmdline.txt
echo -e "${Cyan}Configuring cmdline.txt...${NC}"
sudo sed -i 's/^.*root=PARTUUID/root=PARTUUID/' /boot/cmdline.txt
sed -i 's/flows.json/flows_pekaway.json/g' ~/.node-red/settings.js
sed -i 's/theme: "",/theme: "",\n        header: {\n            title: "Pekaway VAN PI Campercontrol",\n        },/g' ~/.node-red/settings.js
sudo systemctl restart nodered.service

end=`date +%s`
enddate=`date`
runtime=$((end-start))
echo -e "-----------------------------------------"
echo -e "${Cyan}Script started: ${NC}${startdate}"
echo -e "${Cyan}Script ended: ${NC}${enddate}"
echo -e "${Red}Script runtime in Seconds: ${NC}${runtime}"

# reboot Raspberry Pi
echo -e "${Yellow}Installation done, reboot needed!${NC}"
echo -e "${Red}If connection is lost, RPI will reboot into Access Point Mode automatically, \nPlease connect to the access point (VanPiControl_xxx) and proceed from there${NC}"
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
