#!/bin/bash

########################################################
#														
# This script will update your existing VanPi OS 		
# to the latest release from the Pekaway VanPi server!	
# Simply download the script to your VanPi OS and		
# execute it.											
# (see https://github.com/Pekaway/VAN_PI for details)
#
########################################################

# define variables
Server='https://raw.githubusercontent.com/Pekaway/VAN_PI/main/VanPi-Core-OS/'
ServerFiles='https://github.com/Pekaway/VAN_PI/raw/main/VanPi-Core-OS/'
LfsServerFiles='https://media.githubusercontent.com/media/Pekaway/VAN_PI/main/VanPi-Core-OS/'
Version='v2.0.9'		### <--- set new version number VanPi OS
NSPanelVersion='0.0.1'	### <--- set new version number NSPanel
TouchdisplayVersion='2.0.4'	### <--- set new version number Touchdisplay
currentVersion=`cat ~/pekaway/version`

# Define the file for logrotate and the desired line value
LOGROTATE_CONFIG_FILE="/etc/logrotate.conf"
LOGROTATE_TARGET_KEY="maxsize"
LOGROTATE_TARGET_VALUE="60M"
# Define the file for log2ram and the desired line value
LOG2RAM_CONFIG_FILE="/etc/log2ram.conf"
LOG2RAM_TARGET_KEY="LOG_DISK_SIZE"
LOG2RAM_TARGET_VALUE="256M"

# prepare variables to be compared
VersionToCheck='v2.0.0' # Version that has relevant changes in update script
# (if current version number is below that number than this script will execute without the need for confirmation)
# (script will not ask for confirmation if started from Node-RED dashboard directly)


# truncate log folder to make space
# 1) Trim big logs first
# 2) If still almost full, aggressively trim the largest files
# 3) Try to rotate logs (best effort)

echo "checking space in log folder..."

sudo bash -c '
find /var/log -type f -size +2M -exec truncate -s 0 {} \;

usage=$(df --output=pcent /var/log | tail -n1 | tr -dc "0-9")
if [ "$usage" -ge 98 ]; then
  echo "/var/log still at ${usage}%, trimming largest files..."
  # take top 5 largest files and truncate them
  find /var/log -type f -printf "%s %p\n" \
    | sort -nr \
    | head -n 5 \
    | awk "{print \$2}" \
    | while read -r f; do
        truncate -s 0 "$f" || true
      done
fi

logrotate -f /etc/logrotate.conf || true
'
echo "done, starting real update"

# create file for progressbar in NR dashboard
Progress=/var/log/pekaway-update_progress.log
sudo truncate -s 0 ${Progress}
sudo chmod 0666 ${Progress}
echo "PID="$$ | sudo tee ${Progress} # get the PID
# Initialize current step
currentStep=1
# Dynamically count total steps, subtracting 2 for non-literal steps
steps=$(grep -o 'show_progress' "$0" | wc -l)
steps=$((steps - 3))

# Function to display progress
show_progress() {
    echo "Step $currentStep/$steps: $1" | sudo tee ${Progress}
    ((currentStep++))
    sleep 1
}

sleep 7
show_progress "comparing versions"

# create logfile and make it writable
LOG_FILE=/var/log/pekaway-update_$(date +"%Y_%m_%d-%H_%M").log
sudo touch ${LOG_FILE}
sudo chmod 0666 ${LOG_FILE}

exec 3<&1
coproc mytee { tee ${LOG_FILE} >&3;  }
exec >&${mytee[1]} 2>&1

