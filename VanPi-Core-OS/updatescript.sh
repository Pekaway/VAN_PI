#!/bin/bash
# Update an existing VanPi installation. Run as pi, with passwordless sudo.
# Dashboard entry point: bash updatescript.sh node-red-auto-update
# Keep this file self-contained: the dashboard downloads only this script.

set -Eeuo pipefail
umask 022

Version='v2.1.2'
NSPanelVersion='0.0.1'
TouchdisplayVersion='2.1.0'
Server='https://raw.githubusercontent.com/Pekaway/VAN_PI/main/VanPi-Core-OS/'
LfsServerFiles='https://media.githubusercontent.com/media/Pekaway/VAN_PI/main/VanPi-Core-OS/'
PekawayDir="$HOME/pekaway"
NodeRedDir="$HOME/.node-red"
Progress='/var/log/pekaway-update_progress.log'
MIN_KERNEL_VERSION='6.1'
MIN_PYTHON_VERSION='3.11'
MIN_LOG_FREE_KIB=16384
NODE_RED_HEALTH_TIMEOUT=240
# A line containing this marker in /boot/firmware/config.txt disables the
# boot configuration merge; the file is then left exactly as it is.
BOOT_CONFIG_OPT_OUT='VANPI_KEEP_BOOT_CONFIG'
# boot_config.txt settings which are not added to existing installations,
# because they change visible behaviour (CPU clock, HDMI output).
BOOT_CONFIG_SKIP='arm_freq arm_freq_min hdmi_blanking'
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
declare -a PackageFailures=()
declare -A BackedUp=()
PythonFiles=(
    data/ads_py/simplelevel.py data/ads_py/web2.py data/ds18b20_py/ds18b20.py
    data/ble_py/bleMppt.py data/ble_py/bleRuuvi.py data/ble_py/bleShunt.py
    data/ble_py/pu_ble_mqtt.py data/ble_py/jbd_bms_reader2.py
    data/mpu_py/mpuAngle.py data/bmi270_project/bmiAngle.py)

die() { echo "Error: $*" >&2; exit 1; }
warn() { echo "Warning: $*" >&2; }

record_package_failure() {
    local message=$1
    PackageFailures+=("$message")
    if ! printf '%s\n' "$message" >> "$BackupDir/package-failures.log"; then
        warn 'Could not write the package warnings file; keeping warnings in memory.'
    fi
    warn "$message; the update will continue."
}

