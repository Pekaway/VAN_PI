#!/bin/bash

########################################################
#														
# This script will update your existing VanPi OS 		
# to the latest release from the Pekaway VanPi server!	
# Simply download the script to your VanPi OS and		
# execute it.											
#														
########################################################

# create logfile and make it writable
LOG_FILE=/var/log/pekaway-update.log
sudo touch ${LOG_FILE}
sudo chmod 0666 ${LOG_FILE}

exec 3<&1
coproc mytee { tee ${LOG_FILE} >&3;  }
exec >&${mytee[1]} 2>&1

# define variables
Server='https://git.pekaway.de/Vincent/vanpi/-/raw/main/pi4/'
Version='v1.1.1'		### <--- set new version number VanPi OS
NSPanelVersion='0.0.1'	### <--- set new version number NSPanel
currentVersion=`cat ~/pekaway/version`

# prepare variables to be compared
VersionToCheck='v1.1.1' # Version that has relevant changes in update script
# (if current version number is below that number than this script will execute without the need for confirmation)
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
if [[ "$1" == "node-red-auto-update" ]] || [[ "$needUpdate" == "true" ]]; then
	echo -e "proceeding..."
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

# remove packages.txt and package.json if they already exist
cd ~/pekaway
rm -f updatescript.sh
rm -f packages.txt
rm -f package.json
rm -f pip3list.txt
rm -f VanPI_NSPANEL.tft
rm -f autoexec.be

# download new files packages.txt and package.json
echo "downloading new files"
wget ${Server}packages.txt
wget ${Server}package.json
wget ${Server}pip3list.txt
wget ${Server}NSPanel/VanPI_NSPANEL.tft
wget ${Server}NSPanel/autoexec.be

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

extramodules=$(diff <(jq --sort-keys .dependencies ~/.node-red/package.json) <(jq --sort-keys .dependencies ~/pekaway/nrbackups/package-backup.json) | grep '>')

if [[ -n $extramodules ]]; then
    echo -e "Your original package.json file has the following additonal modules listed:"
	echo -e "$extramodules"

   if [[ "$1" == "node-red-auto-update" ]] || [[ "$needUpdate" == "true" ]]; then
	echo -e "adding additional lines in package.json automatically."
		# cd ~/.node-red
		echo `jq -s '.[0] * .[1]' ~/.node-red/package.json ~/pekaway/nrbackups/package-backup.json` > ~/pekaway/nrbackups/package1.json && jq . ~/pekaway/nrbackups/package1.json > ~/pekaway/nrbackups/pretty.json && rm ~/pekaway/nrbackups/package1.json && mv ~/pekaway/nrbackups/pretty.json ~/pekaway/nrbackups/package1.json
		echo "Missing lines have been added to package.json"
		echo "New package.json:"
		cat ~/.node-red/package.json
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
echo "installing npm modules, please stand by..."
npm install
echo "done"

cd ~/pekaway
# Install/update python modules locally (user pi) and globally (root)
echo "installing python modules, please stand by..."
sudo pip3 install -r ~/pekaway/pip3list.txt
sudo pip3 install bottle
pip3 install -r ~/pekaway/pip3list.txt
pip3 install bottle
echo "done"

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
echo "replacing local flows.json file with new one from the server"
curl ${Server}flows.json > ~/pekaway/pkwUpdate/flows_pekaway.json 
cp ~/pekaway/pkwUpdate/flows_pekaway.json ~/.node-red/flows_pekaway.json
echo "update script finished! You can find the logfile at ${LOG_FILE}."
rm ~/pekaway/pkwUpdate/flows_pekaway.json
sudo systemctl restart nodered.service