# Remove the 'v' prefix and split into components
VersionSubstring=${Version#*v}
currentVersionSubstring=${currentVersion#*v}

IFS='.' read -ra version_array <<< "$VersionSubstring"
IFS='.' read -ra currentVersion_array <<< "$currentVersionSubstring"

# Extract components as integers
newVersion1=${version_array[0]}
newVersion2=${version_array[1]}
newVersion3=${version_array[2]}

currentVersion1=${currentVersion_array[0]}
currentVersion2=${currentVersion_array[1]}
currentVersion3=${currentVersion_array[2]}

echo "---------------------------------------------------------------------------------------------------"
echo "#-#-#-#-# This script needs to be run as a sudo user. Press CTRL+C to abort at any time. #-#-#-#-# "
echo "              (Not with sudo command, but the user needs permissions to use sudo)"
echo "---------------------------------------------------------------------------------------------------"
echo -e "logfile will be at ${LOG_FILE}"
echo "---------------------------------------------------------------------------------------------------"

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
    versions=("buster" "bullseye" "bookworm" "trixie")

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


# Compare versions numerically
if (( currentVersion1 < newVersion1 )); then
    echo "currentVersion ($currentVersion) is older than newVersion ($Version)"
    needUpdate='true'
elif (( currentVersion1 == newVersion1 && currentVersion2 < newVersion2 )); then
    echo "currentVersion ($currentVersion) is older than newVersion ($Version)"
    needUpdate='true'
elif (( currentVersion1 == newVersion1 && currentVersion2 == newVersion2 && currentVersion3 < newVersion3 )); then
    echo "currentVersion ($currentVersion) is older than newVersion ($Version)"
    needUpdate='true'
elif (( currentVersion1 == newVersion1 && currentVersion2 == newVersion2 && currentVersion3 == newVersion3 )); then
    echo "currentVersion ($currentVersion) is the same as newVersion ($Version)"
    needUpdate='false'
else
    echo "currentVersion ($currentVersion) is newer than newVersion ($Version)"
    needUpdate='false'
fi

# get confirmation to continue on manual update
if [[ "$1" == "node-red-auto-update" ]] || [[ "$needUpdate" == 'true' ]]; then
	echo -e "not asking for confirmation, proceeding automatically."
else
	while true; do
		read -r -p "This will update to version ${Version}! Currently you are running version ${currentVersion}. Do you want to continue [y/n]" input
		case $input in
			  [yY][eE][sS]|[yY])
					echo "Ok, proceeding..."
					break;;
			  [nN][oO]|[nN])
					echo "Aborting... bye bye."
					exit
					;;
			  *)
					echo "Invalid input... please type 'y' (yes) or 'n' (no)"
					;;
		esac
	done
fi
sleep 3
show_progress "getting new files"

# remove packages.txt and package.json if they already exist
cd ~/pekaway
rm -f updatescript.sh
rm -f packages.txt
rm -f package.json
rm -f pip3list.txt
rm -f VanPI_NSPANEL.tft
rm -f autoexec.be
rm -f /ads_py/simplelevel.py
rm -f /ads_py/web2.py
rm -f /ds18b20_py/ds18b20.py
mkdir -p ~/pekaway/bmi270_project
rm -f /bmi270_project/bmi270_demo

