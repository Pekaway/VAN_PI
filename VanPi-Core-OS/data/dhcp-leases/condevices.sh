#!/bin/bash
# Display basic information about clients connected to our AP
# Requires ieee-data among other packages
DEBUG=1
ME="wapreport"
LOGGER="/usr/bin/logger"
#LOGGEROPTS="-t $ME -i --"   # Logs to syslog
LOGGEROPTS="-t $ME -i -s --" # Mirrors to stdout

# The wireless interface to query and bridge we can arp against
WAP_IFACE=$1
ARP_IFACE='br0'
[ "$WAP_IFACE" == "" ] && $LOGGER $LOGGEROPTS "This script takes a wifi interface name as argument. Exit" && exit

# Survey
DATA=$(/usr/bin/sudo /usr/sbin/hostapd_cli -i ${WAP_IFACE} all_sta);
ARPTABLE=$(/usr/sbin/arp -i ${ARP_IFACE});

# Get the number of clients and connected time
mapfile -t STAS < <(/bin/echo "${DATA}" | /bin/grep -o -E '^([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}' )
COUNT=${#STAS[@]}
mapfile -t CONNTIMES < <(/bin/echo "${DATA}" | /bin/grep -o -P '(?<=connected_time=).*')
# Try to identify clients
IDS=()
OUIS=();
for STA in "${STAS[@]}"
do
    IDS+=( $(/bin/echo "${ARPTABLE}" | /bin/grep -o -P ".*(?=\s+ether\s+${STA})") )
    OUI_b16=${STA//:/}
    MAKE=$(/bin/grep -i "${OUI_b16:0:6}" /var/lib/ieee-data/oui.txt | cut -d$'\t' -f3 | sed -z -E 's/\r|\n//g')
    [[ "${MAKE}" == "" ]] && MAKE="Unknown"
    OUIS+=("${MAKE}")
done
# Now we return our count and lists
echo devices connected on wlan0: $COUNT
for (( i=0; i<${COUNT}; i++)); do
    echo "${STAS[$i]} | ${IDS[$i]} | ${OUIS[$i]} | ${CONNTIMES[$i]} Seconds"
done
exit