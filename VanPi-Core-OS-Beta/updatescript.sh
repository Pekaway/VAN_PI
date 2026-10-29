#!/bin/bash
# Update an existing VanPi installation. Run as pi, with passwordless sudo.
# Dashboard entry point: bash updatescript.sh node-red-auto-update
# Keep this file self-contained: the dashboard downloads only this script.

set -Eeuo pipefail
umask 022

Version='b2.1.1'
NSPanelVersion='0.0.1'
TouchdisplayVersion='2.1.0'
Server='https://raw.githubusercontent.com/Pekaway/VAN_PI/main/VanPi-Core-OS-Beta/'
LfsServerFiles='https://media.githubusercontent.com/media/Pekaway/VAN_PI/main/VanPi-Core-OS-Beta/'
PekawayDir="$HOME/pekaway"
NodeRedDir="$HOME/.node-red"
Progress='/var/log/pekaway-update_progress.log'
MIN_KERNEL_VERSION='6.1'
MIN_PYTHON_VERSION='3.11'
currentStep=0
steps=13
AutoUpdate=false
NodeRedWasActive=false
NodeRedStopped=false
UpdateComplete=false
StageDir=''
BackupDir=''
LOG_FILE=''
declare -a ChangedTargets=()
declare -A BackedUp=()
PythonFiles=(
    data/ads_py/simplelevel.py data/ads_py/web2.py data/ds18b20_py/ds18b20.py
    data/ble_py/bleMppt.py data/ble_py/bleRuuvi.py data/ble_py/bleShunt.py
    data/ble_py/pu_ble_mqtt.py data/ble_py/jbd_bms_reader2.py
    data/mpu_py/mpuAngle.py data/bmi270_project/bmiAngle.py)

die() { echo "Error: $*" >&2; exit 1; }
warn() { echo "Warning: $*" >&2; }

show_progress() {
    currentStep=$((currentStep + 1))
    printf 'Step %s/%s: %s\n' "$currentStep" "$steps" "$1" | sudo -n tee "$Progress"
}