sudo rm -f /boot/*.tft # delete old .tft for touchdisplay if it exists
sudo rm -f /boot/firmware/*.tft # delete old .tft for touchdisplay if it exists

#delete files to be replaced here (e.g. updates in scripts)
#rm -f ~/pekaway/ble_py/supervolt_flybat.py

# Switch to reliable DNS servers (Google DNS and Cloudflare DNS):
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 1.1.1.1" | sudo tee -a /etc/resolv.conf

# Array to track failed downloads
failed_downloads=()

# Function for retry logic
wget_retry() {
    local url=$1
    local max_retries=5
    local count=0
    until wget -N --no-use-server-timestamps "$url"; do
        count=$((count + 1))
        if [ $count -ge $max_retries ]; then
            echo "Failed to download $url after $max_retries attempts."
            failed_downloads+=("$url") # Log the failed URL
            return 1
        fi
        echo "Retrying download: $url ($count/$max_retries)..."
        sleep 3
    done
}

echo "Pre-fetching DNS..."
ping -c 1 $ServerFiles > /dev/null 2>&1
ping -c 1 $LfsServerFiles > /dev/null 2>&1
sleep 1

# Download files with retries
echo "Downloading new files..."
wget_retry "${ServerFiles}packages.txt"
sleep 1
wget_retry "${ServerFiles}node-red/package.json"
sleep 1
wget_retry "${ServerFiles}piplist.txt"
sleep 1
wget_retry "${ServerFiles}data/userdata/NSPanel/VanPI_NSPANEL.tft"
sleep 1
wget_retry "${ServerFiles}data/userdata/NSPanel/autoexec.be"
sleep 1
wget_retry "${ServerFiles}data/ads_py/simplelevel.py"
sleep 1
wget_retry "${ServerFiles}data/ads_py/web2.py"
sleep 1
wget_retry "${ServerFiles}data/ds18b20_py/ds18b20.py"
sleep 1
wget_retry "${ServerFiles}data/bmi270_project/bmi270_demo"
sleep 1
wget_retry "${ServerFiles}data/ci2mqtt/ci_mqtt_bridge"
sleep 1
wget_retry "${ServerFiles}data/ci2mqtt/.env"
sleep 1
wget_retry "${ServerFiles}misc/boot_config.txt"
sleep 1
wget_retry "${ServerFiles}misc/98-pekaway-tty.rules"
sleep 1
wget_retry "${ServerFiles}nginx/pekaway1"
sleep 1
wget_retry "${ServerFiles}misc/pythonsqlite.db"
sleep 1
wget_retry "${ServerFiles}touchdisplay/PekawayTouch.tft"
sleep 1


# create files for mcp inputs if the don't exist
# add json into files if they don't exist
for i in {1..16}
do
	touch ~/pekaway/mcpinput"$i"
	touch ~/pekaway/mcpinput"$i"_type
	relays=$(cat < ~/pekaway/mcpinput"$i" |  jq 'has("relays")')
	dimmers=$(cat < ~/pekaway/mcpinput"$i" |  jq 'has("dimmers")')
	type=$(cat ~/pekaway/mcpinput"$i"_type)
	echo "Relays$i: $relays"
	echo "Dimmers$i: $dimmers"
	echo "Type$i: $type"
	if [[ "$type" != "switch" && "$type" != "button" ]]; then
		echo 'switch' > ~/pekaway/mcpinput"$i"_type
	fi
	if [[ "$relays" == "true" ]] 
	then
		if [[ "$dimmers" != "true" ]]; then	
		input=$(jq ' . += {"dimmers":{"d1":false,"d2":false,"d3":false,"d4":false,"d5":false,"d6":false,"d7":false}}' ~/pekaway/mcpinput"$i")
		echo "$input" > ~/pekaway/mcpinput"$i"
		fi
	elif [[ "$relays" != "true" ]]; then
		echo '{"relays":{"one":false,"two":false,"three":false,"four":false,"five":false,"six":false,"seven":false,"eight":false},"dimmers":{"d1":false,"d2":false,"d3":false,"d4":false,"d5":false,"d6":false,"d7":false}}' > ~/pekaway/mcpinput"$i"
	fi
done

# create needed files if they dont exist
touch ~/pekaway/combined_temp_chart
touch ~/pekaway/combined_ruuvi_chart
# create relayboard_core file if it doesn't exist with defgault value "false"
FILE=~/pekaway/relayboard_core
if [ ! -f "$FILE" ]; then
    echo "false" > "$FILE"
fi
# Create Dimmy Pro RGBW definition files with JSON if they don't exist
FILE1=~/pekaway/dimmyProRgbw1
FILE2=~/pekaway/dimmyProRgbw2

if [ ! -f "$FILE1" ]; then
    echo '{"isRgbw": true, "name": "Dimmy Pro RGBW 1"}' > "$FILE1"
fi
if [ ! -f "$FILE2" ]; then
    echo '{"isRgbw": true, "name": "Dimmy Pro RGBW 2"}' > "$FILE2"
fi
# create relayboard_core file if it doesn't exist with defgault value "false"
FILE3=~/pekaway/trumaCi
if [ ! -f "$FILE3" ]; then
    echo "false" > "$FILE3"
fi

# move TouchDisplay .tft file to /boot to be able to use SD-card to update Touchdisplay
sudo chown root:root PekawayTouch.tft # cannot preserve ownership in root directory
sudo rm /boot/*.tft
sudo rm /boot/firmware/*.tft
sudo mv PekawayTouch.tft /boot/firmware/PekawayTouch${TouchdisplayVersion}.tft


# move new files here
mv -f ds18b20.py ~/pekaway/ds18b20_py/ds18b20.py
mv -f simplelevel.py ~/pekaway/ads_py/simplelevel.py
mv -f web2.py ~/pekaway/ads_py/web2.py
mv -f bmi270_demo ~/pekaway/bmi270_project/bmi270_demo
chmod 755 ~/pekaway/bmi270_project/bmi270_demo
mv -f pythonsqlite.db ~/pekaway/pythonsqlite.db
mkdir ~/pekaway/ci2mqtt
mv -f ci_mqtt_bridge ~/pekaway/ci2mqtt/ci_mqtt_bridge
chmod 755 ~/pekaway/ci2mqtt/ci_mqtt_bridge
mv -f .env ~/pekaway/ci2mqtt/.env
sudo chown root:root boot_config.txt
sudo mv -f boot_config.txt /boot/firmware/config.txt
sudo mv -f 98-pekaway-tty.rules /etc/udev/rules.d/98-pekaway-tty.rules
sudo mv -f pekaway1 /etc/nginx/sites-available/pekaway1
# create symlink for nginx pekaway1
sudo ln -s /etc/nginx/sites-available/pekaway1 /etc/nginx/sites-enabled/pekaway1
#mv supervolt_flybat.py ~/pekaway/ble_py/supervolt_flybat.py

sleep 2
# reload udev rules and nginx
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo systemctl restart nginx
sleep 1

show_progress "installing packages"
# copy NSPanel .tft file to ~/pekaway/userdata/NSPanel to show up in NR-Dashboard
mkdir -p ~/pekaway/userdata/NSPanel
cp -f VanPI_NSPANEL.tft ~/pekaway/userdata/NSPanel/VanPI_NSPANEL${NSPanelVersion}.tft
cp -f autoexec.be ~/pekaway/userdata/NSPanel/autoexec.be

# make a backup of the existing package.json and replace it with the new file
cp ~/.node-red/package.json ~/pekaway/nrbackups/package-backup.json
cp ~/pekaway/package.json ~/.node-red/package.json

# Update package list
sudo apt update

# Upgrade all installed packages while keeping existing configuration files
sudo apt upgrade -y -o Dpkg::Options::="--force-confold"

# Install packages listed in ~/pekaway/packages.txt and keep old config files
sudo apt install -y -o Dpkg::Options::="--force-confold" $(cat ~/pekaway/packages.txt)

# Clean up unnecessary package files to free space
sudo apt clean

# Remove unused packages and dependencies
sudo apt autoremove -y

cd ~/.node-red

# compare older package.json with new one and ask for merging
echo "comparing original package.json with the new one:"
sleep 3
show_progress "checking package.json"

extramodules=$(diff <(jq --sort-keys .dependencies ~/.node-red/package.json) \
                    <(jq --sort-keys .dependencies ~/pekaway/nrbackups/package-backup.json) | grep '>')

if [[ -n $extramodules ]]; then
    echo -e "Your original package.json file has the following additonal modules listed:"
    echo -e "$extramodules"

    if [[ "$1" == "node-red-auto-update" ]] || [[ "$needUpdate" == 'true' ]]; then
        echo -e "updating from Node-RED, adding additional lines automatically."
        # merge to temp
        jq -s '.[0] * .[1]' ~/.node-red/package.json ~/pekaway/nrbackups/package-backup.json > ~/pekaway/nrbackups/package1.json
        # pretty print
        jq . ~/pekaway/nrbackups/package1.json > ~/pekaway/nrbackups/pretty.json
        # replace target (THIS is the missing write-back)
        mv ~/pekaway/nrbackups/pretty.json ~/.node-red/package.json
        # cleanup
        rm -f ~/pekaway/nrbackups/package1.json
        echo "Missing lines have been added to package.json"
        echo "New package.json:"
        cat ~/.node-red/package.json
    else
        while true; do
            read -r -p "Do you want them to be added to the new package.json? [y/n]" input
            case $input in
                [yY][eE][sS]|[yY])
                    # merge to temp
                    jq -s '.[0] * .[1]' ~/.node-red/package.json ~/pekaway/nrbackups/package-backup.json > ~/pekaway/nrbackups/package-backup1.json
                    # pretty print
                    jq . ~/pekaway/nrbackups/package-backup1.json > ~/pekaway/nrbackups/pretty.json
                    # keep a backup just in case
                    mv ~/pekaway/nrbackups/package-backup.json ~/pekaway/package-backup.json
                    # replace target
                    mv ~/pekaway/nrbackups/pretty.json ~/.node-red/package.json
                    # cleanup
                    rm -f ~/pekaway/nrbackups/package1.json ~/pekaway/nrbackups/package-backup1.json 2>/dev/null
                    echo "Missing lines have been added to package.json"
                    echo "New ~/.node-red/package.json:"
                    cat ~/.node-red/package.json
                    break
                    ;;
                [nN][oO]|[nN])
                    echo "No modules added to package.json, proceeding..."
                    break
                    ;;
                *)
                    echo "Invalid input... please type 'y' (yes) or 'n' (no)"
                    ;;
            esac
        done
    fi
else
    echo "modules are identical, proceeding..."
fi


#install npm modules from package.json
sleep 3
show_progress "executing npm install"
echo "installing npm modules, please stand by..."
npm install
echo "done"

cd ~/pekaway
# Install/update python modules locally (user pi) and globally (root)
sleep 3
show_progress "checking python modules"
echo "Installing Python modules with --break-system-packages, please stand by..."
sudo -H pip3 install --upgrade pip --break-system-packages
sudo pip3 install -r ~/pekaway/piplist.txt --break-system-packages
sudo pip3 install bottle --break-system-packages
pip3 install -r ~/pekaway/piplist.txt --break-system-packages
pip3 install bottle --break-system-packages
echo "Done."

sleep 3
show_progress "checking logrotate/log2ram"
# Check logrotate configuration
# Check if the file exists
if [ ! -f "$LOGROTATE_CONFIG_FILE" ]; then
    echo "The file $LOGROTATE_CONFIG_FILE does not exist. Exiting this step."
    exit 0
fi

# Check if the line exists and matches the target value
if grep -q "^$LOGROTATE_TARGET_KEY $LOGROTATE_TARGET_VALUE" "$LOGROTATE_CONFIG_FILE"; then
    echo "The line '$LOGROTATE_TARGET_KEY $LOGROTATE_TARGET_VALUE' is already set and correct."
else
    # Check if the line exists with a different value
    if grep -q "^$LOGROTATE_TARGET_KEY " "$LOGROTATE_CONFIG_FILE"; then
        echo "The line '$LOGROTATE_TARGET_KEY' exists but has a different value. Updating it..."
        sudo sed -i "s|^$LOGROTATE_TARGET_KEY .*|$LOGROTATE_TARGET_KEY $LOGROTATE_TARGET_VALUE|" "LOGROTATE_$CONFIG_FILE"
    else
        # Add the line if it doesn't exist
        echo "The line '$LOGROTATE_TARGET_KEY' is missing. Adding it..."
        sudo echo "$LOGROTATE_TARGET_KEY $LOGROTATE_TARGET_VALUE" >> "$LOGROTATE_CONFIG_FILE"
    fi
fi


# Check log2ram configuration
# Check if the file exists
if [ ! -f "$LOG2RAM_CONFIG_FILE" ]; then
    echo "The file $LOG2RAM_CONFIG_FILE does not exist. Exiting this step."
    exit 0
fi

# Check if the line exists and matches the target value
if grep -q "^$LOG2RAM_TARGET_KEY=$LOG2RAM_TARGET_VALUE" "$LOG2RAM_CONFIG_FILE"; then
    echo "The line '$LOG2RAM_TARGET_KEY=$LOG2RAM_TARGET_VALUE' is already set and correct."
else
    # Check if the line exists with a different value
    if grep -q "^$LOG2RAM_TARGET_KEY=" "$LOG2RAM_CONFIG_FILE"; then
        echo "The line '$LOG2RAM_TARGET_KEY' exists but has a different value. Updating it..."
        sudo sed -i "s|^$LOG2RAM_TARGET_KEY=.*|$LOG2RAM_TARGET_KEY=$LOG2RAM_TARGET_VALUE|" "$LOG2RAM_CONFIG_FILE"
    else
        # Add the line if it doesn't exist
        echo "The line '$LOG2RAM_TARGET_KEY' is missing. Adding it..."
        sudo echo "$LOG2RAM_TARGET_KEY=$LOG2RAM_TARGET_VALUE" >> "$LOG2RAM_CONFIG_FILE"
    fi
fi

# Restart log2ram
echo "Restarting log2ram..."
#sudo systemctl restart log2ram && echo "log2ram restarted successfully." || echo "Failed to restart log2ram."

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

show_progress "backing up flows"

# remove downloaded files
rm -f ~/pekaway/packages.txt && rm -f ~/pekaway/package.json && rm -f ~/pekaway/piplist.txt

# backup Node-RED flows
echo "backing up original Node-RED flows"
cd ~/pekaway/nrbackups
cp ~/.node-red/flows_pekaway.json "flows_pekaway_$(date +%d-%m-%Y_%I:%M:%S%p).json"

# Define the path to the Node-RED settings.js file
NR_SETTINGS_FILE="$HOME/.node-red/settings.js"

# Define the desired global context key-value pairs
declare -A GLOBAL_CONTEXT=(
    ["zlib"]="require('zlib')"
    #["os"]="require('os')"
    # Add more key-value pairs as needed
)

# Check if the settings.js file exists
if [ ! -f "$NR_SETTINGS_FILE" ]; then
    echo "The settings.js file does not exist at $NR_SETTINGS_FILE. Exiting."
    exit 1
fi

# Check if functionGlobalContext exists
if grep -q "functionGlobalContext:" "$NR_SETTINGS_FILE"; then
    echo "Found functionGlobalContext in settings.js."

    # Loop through desired global context entries
    for KEY in "${!GLOBAL_CONTEXT[@]}"; do
        VALUE=${GLOBAL_CONTEXT[$KEY]}

        # Check if the key already exists and is uncommented
        if grep -q "^    $KEY:$VALUE" "$NR_SETTINGS_FILE"; then
            echo "$KEY is already included in functionGlobalContext and uncommented."
        # Check if the key exists but is commented out
        elif grep -q "^ *// *$KEY:$VALUE" "$NR_SETTINGS_FILE"; then
            echo "$KEY is commented out. Uncommenting it..."
            sed -i "s|^ *// *$KEY:$VALUE|    $KEY:$VALUE|" "$NR_SETTINGS_FILE"
            echo "$KEY uncommented."
        else
            echo "$KEY is missing. Adding it to functionGlobalContext..."

            # Insert the key-value pair into functionGlobalContext
            sed -i "/functionGlobalContext:/,/}/ s|}|    $KEY:$VALUE,\n}|" "$NR_SETTINGS_FILE"

            echo "$KEY added to functionGlobalContext."
        fi
    done
