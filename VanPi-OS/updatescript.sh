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
Server='https://raw.githubusercontent.com/Pekaway/VAN_PI/main/VanPi-OS/'
ServerFiles='https://github.com/Pekaway/VAN_PI/raw/main/VanPi-OS/'
Version='v1.1.2'		### <--- set new version number VanPi OS
NSPanelVersion='0.0.1'	### <--- set new version number NSPanel
TouchdisplayVersion='1.0.5'	### <--- set new version number Touchdisplay
currentVersion=`cat ~/pekaway/version`
steps='9' ### <--- number of total steps for progessbar

# prepare variables to be compared
VersionToCheck='v1.1.1' # Version that has relevant changes in update script
# (if current version number is below that number than this script will execute without the need for confirmation)
# (script will not ask for confirmation if started from Node-RED dashboard directly)

# create file for progressbar in NR dashboard
Progress=/var/log/pekaway-update_progress.log
sudo truncate -s 0 ${Progress}
sudo chmod 0666 ${Progress}
echo "PID="$$ | sudo tee ${Progress} # get the PID
sleep 7
echo "Step 1/${steps}: comparing versions" | sudo tee ${Progress}

# create logfile and make it writable
LOG_FILE=/var/log/pekaway-update_$(date +"%Y_%m_%d-%H_%M").log
sudo touch ${LOG_FILE}
sudo chmod 0666 ${LOG_FILE}

exec 3<&1
coproc mytee { tee ${LOG_FILE} >&3;  }
exec >&${mytee[1]} 2>&1