normalize_version() {
    local value=${1//$'\r'/}
    if [[ $value =~ ^[bv]?([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        printf '%d.%d.%d\n' "$((10#${BASH_REMATCH[1]}))" \
            "$((10#${BASH_REMATCH[2]}))" "$((10#${BASH_REMATCH[3]}))"
    else
        return 1
    fi
}

version_greater_equal() {
    [[ $(printf '%s\n' "$1" "$2" | sort -V | head -n 1) == "$2" ]]
}

confirm() {
    local answer
    [[ -t 0 ]] || die 'Confirmation requires a terminal; use node-red-auto-update for dashboard updates.'
    while read -r -p "$1 [y/n] " answer; do
        case "$answer" in
            [yY]|[yY][eE][sS]) return 0 ;;
            [nN]|[nN][oO]) return 1 ;;
        esac
    done
    return 1
}

backup_target() {
    local target=$1
    [[ ${BackedUp[$target]:-} ]] && return 0
    if [[ -e $target || -L $target ]]; then
        sudo -n mkdir -p -- "$BackupDir/files$(dirname "$target")"
        sudo -n cp -a -- "$target" "$BackupDir/files$target"
        BackedUp[$target]=existing
    else
        BackedUp[$target]=missing
    fi
    ChangedTargets+=("$target")
}

install_managed() {
    local source=$1 target=$2 mode=${3:-0644} owner=${4:-user}
    local temporary="${target}.vanpi-update.$$"
    backup_target "$target"
    if [[ $owner == root || $owner == firmware ]]; then
        sudo -n mkdir -p -- "$(dirname "$target")"
        if [[ $owner == firmware ]]; then
            # VFAT ownership and mode come from mount options. Copy content only.
            sudo -n cp -- "$source" "$temporary"
        else
            sudo -n install -m "$mode" -- "$source" "$temporary"
        fi
        sudo -n mv -f -- "$temporary" "$target"
    else
        mkdir -p -- "$(dirname "$target")"
        install -m "$mode" -- "$source" "$temporary"
        mv -f -- "$temporary" "$target"
    fi
}

finish() {
    local status=$? target index
    trap - EXIT ERR INT TERM
    set +e
    if (( status != 0 )) && [[ $UpdateComplete != true ]]; then
        echo "Update failed. Restoring managed files from $BackupDir."
        if [[ $NodeRedStopped == true ]]; then
            sudo -n systemctl stop nodered.service || warn 'Could not stop Node-RED before restoring files.'
        fi
        # APT/pip/npm changes are not transactional; keep their full output in the log.
        for ((index=${#ChangedTargets[@]}-1; index>=0; index--)); do
            target=${ChangedTargets[index]}
            sudo -n rm -f -- "${target}.vanpi-update.$$"
            if [[ ${BackedUp[$target]} == existing ]]; then
                if [[ $target == /boot/* ]]; then
                    sudo -n cp -f --no-preserve=all -- "$BackupDir/files$target" "$target" || warn "Restore failed: $target"
                else
                    sudo -n cp -a --remove-destination -- "$BackupDir/files$target" "$target" || warn "Restore failed: $target"
                fi
            else
                sudo -n rm -f -- "$target" || warn "Cleanup failed: $target"
            fi
        done
        sudo -n systemctl daemon-reload
        if [[ $NodeRedStopped == true && $NodeRedWasActive == true ]]; then
            sudo -n systemctl start nodered.service || warn 'Could not restart the previous Node-RED installation.'
        fi
        sudo -n nginx -t && sudo -n systemctl reload nginx
        sudo -n udevadm control --reload-rules
        printf 'Error: update failed; see %s\n' "$LOG_FILE" | sudo -n tee "$Progress"
        echo 'Package changes may require repair; the OS version has not been advanced.'
    fi
    if [[ -n $StageDir && $StageDir == "$PekawayDir"/.update-* && -d $StageDir ]]; then
        rm -rf -- "$StageDir"
    fi
    exit "$status"
}

download_file() {
    local relative=$1 kind=${2:-raw} destination="$StageDir/$1" base=$Server attempt
    [[ $kind == lfs ]] && base=$LfsServerFiles
    mkdir -p -- "$(dirname "$destination")"
    for attempt in {1..5}; do
        echo "Downloading $relative (attempt $attempt/5)"
        if wget --quiet --timeout=60 --tries=1 -O "$destination.part" "${base}${relative}" \
            && [[ -s $destination.part ]] \
            && ! head -c 512 "$destination.part" | grep -aqE 'git-lfs.github.com/spec/v1|<!DOCTYPE html|<html'; then
            mv -f -- "$destination.part" "$destination"
            return 0
        fi
        rm -f -- "$destination.part"
        sleep 3
    done
    die "Download failed or returned a pointer/error page: $relative"
}

validate_downloads() {
    python3 - "$StageDir" "$TouchdisplayVersion" <<'PY'
import ast
import json
import pathlib
import sqlite3
import sys

root = pathlib.Path(sys.argv[1])
for path in root.rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
for name in ('node-red/package.json', 'node-red/flows_pekaway.json'):
    with (root / name).open(encoding='utf-8-sig') as handle:
        value = json.load(handle)
    if name.endswith('package.json'):
        if not isinstance(value, dict) or not isinstance(value.get('dependencies'), dict):
            raise SystemExit('Downloaded package.json has no dependencies object')
    else:
        if not isinstance(value, list) or not value:
            raise SystemExit('Downloaded flows must be a non-empty array')
        ids = [node.get('id') for node in value if isinstance(node, dict)]
        if len(ids) != len(value) or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
            raise SystemExit('Downloaded flows contain invalid or duplicate IDs')
for name in (f'touchdisplay/PekawayTouch{sys.argv[2]}.tft',
             f'touchdisplay/PekawayTouch{sys.argv[2]}_180.tft',
             'data/userdata/NSPanel/VanPI_NSPANEL.tft'):
    if (root / name).stat().st_size < 1024:
        raise SystemExit(f'Firmware download is suspiciously small: {name}')
for name in ('data/bmi270_project/bmi270_demo', 'data/ci2mqtt/ci_mqtt_bridge'):
    with (root / name).open('rb') as handle:
        if handle.read(4) != b'\x7fELF':
            raise SystemExit(f'Invalid executable: {name}')
database = sqlite3.connect((root / 'misc/pythonsqlite.db').absolute().as_uri() + '?mode=ro', uri=True)
if database.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
    raise SystemExit('Downloaded SQLite database failed integrity_check')
database.close()
print('Downloaded Python, JSON, firmware, binaries and database validated.')
PY
}

merge_flows() {
    python3 - "$1" "$2" "$3" <<'PY'
import json
import pathlib
import re
import sys

def load(name):
    nodes = json.loads(pathlib.Path(name).read_text(encoding='utf-8-sig'))
    if not isinstance(nodes, list):
        raise SystemExit(f'Flows are not an array: {name}')
    ids = [n.get('id') for n in nodes if isinstance(n, dict)]
    if len(ids) != len(nodes) or any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise SystemExit(f'Flows contain invalid or duplicate IDs: {name}')
    return nodes

old, new = load(sys.argv[1]), load(sys.argv[2])
old_by_id = {n['id']: n for n in old}
new_by_id = {n['id']: n for n in new}
core_ids = set(new_by_id)
tabs = {n['id'] for n in old if n.get('type') == 'tab' and re.search(r'user\s*flow', n.get('label', ''), re.I)}
selected = {n['id'] for n in old if n['id'] in tabs or n.get('z') in tabs}
connection_types = {'mqtt-broker', 'tls-config', 'serial-port', 'zigbee2mqtt-server'}

def config_node(node):
    return not node.get('z') and node.get('type') != 'tab' and 'x' not in node and 'y' not in node

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)

# Preserve connection configuration, including types which do not end in -config.
selected.update(n['id'] for n in old if config_node(n) and
                (n.get('type') in connection_types or n.get('type', '').endswith('-config')))
pending = list(selected)
while pending:
    ident = pending.pop()
    node = old_by_id[ident]
    refs = list(strings(node))
    kind = node.get('type', '')
    if kind.startswith('subflow:'):
        refs.append(kind[8:])
    for ref in refs:
        if ref in old_by_id and ref not in selected:
            dependency = old_by_id[ref]
            if config_node(dependency) or dependency.get('type') == 'subflow':
                selected.add(ref)
                pending.append(ref)
    if node.get('type') == 'subflow':
        for child in old:
            if child.get('z') == ident and child['id'] not in selected:
                selected.add(child['id'])
                pending.append(child['id'])

for ident in selected:
    saved = old_by_id[ident]
    if ident not in new_by_id:
        new_by_id[ident] = saved
    elif saved.get('type') in connection_types:
        if new_by_id[ident].get('type') != saved.get('type'):
            raise SystemExit(f'Configuration type conflict: {ident}')
        new_by_id[ident] = {**new_by_id[ident], **saved}
    elif saved != new_by_id[ident] and (ident in tabs or saved.get('z') in tabs):
        raise SystemExit(f'User flow ID conflicts with a new core node: {ident}')

# Keep new core ordering; append preserved user nodes in their previous order.
order = [n['id'] for n in new] + [n['id'] for n in old if n['id'] not in core_ids and n['id'] in selected]
result = [new_by_id[ident] for ident in order]
pathlib.Path(sys.argv[3]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Prepared {len(result)} nodes; preserved {len(tabs)} user tabs and their dependencies.')
PY
}

prepare_settings() {
    node - "$1" "$2" <<'JS'
const fs = require('fs');
const vm = require('vm');
const [input, output] = process.argv.slice(2);
let source = fs.readFileSync(input, 'utf8').replace(/\r\n/g, '\n');
new vm.Script(source, { filename: input });
source = source.replace(/\n\/\/ BEGIN VANPI UPDATE SETTINGS\n[\s\S]*?\/\/ END VANPI UPDATE SETTINGS\n?/g, '\n');
// Assign exported properties after the original object. Preserve arbitrary
// user settings, comments and functions without rewriting JavaScript with sed.
source = source.trimEnd() + `

// BEGIN VANPI UPDATE SETTINGS
;(() => {
    const settings = module.exports;
    settings.functionGlobalContext = {
        ...(settings.functionGlobalContext || {}), zlib: require('zlib')
    };
    const stores = settings.contextStorage || {};
    const name = typeof stores.default === 'string' ? stores.default : null;
    const previous = (name ? stores[name] : stores.default) || {};
    const persistent = {
        ...previous, module: 'localfilesystem',
        config: { ...(previous.config || {}), flushInterval: 3600 }
    };
    settings.contextStorage = name
        ? { ...stores, [name]: persistent }
        : { ...stores, default: persistent };
})();
// END VANPI UPDATE SETTINGS
`;
new vm.Script(source, { filename: output });
fs.writeFileSync(output, source, 'utf8');
JS
}

prepare_python_requirements() {
    python3 - "$1" "$2" <<'PY'
import pathlib
import re
import sys

# Supplied by APT (or installer tooling), not rebuilt from PyPI.
system = {'python-apt', 'pygobject', 'pycairo', 'smbus', 'ssh-import-id',
          'pip', 'setuptools', 'wheel', 'rpi-gpio', 'rpi-lgpio'}
result = []
for raw in pathlib.Path(sys.argv[1]).read_text(encoding='utf-8-sig').splitlines():
    line = raw.split('#', 1)[0].strip()
    if not line:
        continue
    match = re.match(r'^([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\s|[<>=!~;\[]|$)', line)
    if not match:
        raise SystemExit(f'Unexpected requirement: {line}')
    name = re.sub(r'[-_.]+', '-', match.group(1)).lower()
    if name not in system and name != 'paho-mqtt':
        result.append(line)
result.append('paho-mqtt>=2,<3')
pathlib.Path(sys.argv[2]).write_text('\n'.join(result) + '\n', encoding='utf-8')
PY
}

install_system_packages() {
    sudo -n env DEBIAN_FRONTEND=noninteractive apt-get update
    # Keep the previous updater's OS upgrade behaviour, preserving local configs.
    sudo -n env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::='--force-confold'
    local -a required=(python3-pip python3-apt python3-gi python3-gi-cairo python3-cairo
        python3-smbus python3-dbus python3-dev python-is-python3 bluez can-utils
        i2c-tools iw jq nginx mosquitto mosquitto-clients)
    if ! python3 -c 'import RPi.GPIO' >/dev/null 2>&1; then
        if grep -aq 'Raspberry Pi 5' /proc/device-tree/model; then
            required+=(python3-rpi-lgpio)
        else
            required+=(python3-rpi.gpio)
        fi
    fi
    sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::='--force-confold' "${required[@]}"

    # packages.txt is an image inventory, not an instruction to reinstall old
    # kernels or foreign-architecture libraries on every Raspberry Pi.
    python3 - "$StageDir/packages.txt" "$StageDir/apt-missing.txt" "$BackupDir/packages-skipped.log" <<'PY'
import apt
import pathlib
import re
import subprocess
import sys

cache = apt.Cache()
architecture = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
installed = set(subprocess.check_output(
    ['dpkg-query', '-W', '-f=${binary:Package}\t${db:Status-Status}\n'], text=True).splitlines())
missing, skipped, seen = [], [], set()
for raw in pathlib.Path(sys.argv[1]).read_text(encoding='utf-8-sig').splitlines():
    package = raw.split('#', 1)[0].strip()
    if not package or package in seen:
        continue
    seen.add(package)
    if not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*(?::[a-z0-9-]+)?', package):
        raise SystemExit(f'Invalid APT package name: {package}')
    base, _, arch = package.partition(':')
    if arch and arch not in (architecture, 'all', 'native'):
        skipped.append(f'{package}: foreign architecture')
    elif re.match(r'^linux-(?:image|headers|kbuild)-[0-9]', base):
        skipped.append(f'{package}: historical kernel; use the kernel metapackage')
    elif f'{package}\tinstalled' in installed or f'{base}\tinstalled' in installed or f'{base}:{architecture}\tinstalled' in installed:
        continue
    elif re.match(r'^libcamera[0-9]', base):
        # Old ABI packages can remain in the repository while requiring an IPA
        # version replaced by a newer camera stack. Let camera applications pull
        # in their matching libraries instead of replaying the image's ABI list.
        skipped.append(f'{package}: historical camera ABI; resolved by camera application dependencies')
    elif package not in cache or cache[package].candidate is None:
        skipped.append(f'{package}: no installation candidate')
    else:
        missing.append(package)
pathlib.Path(sys.argv[2]).write_text('\n'.join(missing) + ('\n' if missing else ''), encoding='utf-8')
pathlib.Path(sys.argv[3]).write_text('\n'.join(skipped) + '\n', encoding='utf-8')
print(f'APT inventory: {len(missing)} missing packages; {len(skipped)} skipped entries.')
for item in skipped:
    print('Skipped:', item)
PY
    local -a missing=()
    mapfile -t missing < "$StageDir/apt-missing.txt"
    if (( ${#missing[@]} > 0 )); then
        sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::='--force-confold' "${missing[@]}"
    fi
    sudo -n apt-get clean
    # Do not autoremove packages during an application update.
}

verify_python_runtime() {
    "$@" - <<'PY'
import importlib
import importlib.metadata
import paho.mqtt.client as mqtt

version = importlib.metadata.version('paho-mqtt')
if version.split('.')[0] != '2':
    raise SystemExit(f'paho-mqtt 2.x required, got {version} from {mqtt.__file__}')
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
for name in ('bleak', 'ruuvitag_sensor.ruuvi', 'smbus2', 'pexpect', 'gi', 'cairo', 'bottle'):
    importlib.import_module(name)
from ruuvitag_sensor.ruuvi import RuuviTagSensor
if not hasattr(RuuviTagSensor, 'get_data_async'):
    raise SystemExit('Installed ruuvitag_sensor does not provide get_data_async')
print(f'Python runtime OK; paho-mqtt {version} from {mqtt.__file__}')
PY
}

install_python_packages() {
    prepare_python_requirements "$StageDir/piplist.txt" "$StageDir/python-requirements.txt"
    # Install in /usr/local, leaving the Debian-owned paho 1.x files intact.
    # paho has no dependencies. Limit --ignore-installed deliberately to it.
    sudo -n -H python3 -m pip install --break-system-packages --ignore-installed --no-deps 'paho-mqtt>=2,<3'
    sudo -n -H python3 -m pip install --break-system-packages --upgrade -r "$StageDir/python-requirements.txt"
    # Update stale user-site packages which otherwise shadow system packages.
    python3 -m pip install --user --break-system-packages --upgrade -r "$StageDir/python-requirements.txt"
    verify_python_runtime sudo -n -H python3
    verify_python_runtime python3
}

prepare_input_defaults() {
    local i file type prepared
    for i in {1..16}; do
        file="$PekawayDir/mcpinput$i"
        prepared="$StageDir/mcpinput$i"
        # Preserve existing mappings and only add absent keys. Invalid non-empty
        # configuration is an error rather than permission to erase user data.
        python3 - "$file" "$prepared" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else {}
if not isinstance(data, dict):
    raise SystemExit(f'Input configuration must be an object: {path}')
data.setdefault('relays', dict.fromkeys(('one','two','three','four','five','six','seven','eight'), False))
data.setdefault('dimmers', {f'd{i}': False for i in range(1, 8)})
pathlib.Path(sys.argv[2]).write_text(json.dumps(data) + '\n')
PY
        install_managed "$prepared" "$file"
        type=''
        if [[ -f ${file}_type ]]; then type=$(tr -d '\r\n' < "${file}_type"); fi
        if [[ $type != switch && $type != button ]]; then
            printf 'button\n' > "$StageDir/input_type"
            install_managed "$StageDir/input_type" "${file}_type"
        fi
    done
    local name value
    for name in combined_temp_chart combined_ruuvi_chart relayboard_core trumaCi dimmyProRgbw1 dimmyProRgbw2; do
        [[ -e $PekawayDir/$name ]] && continue
        case "$name" in
            relayboard_core|trumaCi) value='false' ;;
            dimmyProRgbw1) value='{"isRgbw":true,"name":"Dimmy Pro RGBW 1"}' ;;
            dimmyProRgbw2) value='{"isRgbw":true,"name":"Dimmy Pro RGBW 2"}' ;;
            *) value='' ;;
        esac
        printf '%s\n' "$value" > "$StageDir/default"
        install_managed "$StageDir/default" "$PekawayDir/$name"
    done
}

configure_logs_and_wifi() {
    local file
    for file in /etc/logrotate.conf /etc/log2ram.conf; do
        if [[ ! -f $file ]]; then
            warn "$file is absent; skipping this optional configuration."
            continue
        fi
        python3 - "$file" "$StageDir/log-config" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
source = path.read_text()
key, value, sep = ('maxsize', '60M', ' ') if path.name == 'logrotate.conf' else ('LOG_DISK_SIZE', '256M', '=')
pattern = rf'(?m)^[ \t]*{key}[ \t]*{re.escape(sep)}.*$'
line = f'{key}{sep}{value}'
source = re.sub(pattern, lambda _: line, source) if re.search(pattern, source) else source.rstrip() + '\n' + line + '\n'
pathlib.Path(sys.argv[2]).write_text(source)
PY
        install_managed "$StageDir/log-config" "$file" 0644 root
    done
    if [[ -f /proc/device-tree/model ]] && grep -aq '^Raspberry' /proc/device-tree/model \
        && [[ -d /sys/class/net/wlan0 ]]; then
        file=/etc/systemd/system/wifi-powersave-off.service
        if [[ ! -e $file ]]; then
            cat > "$StageDir/wifi-powersave-off.service" <<'UNIT'
[Unit]
Description=Disable WiFi Power Save Mode
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/sbin/iw dev wlan0 set power_save off
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT
            sed -i "s|/usr/sbin/iw|$(command -v iw)|" "$StageDir/wifi-powersave-off.service"
            install_managed "$StageDir/wifi-powersave-off.service" "$file" 0644 root
        fi
        sudo -n systemctl daemon-reload
        sudo -n systemctl enable wifi-powersave-off.service
        sudo -n systemctl start wifi-powersave-off.service || warn 'Could not disable WiFi power saving now; service is enabled for boot.'
    else
        echo 'Skipping WiFi power-save service: no Raspberry Pi wlan0 interface.'
    fi
    echo 'log2ram size changes take effect at the next reboot.'
}

install_payload() {
    local relative destination mode old
    for relative in "${PythonFiles[@]}" data/bmi270_project/bmi270_demo data/ci2mqtt/ci_mqtt_bridge; do
        destination="$PekawayDir/${relative#data/}"
        mode=0644
        [[ $relative != *.py ]] && mode=0755
        install_managed "$StageDir/$relative" "$destination" "$mode"
    done
    # Configuration and state defaults are created only when missing.
    [[ -e $PekawayDir/ci2mqtt/.env ]] || install_managed "$StageDir/data/ci2mqtt/.env" "$PekawayDir/ci2mqtt/.env" 0600
    [[ -e $PekawayDir/pythonsqlite.db ]] || install_managed "$StageDir/misc/pythonsqlite.db" "$PekawayDir/pythonsqlite.db"
    [[ -e /boot/firmware/config.txt ]] || install_managed "$StageDir/misc/boot_config.txt" /boot/firmware/config.txt 0644 firmware
    install_managed "$StageDir/misc/98-pekaway-tty.rules" /etc/udev/rules.d/98-pekaway-tty.rules 0644 root
    install_managed "$StageDir/nginx/pekaway1" /etc/nginx/sites-available/pekaway1 0644 root
    destination=/etc/nginx/sites-enabled/pekaway1
    backup_target "$destination"
    sudo -n ln -sfn /etc/nginx/sites-available/pekaway1 "$destination"

    local normal="PekawayTouch${TouchdisplayVersion}.tft" rotated="PekawayTouch${TouchdisplayVersion}_180.tft"
    local required_kb available_kb
    required_kb=$(du -ck "$StageDir/touchdisplay/$normal" "$StageDir/touchdisplay/$rotated" | tail -n 1 | awk '{print $1}')
    available_kb=$(df -Pk /boot/firmware | awk 'NR==2 {print $4}')
    (( available_kb > required_kb + 1024 )) || die 'Insufficient space in /boot/firmware for both display files.'
    install_managed "$StageDir/touchdisplay/$normal" "/boot/firmware/$normal" 0644 firmware
    install_managed "$StageDir/touchdisplay/$rotated" "/boot/firmware/$rotated" 0644 firmware
    # Only remove obsolete Pekaway firmware after BOTH replacements succeeded.
    for old in /boot/PekawayTouch*.tft /boot/firmware/PekawayTouch*.tft; do
        [[ -e $old ]] || continue
        [[ $old == "/boot/firmware/$normal" || $old == "/boot/firmware/$rotated" ]] && continue
        backup_target "$old"
        sudo -n rm -f -- "$old"
    done
    install_managed "$StageDir/data/userdata/NSPanel/VanPI_NSPANEL.tft" "$PekawayDir/VanPI_NSPANEL.tft"
    install_managed "$StageDir/data/userdata/NSPanel/VanPI_NSPANEL.tft" "$PekawayDir/userdata/NSPanel/VanPI_NSPANEL${NSPanelVersion}.tft"
    install_managed "$StageDir/data/userdata/NSPanel/autoexec.be" "$PekawayDir/autoexec.be"
    install_managed "$StageDir/data/userdata/NSPanel/autoexec.be" "$PekawayDir/userdata/NSPanel/autoexec.be"
}

launch_dashboard_worker() {
    # A child of nodered.service would be killed when that service is stopped.
    # Start a separate systemd unit, with a stable snapshot of this script.
    sudo -n true || die 'Dashboard updates require passwordless sudo.'
    command -v systemd-run >/dev/null || die 'systemd-run is required for dashboard updates.'
    local snapshot unit
    mkdir -p "$PekawayDir/nrbackups"
    snapshot=$(mktemp "$PekawayDir/nrbackups/updatescript-${Version}-XXXXXX.sh")
    cp -- "${BASH_SOURCE[0]}" "$snapshot"
    chmod 0700 "$snapshot"
    unit="pekaway-update-$(date +%Y%m%d%H%M%S)-$$"
    sudo -n systemd-run --quiet --collect --unit="$unit" \
        --uid="$(id -u)" --gid="$(id -g)" --working-directory="$HOME" \
        --setenv="HOME=$HOME" --setenv="USER=$(id -un)" \
        --setenv='PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' \
        /bin/bash "$snapshot" node-red-auto-update --worker
    echo "Update started as $unit; progress: $Progress"
}

main() {
    (( EUID != 0 )) || die 'Run as pi with sudo permissions, not as root or with sudo bash.'
    case "${1:-}" in
        node-red-auto-update)
            AutoUpdate=true
            if [[ ${2:-} != --worker ]]; then launch_dashboard_worker; return; fi
            ;;
        '') ;;
        *) die "Unknown argument: $1" ;;
    esac
    sudo -n true || die 'Passwordless sudo is required for this updater.'
    local command
    for command in python3 node npm wget flock dpkg; do
        command -v "$command" >/dev/null || die "Required command not found: $command"
    done
    [[ -d $PekawayDir && -d $NodeRedDir && -d /boot/firmware ]] || die 'Existing VanPi installation and /boot/firmware are required.'
    [[ -f $NodeRedDir/settings.js && -f $NodeRedDir/flows_pekaway.json && -f $NodeRedDir/package.json ]] || die 'Node-RED settings, flows or package.json are missing.'
    exec 9> "$PekawayDir/.update.lock"
    flock -n 9 || die 'Another VanPi update is already running.'

    local os_major os_id kernel python_version current_version normalized_current normalized_target
    # shellcheck source=/dev/null
    os_id=$(. /etc/os-release; printf '%s' "$ID")
    [[ $os_id == debian || $os_id == raspbian ]] || die 'Debian/Raspberry Pi OS is required.'
    # shellcheck source=/dev/null
    os_major=$(. /etc/os-release; printf '%s' "${VERSION_ID%%.*}")
    if [[ ! $os_major =~ ^[0-9]+$ ]] || (( os_major < 12 )); then
        die 'Debian/Raspberry Pi OS 12 or newer is required.'
    fi
    kernel=$(uname -r); kernel=${kernel%%-*}
    python_version=$(python3 -c 'import platform; print(platform.python_version())')
    version_greater_equal "$kernel" "$MIN_KERNEL_VERSION" || die "Kernel $MIN_KERNEL_VERSION or newer required."
    version_greater_equal "$python_version" "$MIN_PYTHON_VERSION" || die "Python $MIN_PYTHON_VERSION or newer required."
    current_version=$(cat "$PekawayDir/version" 2>/dev/null || true)
    normalized_target=$(normalize_version "$Version")
    if normalized_current=$(normalize_version "$current_version"); then
        echo "Current version: $current_version; update target: $Version"
        if [[ $AutoUpdate != true ]] && version_greater_equal "$normalized_current" "$normalized_target"; then
            confirm "Install $Version over $current_version?" || return 0
        fi
    else
        echo "No valid current version found; preparing installation of $Version."
    fi

    mkdir -p "$PekawayDir/nrbackups" "$PekawayDir/pkwUpdate"
    BackupDir=$(mktemp -d "$PekawayDir/nrbackups/update-${Version}-$(date +%Y%m%d-%H%M%S)-XXXXXX")
    chmod 0700 "$BackupDir"
    StageDir=$(mktemp -d "$PekawayDir/.update-XXXXXX")
    LOG_FILE="/var/log/pekaway-update_$(date +%Y_%m_%d-%H_%M_%S).log"
    sudo -n touch "$LOG_FILE" "$Progress"
    sudo -n chown "$(id -u):$(id -g)" "$LOG_FILE"
    sudo -n chmod 0644 "$LOG_FILE" "$Progress"
    exec > >(tee -a "$LOG_FILE") 2>&1
    trap 'echo "Update failed at line $LINENO (exit $?)." >&2' ERR
    trap finish EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    printf 'PID=%s\n' "$$" | sudo -n tee "$Progress"
    # Give the existing dashboard file watcher time to read the PID-only entry.
    sleep 7
    echo "Log: $LOG_FILE; file backups: $BackupDir"
    echo 'Existing boot config, SQLite data and CI-bridge settings will be preserved.'

    show_progress 'downloading and validating update files'
    local relative
    for relative in packages.txt piplist.txt "${PythonFiles[@]}" \
        data/bmi270_project/bmi270_demo data/ci2mqtt/ci_mqtt_bridge data/ci2mqtt/.env \
        data/userdata/NSPanel/autoexec.be misc/boot_config.txt misc/98-pekaway-tty.rules \
        misc/pythonsqlite.db nginx/pekaway1; do
        download_file "$relative"
    done
    for relative in node-red/package.json node-red/flows_pekaway.json \
        data/userdata/NSPanel/VanPI_NSPANEL.tft \
        "touchdisplay/PekawayTouch${TouchdisplayVersion}.tft" \
        "touchdisplay/PekawayTouch${TouchdisplayVersion}_180.tft"; do
        download_file "$relative" lfs
    done
    validate_downloads

    show_progress 'checking Node-RED settings and package changes'
    prepare_settings "$NodeRedDir/settings.js" "$StageDir/settings.js"
    node --check "$StageDir/settings.js"
    python3 - "$NodeRedDir/package.json" "$StageDir/node-red/package.json" "$StageDir/package.json" <<'PY'
import json
import pathlib
import sys

old, new = [json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig')) for p in sys.argv[1:3]]
dependencies = old.get('dependencies', {})
if not isinstance(dependencies, dict):
    raise SystemExit('Existing package.json dependencies must be an object')
extra = sorted(set(dependencies) - set(new['dependencies']))
new['dependencies'] = {**dependencies, **new['dependencies']}
pathlib.Path(sys.argv[3]).write_text(json.dumps(new, indent=2) + '\n')
print('Preserving additional user modules:', ', '.join(extra) or '(none)')
PY
    # Validate before stopping services; recompute after stopping Node-RED so
    # a last-second deploy is included in the actual installation.
    merge_flows "$NodeRedDir/flows_pekaway.json" "$StageDir/node-red/flows_pekaway.json" "$StageDir/flows_pekaway.json"

    show_progress 'backing up and stopping Node-RED'
    if sudo -n systemctl is-active --quiet nodered.service; then NodeRedWasActive=true; fi
    backup_target "$NodeRedDir/settings.js"
    backup_target "$NodeRedDir/package.json"
    backup_target "$NodeRedDir/package-lock.json"
    [[ ! -e $NodeRedDir/flows_pekaway_cred.json ]] || cp -p "$NodeRedDir/flows_pekaway_cred.json" "$BackupDir/flows_pekaway_cred.json"
    NodeRedStopped=true
    sudo -n systemctl stop nodered.service
    backup_target "$NodeRedDir/flows_pekaway.json"
    merge_flows "$NodeRedDir/flows_pekaway.json" "$StageDir/node-red/flows_pekaway.json" "$StageDir/flows_pekaway.json"

    show_progress 'installing system packages'
    install_system_packages

    show_progress 'installing Python packages and verifying MQTT v2'
    install_python_packages

    show_progress 'installing Node-RED modules'
    install_managed "$StageDir/package.json" "$NodeRedDir/package.json"
    (cd "$NodeRedDir" && npm install --no-audit --no-fund)
    (cd "$NodeRedDir" && npm ls --omit=dev --depth=0)

    show_progress 'installing Python scripts and both display firmware files'
    install_payload

    show_progress 'updating input defaults'
    prepare_input_defaults

    show_progress 'configuring log limits and WiFi power saving'
    configure_logs_and_wifi

    show_progress 'installing validated Node-RED settings and merged flows'
    install_managed "$StageDir/settings.js" "$NodeRedDir/settings.js"
    install_managed "$StageDir/flows_pekaway.json" "$NodeRedDir/flows_pekaway.json"

    show_progress 'validating and reloading system services'
    sudo -n nginx -t
    sudo -n systemctl reload nginx
    sudo -n udevadm control --reload-rules
    sudo -n udevadm trigger

    show_progress 'starting Node-RED and checking service state'
    # Node-RED reads these files during startup. They remain part of the rollback
    # until the new service has passed its health check.
    printf '%s\n' "$Version" > "$StageDir/version"
    printf '1\n' > "$StageDir/update"
    install_managed "$StageDir/version" "$PekawayDir/version"
    install_managed "$StageDir/update" "$PekawayDir/update"
    sudo -n systemctl start nodered.service
    sleep 10
    sudo -n systemctl is-active --quiet nodered.service || die 'Node-RED did not remain active after the update.'

    show_progress 'recording successful update'
    UpdateComplete=true
    NodeRedStopped=false
    echo "Update to $Version completed. Backups: $BackupDir"
    sudo -n truncate -s 0 "$Progress"
    if [[ $AutoUpdate == true ]]; then
        echo 'Rebooting automatically after dashboard update.'
        sudo -n systemctl reboot || warn 'Update succeeded, but automatic reboot failed. Reboot manually.'
    elif [[ -t 0 ]] && confirm 'Update complete. Reboot now?'; then
        sudo -n systemctl reboot || warn 'Update succeeded, but reboot failed. Reboot manually.'
    else
        echo 'Node-RED is running. Reboot later to apply all system changes.'
    fi
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