else
    echo "functionGlobalContext not found. Adding it with the desired entries..."

    # Build the functionGlobalContext block dynamically
    CONTEXT_BLOCK="functionGlobalContext: {\n"
    for KEY in "${!GLOBAL_CONTEXT[@]}"; do
        CONTEXT_BLOCK+="    $KEY:${GLOBAL_CONTEXT[$KEY]},\n"
    done
    CONTEXT_BLOCK+="},"

    # Add the block at the end of the file
    echo -e "\n$CONTEXT_BLOCK" >> "$NR_SETTINGS_FILE"

    echo "functionGlobalContext added with the desired entries."
fi


# extract user flows from original flows.json file
echo "Extracting user flows from flows_pekaway.json to extracted_user_flows.json in NR folder"
jq '
. as $all |

($all | map(select(.type == "tab" and (.label | test(".*user\\s*flow.*"; "i"))))) as $tabs |

($tabs | map(.id)) as $tab_ids |

($all | map(select(.z != null and (.z as $z | $tab_ids | index($z))))) as $nodes |

($nodes | map(select(.group? != null) | .group)) as $group_ids |

($all | map(select(.type == "ui_group" and (.id as $id | $group_ids | index($id))))) as $groups |

($groups | map(.tab)) as $ui_tab_ids |