# compare current and new version numbers
VersionSubstring=${VersionToCheck#*v}
currentVersionSubstring=${currentVersion#*v}
IFS='.' read -ra currentVersion_array <<< "$currentVersionSubstring"
IFS='.' read -ra version_array <<< "$VersionSubstring"

currentVersion1=${currentVersion_array[0]}
currentVersion2=${currentVersion_array[1]}
currentVersion3=${currentVersion_array[2]}
newVersion1=${version_array[0]}
newVersion2=${version_array[1]}
newVersion3=${version_array[2]}

echo "This script needs to be run as a sudo user. Press CTRL+C to abort at any time."
echo -e "logfile will be at ${LOG_FILE}"

if [[ $currentVersion1 -lt $newVersion1 ]]; then
  echo "currentVersion ($currentVersion) is older than newVersion ($Version)"

elif [[ $currentVersion1 -eq $newVersion1 ]] && [[ $currentVersion2 -lt $newVersion2 ]]; then
  echo "currentVersion ($currentVersion) is older than newVersion ($Version)"
  needUpdate='true'
elif [[ $currentVersion1 -eq $newVersion1 ]] && [[ $currentVersion2 -eq $newVersion2 ]] && [[ $currentVersion3 -lt $newVersion3 ]]; then
  echo "currentVersion ($currentVersion) is older than newVersion ($Version)"
  needUpdate='true'
elif [[ $currentVersion1 -eq $newVersion1 ]] && [[ $currentVersion2 -eq $newVersion2 ]] && [[ $currentVersion3 -eq $newVersion3 ]]; then
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
echo  "Step 2/${steps}: getting new files" | sudo tee ${Progress}

# remove packages.txt and package.json if they already exist
cd ~/pekaway
rm -f updatescript.sh
rm -f packages.txt
rm -f package.json
rm -f pip3list.txt
rm -f VanPI_NSPANEL.tft
rm -f autoexec.be

sudo rm -f /boot/*.tft # delete old .tft for touchdisplay if it exists

#delete files to be replaced here (e.g. updates in scripts)
#rm -f ~/pekaway/ble_py/supervolt_flybat.py

# download new files packages.txt and package.json
echo "downloading new files"
wget ${Server}packages.txt
wget ${Server}package.json
wget ${Server}pip3list.txt
wget ${ServerFiles}NSPanel/VanPI_NSPANEL.tft
wget ${Server}NSPanel/autoexec.be

# get new files here
wget ${Server}newFilesForUpdate/supervolt_flybat.py
wget ${ServerFiles}Touchdisplay/PekawayTouch.tft

# create files for mcp inputs if the don't exist
# add json into files if they don't exist
for i in {1..6}
do
	touch ~/pekaway/mcpinput"$i"
	touch ~/pekaway/mcpinput"$i"_type
	relays=$(cat ~/pekaway/mcpinput"$i" |  jq 'has("relays")')
	dimmers=$(cat ~/pekaway/mcpinput"$i" |  jq 'has("dimmers")')
	type=$(cat ~/pekaway/mcpinput"$i"_type)
	echo "Relays$i: $relays"
	echo "Dimmers$i: $dimmers"
	echo "Type$i: $type"
	if [[ "$type" != "switch" && "$type" != "button" ]]; then
		echo 'switch' > ~/pekaway/mcpinput"$i"_type
	fi
	if [ "$relays" == "true" ]
	then
		if [ "$dimmers" != "true" ]; then
			jq ' . += [{ "dimmers":{"d1":false,"d2":false,"d3":false,"d4":false,"d5":false,"d6":false,"d7":false} }] '
		fi
	elif [ "$relays" != "true" ]; then
		echo '{"relays":{"one":false,"two":false,"three":false,"four":false,"five":false,"six":false,"seven":false,"eight":false},"dimmers":{"d1":false,"d2":false,"d3":false,"d4":false,"d5":false,"d6":false,"d7":false}}' > ~/pekaway/mcpinput"$i"
	fi
done




# move TouchDisplay .tft file to /boot to be able to use SD-card to update Touchdisplay
sudo chown root:root PekawayTouch.tft # cannot preserve ownership in root directory
sudo mv PekawayTouch.tft /boot/PekawayTouch${TouchdisplayVersion}.tft


# move new files here
mv supervolt_flybat.py ~/pekaway/ble_py/supervolt_flybat.py

sleep 3
echo "Step 3/${steps}: installing packages" | sudo tee ${Progress}
# copy NSPanel .tft file to ~/pekaway/userdata/NSPanel to show up in NR-Dashboard
mkdir -p ~/pekaway/userdata/NSPanel
cp VanPI_NSPANEL.tft ~/pekaway/userdata/NSPanel/VanPI_NSPANEL${NSPanelVersion}.tft

# make a backup of the existing package.json and replace it with the new file
cp ~/.node-red/package.json ~/pekaway/nrbackups/package-backup.json
cp ~/pekaway/package.json ~/.node-red/package.json

# install packages and dependencies
sudo apt update
sudo apt install $(cat ~/pekaway/packages.txt) -y
cd ~/.node-red

# compare older package.json with new one and ask for merging
echo "comparing original package.json with the new one:"
sleep 3
echo "Step 4/${steps}: checking package.json" | sudo tee ${Progress}

extramodules=$(diff <(jq --sort-keys .dependencies ~/.node-red/package.json) <(jq --sort-keys .dependencies ~/pekaway/nrbackups/package-backup.json) | grep '>')

if [[ -n $extramodules ]]; then
    echo -e "Your original package.json file has the following additonal modules listed:"
	echo -e "$extramodules"

   if [[ "$1" == "node-red-auto-update" ]] || [[ "$needUpdate" == 'true' ]]; then
	echo -e "updating from Node-RED, adding additional lines automatically."
		# cd ~/.node-red
		echo `jq -s '.[0] * .[1]' ~/.node-red/package.json ~/pekaway/nrbackups/package-backup.json` > ~/pekaway/nrbackups/package1.json && jq . ~/pekaway/nrbackups/package1.json > ~/pekaway/nrbackups/pretty.json && rm ~/pekaway/nrbackups/package1.json && mv ~/pekaway/nrbackups/pretty.json ~/pekaway/nrbackups/package1.json
		echo "Missing lines have been added to package.json"
		echo "New package.json:"
		cat ~/.node-red/package.json
		exit
   else
		while true; do
			read -r -p "Do you want them to be added to the new package.json? [y/n]" input
			case $input in
				  [yY][eE][sS]|[yY])
						# cd ~/.node-red
						echo `jq -s '.[0] * .[1]' ~/.node-red/package.json ~/pekaway/nrbackups/package-backup.json` > ~/pekaway/nrbackups/package-backup1.json
						jq . ~/pekaway/nrbackups/package-backup1.json > ~/pekaway/nrbackups/pretty.json 
						mv ~/pekaway/nrbackups/package-backup.json ~/pekaway/package-backup.json # keep backup just in case
						rm -f ~/pekaway/nrbackups/package1.json
						mv ~/pekaway/nrbackups/pretty.json ~/.node-red/package.json
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
echo "Step 5/${steps}: executing npm install" | sudo tee ${Progress}
echo "installing npm modules, please stand by..."
npm install
echo "done"

cd ~/pekaway
# Install/update python modules locally (user pi) and globally (root)
sleep 3
echo "Step 6/${steps}: checking python modules" | sudo tee ${Progress}
echo "installing python modules, please stand by..."
sudo -H pip3 install --upgrade pip 
sudo pip3 install -r ~/pekaway/pip3list.txt
sudo pip3 install bottle
pip3 install -r ~/pekaway/pip3list.txt
pip3 install bottle
echo "done"

sleep 3
echo "Step 7/${steps}: backing up flows" | sudo tee ${Progress}

# remove downloaded files
rm -f ~/pekaway/packages.txt && rm -f ~/pekaway/package.json && rm -f ~/pekaway/pip3list.txt

# backup Node-RED flows
echo "backing up original Node-RED flows"
cd ~/pekaway/nrbackups
cp ~/.node-red/flows_pekaway.json "flows_pekaway_$(date +%d-%m-%Y_%I:%M:%S%p).json"

echo "replacing version number of VanPi OS"
# replace version number
echo ${Version} >| ~/pekaway/version

# set update = true to show up when opening dashboard
echo "1" >| ~/pekaway/update

# download new flows and replace the old file
sleep 3
echo "Step 8/${steps}: getting new flows" | sudo tee ${Progress}
echo "replacing local flows.json file with new one from the server"
curl ${Server}flows.json > ~/pekaway/pkwUpdate/flows_pekaway.json 
cp ~/pekaway/pkwUpdate/flows_pekaway.json ~/.node-red/flows_pekaway.json
echo "update script finished! You can find the logfile at ${LOG_FILE}."
rm ~/pekaway/pkwUpdate/flows_pekaway.json
sleep 3
echo "Step 9/${steps}: restarting..." | sudo tee ${Progress}
sleep 5
sudo truncate -s 0 ${Progress}
sudo systemctl restart nodered.service