report_package_failures() {
    local line
    if (( ${#PackageFailures[@]} > 0 )); then
        echo 'Package installation and runtime warnings:'
        for line in "${PackageFailures[@]}"; do
            printf '  - %s\n' "$line"
        done
        echo "Warning file, if writable: $BackupDir/package-failures.log; full output: $LOG_FILE"
    fi
}

write_progress() {
    local message=$1 fallback="$BackupDir/update-progress.log"
    if printf '%s\n' "$message" | sudo -n tee "$Progress"; then
        return 0
    fi
    if [[ $Progress == "$fallback" ]]; then
        warn "Could not write progress to $fallback; continuing without a progress file."
        return 0
    fi
    warn "Could not write progress to $Progress; using $fallback. Dashboard progress may be unavailable."
    Progress=$fallback
    if ! printf '%s\n' "$message" | sudo -n tee "$Progress"; then
        warn "Could not write progress to $fallback; continuing without a progress file."
    fi
    return 0
}

show_progress() {
    currentStep=$((currentStep + 1))
    write_progress "Step $currentStep/$steps: $1"
}

log_free_kib() {
    LC_ALL=C df -Pk -- "$1" | awk 'NR == 2 {print $4}'
}

prepare_log_storage() {
    local log_dir=$1 free file relative destination log_dev backup_dev
    echo "Preparing log storage at $log_dir before starting the update."
    # Vacuum archived journals only; never truncate active binary journal files.
    if command -v journalctl >/dev/null 2>&1; then
        sudo -n journalctl --vacuum-size=32M || warn 'Could not vacuum archived journals.'
        # Even on a full filesystem, rotation may succeed and make the former
        # active journal eligible for vacuuming. Failure is non-fatal.
        sudo -n journalctl --rotate || warn 'Could not rotate the journal.'
        sudo -n journalctl --vacuum-size=32M || warn 'Could not vacuum rotated journals.'
    fi
    free=$(log_free_kib "$log_dir") || free=0
    [[ $free =~ ^[0-9]+$ ]] || free=0
    if (( free < MIN_LOG_FREE_KIB )); then
        echo "Log filesystem has ${free} KiB free; looking for large text logs to preserve and clear."
        log_dev=$(stat -c %d -- "$log_dir") || log_dev=''
        backup_dev=$(stat -c %d -- "$BackupDir") || backup_dev=''
        if [[ -n $log_dev && -n $backup_dev && $log_dev != "$backup_dev" ]]; then
            while IFS= read -r -d '' file; do
                relative=${file#"$log_dir"/}
                destination="$BackupDir/log-recovery/$relative"
                if sudo -n mkdir -p -- "$(dirname "$destination")" && \
                   sudo -n cp -p -- "$file" "$destination" && \
                   sudo -n truncate -s 0 -- "$file"; then
                    echo "Saved and cleared $file (backup: $destination)."
                else
                    warn "Could not preserve and clear $file."
                fi
                free=$(log_free_kib "$log_dir") || free=0
                [[ $free =~ ^[0-9]+$ ]] || free=0
                (( free < MIN_LOG_FREE_KIB )) || break
            done < <(sudo -n find "$log_dir" -xdev -type f -size +1M \
                ! -path "$log_dir/journal/*" \
                \( -name '*.log' -o -name '*.log.1' -o -name 'syslog' -o -name 'syslog.1' \) -print0)
        else
            warn 'Log backup is not on a separate filesystem; skipping text-log clearing.'
        fi
    fi
    free=$(log_free_kib "$log_dir") || free=0
    [[ $free =~ ^[0-9]+$ ]] || free=0
    if (( free >= MIN_LOG_FREE_KIB )); then
        if [[ -x /usr/sbin/logrotate && -f /etc/logrotate.conf ]]; then
            sudo -n /usr/sbin/logrotate -f /etc/logrotate.conf || warn 'Log rotation did not complete; see the maintenance log.'
        else
            warn 'logrotate or its configuration is unavailable.'
        fi
    else
        warn "Log filesystem still has only ${free} KiB free; update logs will also be stored in the backup directory."
    fi
    echo "Log storage preparation finished; $(log_free_kib "$log_dir" || echo unknown) KiB free."
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
        write_progress "Error: update failed; see $LOG_FILE"
        echo 'Package changes may require repair; the OS version has not been advanced.'
        report_package_failures
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
flows = json.loads((root / 'node-red/flows_pekaway.json').read_text(encoding='utf-8-sig'))
if not any(isinstance(node, dict) and node.get('type') == 'http in' and node.get('method') == 'get'
           and str(node.get('url', '')).strip('/') == 'names' and not node.get('disabled') for node in flows):
    raise SystemExit('Downloaded flows lack the GET /names endpoint used for the Node-RED health check')
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
    python3 - "$1" "$2" "$3" "$4" <<'PY'
import hashlib
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
user_ids = {n['id'] for n in old if n['id'] in tabs or n.get('z') in tabs}
selected = set(user_ids)
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

def references(node):
    yield from strings(node)
    kind = node.get('type', '')
    if kind.startswith('subflow:'):
        yield kind[8:]

# Preserve connection configuration, including types which do not end in -config.
selected.update(n['id'] for n in old if config_node(n) and
                (n.get('type') in connection_types or n.get('type', '').endswith('-config')))
pending = list(selected)
while pending:
    ident = pending.pop()
    node = old_by_id[ident]
    for ref in references(node):
        if ref in old_by_id and ref not in selected:
            dependency = old_by_id[ref]
            if dependency.get('type') == 'subflow':
                user_ids.add(ref)
            if config_node(dependency) or ref in user_ids:
                selected.add(ref)
                pending.append(ref)
    if node.get('type') == 'subflow':
        for child in old:
            if child.get('z') == ident and child['id'] not in selected:
                user_ids.add(child['id'])
                selected.add(child['id'])
                pending.append(child['id'])

# A node copied verbatim also needs a new ID when a reference changes,
# for example when its parent user tab gets a new ID.
shared_ids = user_ids & core_ids
conflicts = {ident for ident in shared_ids if old_by_id[ident] != new_by_id[ident]}
if conflicts:
    dependents = {}
    for ident in shared_ids - conflicts:
        for ref in references(old_by_id[ident]):
            if ref in shared_ids and ref != ident:
                dependents.setdefault(ref, set()).add(ident)
    pending = list(conflicts)
    while pending:
        added = dependents.get(pending.pop(), set()) - conflicts
        conflicts.update(added)
        pending.extend(added)

user_ids_remapped = {}
occupied = core_ids | old_by_id.keys()
for ident in sorted(conflicts):
    attempt = 0
    while True:
        alias = hashlib.sha256(f'vanpi-user-flow:{ident}:{attempt}'.encode()).hexdigest()[:16]
        if alias not in occupied:
            break
        attempt += 1
    user_ids_remapped[ident] = alias
    occupied.add(alias)
    print(f'Remapped user flow node {ident} to {alias}.')

def remap_ref(value):
    if isinstance(value, str):
        return user_ids_remapped.get(value, value)
    if isinstance(value, list):
        return [remap_ref(item) for item in value]
    if isinstance(value, dict):
        return {key: remap_ref(item) for key, item in value.items()}
    return value

def remap_node(node):
    if not user_ids_remapped:
        return node
    result = remap_ref(node)
    kind = node.get('type', '')
    if kind.startswith('subflow:'):
        result['type'] = 'subflow:' + remap_ref(kind[8:])
    return result

retained = (selected - core_ids) | conflicts
for ident in sorted(selected):
    saved = old_by_id[ident]
    if ident in retained:
        new_by_id[remap_ref(ident)] = remap_node(saved)
    elif saved.get('type') in connection_types:
        if new_by_id[ident].get('type') != saved.get('type'):
            raise SystemExit(f'Configuration type conflict: {ident}')
        new_by_id[ident] = {**new_by_id[ident], **remap_node(saved)}

if retained:
    # Either side of a Node-RED link can hold the connection. Carry over links
    # involving a retained node while keeping the links shipped with the Core.
    link_partners = {'link in': 'link out', 'link out': 'link in'}
    for old_node in old:
        ident = old_node['id']
        kind = old_node.get('type')
        current_id = remap_ref(ident)
        current = new_by_id.get(current_id, {})
        if kind not in link_partners or current.get('type') != kind:
            continue
        for peer_id in old_node.get('links') or []:
            if ident not in retained and peer_id not in retained:
                continue
            target_id = remap_ref(peer_id)
            peer = new_by_id.get(target_id, {})
            if peer.get('type') != link_partners[kind]:
                continue
            for node, link_id in ((current, target_id), (peer, current_id)):
                links = node.get('links') or []
                if link_id not in links:
                    node['links'] = links + [link_id]

# Keep new core ordering; append preserved user nodes in their previous order.
order = [n['id'] for n in new] + [remap_ref(n['id']) for n in old if n['id'] in retained]
result = [new_by_id[ident] for ident in order]
pathlib.Path(sys.argv[3]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
pathlib.Path(sys.argv[4]).write_text(json.dumps(user_ids_remapped) + '\n', encoding='utf-8')
print(f'Prepared {len(result)} nodes; preserved {len(tabs)} user tabs and their dependencies.')
PY
}

prepare_flow_state() {
    node - "$1" "$2" "$3" <<'JS'
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const [userDir, idMapPath, stage] = process.argv.slice(2);
const readJson = file => JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const ids = readJson(idMapPath);
if (Object.keys(ids).length === 0) process.exit(0);

const settings = require(path.join(userDir, 'settings.js'));
const credentialsFile = path.join(userDir, 'flows_pekaway_cred.json');
const owns = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const mapped = id => owns(ids, id) ? ids[id] : id;
const mapScope = id => mapped(id) === id ? id.split('-').map(mapped).join('-') : mapped(id);

function readCredentials() {
    const stored = readJson(credentialsFile);
    if (!owns(stored, '$')) return { entries: stored };

    // Node-RED local filesystem credentials use an IV prefix and AES-256-CTR.
    // Try the runtime key first, as Node-RED does when migrating to a user key.
    const keyFiles = ['.config.runtime.json', '.config.runtime.json.backup', '.config.json'];
    const secrets = [];
    for (const filename of keyFiles.map(file => path.join(userDir, file))) {
        try {
            secrets.push(readJson(filename)._credentialSecret);
        } catch (error) {
            if (error.code !== 'ENOENT' && !(error instanceof SyntaxError)) throw error;
        }
    }
    secrets.push(settings.credentialSecret);
    const payload = stored.$;
    if (typeof payload === 'string' && /^[0-9a-f]{32}/i.test(payload)) {
        const iv = Buffer.from(payload.slice(0, 32), 'hex');
        for (const secret of new Set(secrets)) {
            if (typeof secret !== 'string') continue;
            const key = crypto.createHash('sha256').update(secret).digest();
            try {
                const decipher = crypto.createDecipheriv('aes-256-ctr', key, iv);
                const decoded = decipher.update(payload.slice(32), 'base64', 'utf8') + decipher.final('utf8');
                const entries = JSON.parse(decoded);
                if (entries && typeof entries === 'object' && !Array.isArray(entries)) return { entries, key };
            } catch {
                // Try the next configured key. Never print credential data.
            }
        }
    }
    throw new Error('Cannot read encrypted Node-RED credentials for the ID migration');
}

function prepareCredentials() {
    if (!fs.existsSync(credentialsFile)) return;
    const { entries, key } = readCredentials();
    const changes = Object.entries(ids).filter(([id]) => owns(entries, id));
    if (changes.length === 0) return;
    for (const [id, replacement] of changes) {
        if (owns(entries, replacement)) throw new Error(`Credentials already exist for replacement ID ${replacement}`);
        entries[replacement] = entries[id];
        delete entries[id];
    }
    let prepared = entries;
    if (key) {
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipheriv('aes-256-ctr', key, iv);
        const data = cipher.update(JSON.stringify(entries), 'utf8', 'base64') + cipher.final('base64');
        prepared = { $: iv.toString('hex') + data };
    }
    fs.writeFileSync(path.join(stage, 'flows_pekaway_cred.json'), JSON.stringify(prepared) + '\n', { mode: 0o600 });
    console.log(`Prepared credentials for ${changes.length} remapped Node-RED IDs.`);
}

function prepareContext() {
    const roots = [path.join(userDir, 'context')];
    for (const store of Object.values(settings.contextStorage || {})) {
        if (typeof store === 'string' || store?.module === 'memory') continue;
        if (store?.module !== 'localfilesystem') {
            console.warn('Context in a custom Node-RED store may need to be migrated separately.');
            continue;
        }
        const config = store.config || {};
        roots.push(path.resolve(path.dirname(userDir), path.join(config.dir || userDir, config.base || 'context')));
    }
    const manifest = [];
    const destinations = new Set();
    const existingRoots = new Set(roots.filter(dir => fs.existsSync(dir)).map(dir => fs.realpathSync(dir)));
    for (const root of existingRoots) {
        for (const scope of fs.readdirSync(root, { withFileTypes: true })) {
            if (!scope.isDirectory() || scope.name === 'global') continue;
            const sourceDir = path.join(root, scope.name);
            const targetDir = path.join(root, mapScope(scope.name));
            for (const file of fs.readdirSync(sourceDir, { withFileTypes: true })) {
                if (!file.isFile() || !file.name.endsWith('.json')) continue;
                const name = file.name === 'flow.json' ? file.name : `${mapScope(file.name.slice(0, -5))}.json`;
                const from = path.join(sourceDir, file.name);
                const to = path.join(targetDir, name);
                if (from === to) continue;
                if (destinations.has(to) || fs.existsSync(to)) throw new Error(`Node-RED context already exists at ${to}`);
                const prepared = path.join(stage, `flow-context-${manifest.length / 3}`);
                fs.copyFileSync(from, prepared);
                manifest.push(prepared, from, to);
                destinations.add(to);
            }
        }
    }
    if (manifest.length) {
        fs.writeFileSync(path.join(stage, 'flow-context-moves'), manifest.join('\0') + '\0');
        console.log(`Prepared ${manifest.length / 3} Node-RED context files for migration.`);
    }
}

try {
    prepareCredentials();
    prepareContext();
} catch (error) {
    console.error(error instanceof SyntaxError ? 'Invalid Node-RED state JSON during ID migration' : error.message);
    process.exitCode = 1;
}
JS
}

install_flow_state() {
    if [[ -f $StageDir/flows_pekaway_cred.json ]]; then
        backup_target "$NodeRedDir/.config.runtime.json"
        backup_target "$NodeRedDir/.config.runtime.json.backup"
        install_managed "$StageDir/flows_pekaway_cred.json" "$NodeRedDir/flows_pekaway_cred.json" 0600
    fi
    if [[ -f $StageDir/flow-context-moves ]]; then
        local prepared source destination
        while IFS= read -r -d '' prepared && IFS= read -r -d '' source && IFS= read -r -d '' destination; do
            backup_target "$source"
            install_managed "$prepared" "$destination" 0600
            rm -f -- "$source"
        done < "$StageDir/flow-context-moves"
    fi
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

merge_boot_config() {
    # Adds settings from boot_config.txt which are missing in the existing
    # config.txt. Existing lines are never changed or removed: a different
    # user value, or a setting the user has commented out, is kept and reported.
    python3 - "$1" "$2" "$3" "$Version" "$BOOT_CONFIG_OPT_OUT" "$BOOT_CONFIG_SKIP" <<'PY'
import pathlib
import re
import sys

current_path, reference_path, output_path, version, opt_out = sys.argv[1:6]
skip = set(sys.argv[6].lower().split())
raw = pathlib.Path(current_path).read_bytes()
current = raw.decode('utf-8', errors='surrogateescape')
reference = pathlib.Path(reference_path).read_text(encoding='utf-8-sig')
newline = '\r\n' if '\r\n' in current else '\n'
# Commented-out examples in the stock Raspberry Pi OS file are not user decisions.
stock_comments = {'dtparam=i2c_arm=on', 'dtparam=i2s=on', 'dtparam=spi=on', 'dtparam=audio=on'}

def normalize(line):
    name, sep, value = line.partition('=')
    return f'{name.strip().lower()}={value.strip()}' if sep else line.strip()

def entries(line):
    name, sep, value = line.partition('=')
    if not sep or not re.fullmatch(r'[A-Za-z0-9_.:-]+', name.strip()):
        return []
    name, value = name.strip().lower(), value.strip()
    if name == 'dtoverlay':
        overlay = value.split(',', 1)[0].strip().lower()
        return [('dtoverlay', overlay)] if overlay else []
    if name == 'dtparam':
        return [('dtparam', part.split('=', 1)[0].strip().lower()) for part in value.split(',') if part.strip()]
    return [('key', name)]

def parse(text):
    section = 'all'
    for line in text.splitlines():
        line = line.strip()
        header = re.fullmatch(r'\[(.+)\]', line)
        if header:
            section = header.group(1).strip().lower()
            continue
        if line:
            yield section, line

if opt_out in current:
    pathlib.Path(output_path).write_bytes(raw)
    print(f'Boot configuration contains {opt_out}; leaving it unchanged.')
    raise SystemExit(0)

active, disabled, exact = {}, {}, set()
for section, line in parse(current):
    if line.startswith('#'):
        content = line.lstrip('#').strip()
        if section == 'all' and normalize(content) in stock_comments:
            continue
        for entry in entries(content):
            disabled.setdefault(entry, set()).add(section)
    else:
        exact.add((section, normalize(line)))
        for entry in entries(line):
            active.setdefault(entry, {}).setdefault(section, line)

def relevant(sections, section):
    # [all] applies to every board; a board section only to that board.
    return set(sections) if section == 'all' else set(sections) & {section, 'all'}

additions, kept = {}, []
for section, line in parse(reference):
    if line.startswith('#') or (section, normalize(line)) in exact:
        continue
    found = entries(line)
    if not found:
        continue
    if any(kind == 'key' and name in skip for kind, name in found):
        if not any(relevant(active.get(entry, {}), section) for entry in found):
            kept.append(f'[{section}] not added automatically: "{line}"')
        continue
    missing = []
    for entry in found:
        where = relevant(active.get(entry, {}), section)
        if where:
            existing = active[entry][sorted(where)[0]]
            if normalize(existing) != normalize(line):
                kept.append(f'[{section}] kept existing "{existing}" (VanPi default: "{line}")')
        elif relevant(disabled.get(entry, set()), section):
            kept.append(f'[{section}] kept disabled by user: "{line}"')
        else:
            missing.append(entry)
    if not missing:
        continue
    if line.split('=', 1)[0].strip().lower() == 'dtparam' and len(missing) < len(found):
        names = {name for _, name in missing}
        line = 'dtparam=' + ','.join(p.strip() for p in line.split('=', 1)[1].split(',')
                                     if p.split('=', 1)[0].strip().lower() in names)
    additions.setdefault(section, []).append(line)

for message in kept:
    print('Boot configuration:', message)
if not additions:
    pathlib.Path(output_path).write_bytes(raw)
    print('Boot configuration already contains all VanPi settings.')
    raise SystemExit(0)

block = ['', f'# BEGIN VanPi {version}: settings added from boot_config.txt']
for section, lines in additions.items():
    block.append(f'[{section}]')
    if lines[0].split('=', 1)[0].strip().lower() == 'dtparam':
        # A dtparam after a dtoverlay belongs to that overlay; an empty
        # dtoverlay= ends the overlay scope so it applies to the base DT.
        block.append('dtoverlay=')
    block.extend(lines)
    print(f'Boot configuration: adding to [{section}]: ' + '; '.join(lines))
if list(additions)[-1] != 'all':
    block.append('[all]')
block += [f'# END VanPi {version}', '']
text = current if current.endswith(('\n', '\r')) or not current else current + newline
pathlib.Path(output_path).write_bytes((text + newline.join(block)).encode('utf-8', errors='surrogateescape'))
PY
}

node_red_health_url() {
    # Derive the HTTP node endpoint from settings.js; fall back to the defaults.
    (cd "$NodeRedDir" && node -e '
const s = require("./settings.js");
const port = Number.parseInt(s.uiPort, 10) || 1880;
let root = typeof s.httpNodeRoot === "string" ? s.httpNodeRoot : (typeof s.httpRoot === "string" ? s.httpRoot : "/");
root = ("/" + root + "/").replace(/\/+/g, "/");
process.stdout.write(`${s.https ? "https" : "http"}://127.0.0.1:${port}${root}names`);
' 2>/dev/null) || printf 'http://127.0.0.1:1880/names'
}

node_red_responds() {
    wget --quiet --no-check-certificate --timeout=5 --tries=1 -O /dev/null "$1"
}

wait_for_node_red() {
    # The service being active is not enough: wait until the flows answer HTTP.
    local url elapsed=0
    url=$(node_red_health_url)
    echo "Waiting up to ${NODE_RED_HEALTH_TIMEOUT}s for Node-RED flows at $url"
    while (( elapsed < NODE_RED_HEALTH_TIMEOUT )); do
        if sudo -n systemctl is-active --quiet nodered.service && node_red_responds "$url"; then
            # Confirm once more to catch a crash directly after the flows started.
            sleep 10
            if sudo -n systemctl is-active --quiet nodered.service && node_red_responds "$url"; then
                echo "Node-RED flows respond after about $((elapsed + 10))s."
                return 0
            fi
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done
    sudo -n journalctl -u nodered.service -n 60 --no-pager || true
    die "Node-RED flows did not respond at $url within ${NODE_RED_HEALTH_TIMEOUT}s."
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

install_apt_packages() {
    local group=$1 package
    shift
    (( $# > 0 )) || return 0
    if sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::='--force-confold' "$@"; then
        return 0
    fi
    warn "APT $group batch failed; retrying packages individually."
    for package in "$@"; do
        if ! sudo -n env DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::='--force-confold' "$package"; then
            record_package_failure "APT $group: $package"
        fi
    done
}

install_system_packages() {
    if ! sudo -n env DEBIAN_FRONTEND=noninteractive apt-get update; then
        record_package_failure 'APT repository refresh failed; package lists may be outdated'
    fi
    # Keep the previous updater's OS upgrade behaviour, preserving local configs.
    if ! sudo -n env DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::='--force-confold'; then
        record_package_failure 'APT upgrade failed; see the full log for affected packages'
    fi
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
    install_apt_packages 'required' "${required[@]}"

    # packages.txt is an image inventory, not an instruction to reinstall old
    # kernels or foreign-architecture libraries on every Raspberry Pi.
    if python3 - "$StageDir/packages.txt" "$StageDir/apt-missing.txt" "$BackupDir/packages-skipped.log" <<'PY'
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
    then
        local -a missing=()
        mapfile -t missing < "$StageDir/apt-missing.txt"
        install_apt_packages 'inventory' "${missing[@]}"
    else
        record_package_failure 'APT inventory could not be evaluated; see the full log'
    fi
    if ! sudo -n apt-get clean; then
        record_package_failure 'APT cache cleanup failed'
    fi
    # Do not autoremove packages during an application update.
}

verify_python_runtime() {
    "$@" - <<'PY'
import importlib
import importlib.metadata
errors = []
try:
    import paho.mqtt.client as mqtt
    version = importlib.metadata.version('paho-mqtt')
    if version.split('.')[0] != '2':
        raise ValueError(f'paho-mqtt 2.x required, got {version} from {mqtt.__file__}')
    mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    print(f'Paho MQTT runtime OK; version {version} from {mqtt.__file__}')
except Exception as exc:
    errors.append(('paho-mqtt>=2,<3', exc))
for name in ('bleak', 'ruuvitag_sensor.ruuvi', 'smbus2', 'pexpect', 'gi', 'cairo', 'bottle'):
    try:
        module = importlib.import_module(name)
        if name == 'ruuvitag_sensor.ruuvi' and not hasattr(module.RuuviTagSensor, 'get_data_async'):
            raise ValueError('RuuviTagSensor does not provide get_data_async')
    except Exception as exc:
        errors.append((name, exc))
if errors:
    for name, exc in errors:
        print(f'PACKAGE WARNING: {name}: {type(exc).__name__}: {exc}')
    raise SystemExit(1)
print('Python runtime OK')
PY
}

check_python_runtime() {
    local scope=$1 line output found=false
    shift
    if output=$(verify_python_runtime "$@" 2>&1); then
        printf '%s\n' "$output"
        return 0
    fi
    printf '%s\n' "$output"
    while IFS= read -r line || [[ -n $line ]]; do
        if [[ $line == 'PACKAGE WARNING: '* ]]; then
            record_package_failure "Python $scope: ${line#PACKAGE WARNING: }"
            found=true
        fi
    done <<< "$output"
    if [[ $found == false ]]; then
        record_package_failure "Python $scope runtime verification failed; see the full log"
    fi
}

install_pip_requirements() {
    local scope=$1 requirement
    local -a command=(python3 -m pip install --break-system-packages --upgrade)
    if [[ $scope == root ]]; then
        command=(sudo -n -H "${command[@]}")
    else
        command+=(--user)
    fi
    if "${command[@]}" -r "$StageDir/python-requirements.txt"; then
        return 0
    fi
    warn "pip $scope batch failed; retrying requirements individually."
    while IFS= read -r requirement || [[ -n $requirement ]]; do
        [[ -n $requirement ]] || continue
        if ! "${command[@]}" "$requirement"; then
            record_package_failure "pip $scope: $requirement"
        fi
    done < "$StageDir/python-requirements.txt"
}

install_python_packages() {
    prepare_python_requirements "$StageDir/piplist.txt" "$StageDir/python-requirements.txt"
    # Install in /usr/local, leaving the Debian-owned paho 1.x files intact.
    # paho has no dependencies. Limit --ignore-installed deliberately to it.
    if ! sudo -n -H python3 -m pip install --break-system-packages --ignore-installed --no-deps 'paho-mqtt>=2,<3'; then
        warn 'Initial Paho MQTT installation failed; the requirements installation and runtime checks will retry it.'
    fi
    install_pip_requirements root
    # Update stale user-site packages which otherwise shadow system packages.
    install_pip_requirements user
    check_python_runtime root sudo -n -H python3
    check_python_runtime user python3
}

install_node_red_modules() {
    install_managed "$StageDir/package.json" "$NodeRedDir/package.json"
    if ! (cd "$NodeRedDir" && npm install --no-audit --no-fund); then
        record_package_failure 'npm install failed; see the full log for affected modules'
    fi
    if ! (cd "$NodeRedDir" && npm ls --omit=dev --depth=0); then
        record_package_failure 'npm dependency verification failed; see the full log for affected modules'
    fi
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
    # $StageDir/config.txt was merged and reported during the checks step.
    if [[ ! -e /boot/firmware/config.txt ]]; then
        install_managed "$StageDir/misc/boot_config.txt" /boot/firmware/config.txt 0644 firmware
    elif ! cmp -s /boot/firmware/config.txt "$StageDir/config.txt"; then
        install_managed "$StageDir/config.txt" /boot/firmware/config.txt 0644 firmware
        echo 'Boot configuration extended; the changes take effect after the reboot.'
    fi
    install_managed "$StageDir/misc/98-pekaway-tty.rules" /etc/udev/rules.d/98-pekaway-tty.rules 0644 root
    install_managed "$StageDir/nginx/pekaway1" /etc/nginx/sites-available/pekaway1 0644 root
    destination=/etc/nginx/sites-enabled/pekaway1
    backup_target "$destination"
    sudo -n ln -sfn /etc/nginx/sites-available/pekaway1 "$destination"

    local normal="PekawayTouch${TouchdisplayVersion}.tft" rotated="PekawayTouch${TouchdisplayVersion}_180.tft"
    local required_kb available_kb
    required_kb=$(du -ck "$StageDir/touchdisplay/$normal" "$StageDir/touchdisplay/$rotated" | tail -n 1 | awk '{print $1}')
    required_kb=$((required_kb + 1024))
    available_kb=$(df -Pk /boot/firmware | awk 'NR==2 {print $4}')
    if (( available_kb <= required_kb )); then
        # Small boot partitions: remove the previous display firmware first.
        # Every removed file is in the backup and is restored on failure.
        echo "Only ${available_kb} KiB free in /boot/firmware (${required_kb} KiB needed); removing previous display firmware first."
        for old in /boot/firmware/PekawayTouch*.tft; do
            [[ -e $old ]] || continue
            backup_target "$old"
            sudo -n rm -f -- "$old"
        done
        available_kb=$(df -Pk /boot/firmware | awk 'NR==2 {print $4}')
        (( available_kb > required_kb )) || \
            die "Insufficient space in /boot/firmware: ${available_kb} KiB free, ${required_kb} KiB required for both display files."
    fi
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
    # Log maintenance, progress and logging are best effort: a full log disk
    # must not itself stop the update. The persistent copy is preferred.
    local var_log_file="/var/log/pekaway-update_$(date +%Y_%m_%d-%H_%M_%S).log" var_log_enabled=false
    local maintenance_log="$BackupDir/log-maintenance.log" persistent_log="$BackupDir/update.log"
    local -a log_destinations=()
    if : > "$maintenance_log"; then
        prepare_log_storage /var/log >> "$maintenance_log" 2>&1 || \
            warn "Log preparation encountered an error; see $maintenance_log."
    else
        warn 'Cannot create the log maintenance file; attempting log preparation without it.'
        prepare_log_storage /var/log || warn 'Log preparation encountered an error.'
    fi
    LOG_FILE='unavailable; see service journal or console'
    if printf 'Initializing update log...\n' >> "$persistent_log"; then
        LOG_FILE=$persistent_log
        log_destinations+=("$persistent_log")
    else
        warn "Cannot write $persistent_log; continuing without this log copy."
    fi
    if ! sudo -n touch "$Progress" || ! sudo -n chmod 0644 "$Progress" || \
       ! printf 'Starting update...\n' | sudo -n tee "$Progress" >/dev/null; then
        warn "Cannot write dashboard progress to $Progress; using the backup directory."
        Progress="$BackupDir/update-progress.log"
    fi
    if sudo -n touch "$var_log_file" && \
       sudo -n chown "$(id -u):$(id -g)" "$var_log_file" && \
       sudo -n chmod 0644 "$var_log_file" && \
       printf 'Initializing update log...\n' >> "$var_log_file"; then
        var_log_enabled=true
        log_destinations+=("$var_log_file")
        if [[ $LOG_FILE != "$persistent_log" ]]; then LOG_FILE=$var_log_file; fi
    else
        warn "Cannot write $var_log_file; continuing without this log copy."
    fi
    # Keep draining the pipe even if every tee output fails, avoiding SIGPIPE.
    exec > >(tee -p -a "${log_destinations[@]}" || cat >/dev/null) 2>&1
    trap 'echo "Update failed at line $LINENO (exit $?)." >&2' ERR
    trap finish EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    if [[ -f $maintenance_log ]]; then
        cat "$maintenance_log" || warn "Cannot read $maintenance_log."
    fi
    write_progress "PID=$$"
    # Give the existing dashboard file watcher time to read the PID-only entry.
    sleep 7
    echo "Log: $LOG_FILE; file backups: $BackupDir"
    if [[ $var_log_enabled == true && $LOG_FILE != "$var_log_file" ]]; then
        echo "Additional log copy: $var_log_file"
    fi
    echo 'Existing SQLite data and CI-bridge settings will be preserved.'
    echo 'The boot config only receives missing VanPi settings; existing lines are kept.'

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

    show_progress 'checking boot, Node-RED settings and package changes'
    if [[ -e /boot/firmware/config.txt ]]; then
        merge_boot_config /boot/firmware/config.txt "$StageDir/misc/boot_config.txt" "$StageDir/config.txt"
    fi
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
    merge_flows "$NodeRedDir/flows_pekaway.json" "$StageDir/node-red/flows_pekaway.json" \
        "$StageDir/flows_pekaway.json" "$StageDir/flow-id-map.json"

    show_progress 'backing up and stopping Node-RED'
    if sudo -n systemctl is-active --quiet nodered.service; then NodeRedWasActive=true; fi
    backup_target "$NodeRedDir/settings.js"
    backup_target "$NodeRedDir/package.json"
    backup_target "$NodeRedDir/package-lock.json"
    [[ ! -e $NodeRedDir/flows_pekaway_cred.json ]] || cp -p "$NodeRedDir/flows_pekaway_cred.json" "$BackupDir/flows_pekaway_cred.json"
    NodeRedStopped=true
    sudo -n systemctl stop nodered.service
    backup_target "$NodeRedDir/flows_pekaway.json"
    merge_flows "$NodeRedDir/flows_pekaway.json" "$StageDir/node-red/flows_pekaway.json" \
        "$StageDir/flows_pekaway.json" "$StageDir/flow-id-map.json"
    prepare_flow_state "$NodeRedDir" "$StageDir/flow-id-map.json" "$StageDir"

    show_progress 'installing system packages'
    install_system_packages

    show_progress 'installing Python packages and verifying MQTT v2'
    install_python_packages

    show_progress 'installing Node-RED modules'
    install_node_red_modules

    show_progress 'installing Python scripts and both display firmware files'
    install_payload

    show_progress 'updating input defaults'
    prepare_input_defaults

    show_progress 'configuring log limits and WiFi power saving'
    configure_logs_and_wifi

    show_progress 'installing validated Node-RED settings and merged flows'
    install_managed "$StageDir/settings.js" "$NodeRedDir/settings.js"
    install_flow_state
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
    wait_for_node_red

    show_progress 'recording successful update'
    report_package_failures
    UpdateComplete=true
    NodeRedStopped=false
    echo "Update to $Version completed. Backups: $BackupDir"
    if (( ${#PackageFailures[@]} > 0 )); then
        local warning_summary
        warning_summary=$(
            echo 'Update completed with package warnings:'
            printf '%s\n' "${PackageFailures[@]}"
            printf 'Warning file, if writable: %s; full log: %s\n' "$BackupDir/package-failures.log" "$LOG_FILE"
        )
        write_progress "$warning_summary"
    else
        sudo -n truncate -s 0 "$Progress" || warn "Could not clear progress at $Progress."
    fi
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