($all | map(select(.type == "ui_tab" and (.id as $id | $ui_tab_ids | index($id))))) as $ui_tabs |

$tabs + $nodes + $groups + $ui_tabs
' ~/.node-red/flows_pekaway.json > ~/.node-red/extracted_user_flows.json

cp ~/.node-red/flows_pekaway.json ~/.node-red/.flows_pekaway.json.bkp

# Download new flows and replace the old file
sleep 3
show_progress "getting new flows"
echo "Replacing local flows.json file with the new one from the server"
cd ~/pekaway/pkwUpdate/
wget_retry "${LfsServerFiles}node-red/flows_pekaway.json"

# Check for failures
flows_success=true
if [ ! -f "flows_pekaway.json" ]; then
    echo "The file flows_pekaway.json failed to download."
    failed_downloads+=("flows_pekaway.json")
    flows_success=false
fi

if [ ${#failed_downloads[@]} -gt 0 ]; then
    echo "The following files failed to download:"
    for file in "${failed_downloads[@]}"; do
        echo "  - $file"
    done
fi

# Decision based on flows_pekaway.json status
if [ "$flows_success" = true ]; then
    # Proceed with updating the flows file
    cp ~/pekaway/pkwUpdate/flows_pekaway.json ~/.node-red/flows_pekaway.json
    echo "Flows file replaced successfully."
else
    echo "Critical: flows_pekaway.json failed to download. Please check the logfile for details."
    echo "Aborting Node-RED restart and script execution."
    echo "Logfile: ${LOG_FILE}"
    show_progress "Error, see logfile"
    sleep 3
    exit 1
fi

# Merge flows_pekaway.json with extracted_user_flows.json and save to merged_flows.json
echo "Merging flows_pekaway.json and extracted_user_flows.json, saving as merged_flows.json"
if [ -s ~/.node-red/extracted_user_flows.json ] && jq empty ~/.node-red/extracted_user_flows.json >/dev/null 2>&1; then
    jq -s '[.[0][] , .[1][]]' ~/.node-red/flows_pekaway.json ~/.node-red/extracted_user_flows.json > ~/.node-red/merged_flows.json &&
    rm ~/.node-red/flows_pekaway.json ~/.node-red/extracted_user_flows.json &&
    mv ~/.node-red/merged_flows.json ~/.node-red/flows_pekaway.json
else
    echo "No valid user flows to merge. Skipping merging."
    rm -f ~/.node-red/extracted_user_flows.json  # Clean up even if it's empty
fi


# Clean up and proceed with the rest of the script
rm ~/pekaway/pkwUpdate/flows_pekaway.json
sleep 3
echo "Replacing version number of VanPi OS"
# Replace version number
echo ${Version} >| ~/pekaway/version
# Set update = true to show up when opening dashboard
echo "1" >| ~/pekaway/update
show_progress "restarting Node-RED..."
sleep 5
sudo truncate -s 0 ${Progress}

# Inform the user about non-critical failed downloads
if [ ${#failed_downloads[@]} -gt 0 ]; then
    echo "Some non-critical files failed to download. Please check the logfile for details."
    echo "Logfile: ${LOG_FILE}"
fi

# Reboot or inform the user
if [[ "$1" == "node-red-auto-update" ]]; then
    echo -e "Not asking for confirmation, rebooting automatically."
    sleep 3
    sudo reboot
else
    while true; do
        read -r -p "Do you want to reboot now? [y/n] " input
        case $input in
            [yY][eE][sS]|[yY])
                sudo reboot
                break
                ;;
            [nN][oO]|[nN])
                echo "Reboot cancelled. Please remember to reboot for the VanPi system to work properly!"
                break
                ;;
            *)
                echo "Invalid input... please type 'y' (yes) or 'n' (no)"
                ;;
        esac
    done
fi

# If no reboot, restart Node-RED
echo "No reboot, will try to restart Node-RED service..."
sudo systemctl restart nodered.service
echo "Exiting now. Bye Bye!"
