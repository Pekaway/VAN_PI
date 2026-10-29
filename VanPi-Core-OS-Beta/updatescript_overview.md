# VanPi OS Update Script Overview

This document outlines the structure and purpose of the VanPi OS update script. It provides a clear overview of what the script does, step by step, to help developers and users understand the upgrade process without reading the entire script.

## Version Management and Initialization
- Before creating the update log in `/var/log`, attempts journal rotation and vacuums archived journals, then runs logrotate when there is sufficient free space. Under low space it copies large text logs to the update backup on a separate filesystem before clearing them; active binary journals are never truncated.
- Keeps the full update log in the backup directory as well as `/var/log` when possible. If dashboard progress cannot be written to `/var/log`, it uses `update-progress.log` in the backup directory instead. Log and progress write failures do not stop the update; the dashboard or file logs may then be unavailable.
- Compares current OS version (`~/pekaway/version`) with the update target version.
- Creates a progress log at `/var/log/pekaway-update_progress.log` for Node-RED dashboard integration.
- Validates system compatibility by checking:
  - Debian codename (requires "bookworm" or newer).
  - Kernel version (requires 6.1 or newer).
  - Python version (validated against minimum requirement).
- If the version file is missing or incorrectly formatted, the script continues without interruption and assumes an update is needed.

## File Downloads and Cleanup
- Prepares the system for update by removing temporary and outdated files.
- Uses robust download logic with retry (up to five attempts) for each required file from GitHub.
- Logs and tracks failed downloads for reporting.
- Deletes old `.tft` files from `/boot` and `/boot/firmware` to prepare for fresh installations.
- Differentiates critical files (like flows and `.tft` firmware) from optional support scripts.

## Configuration File Updates
- Ensures necessary input configuration files for relays and dimmers are created and properly formatted.
- Populates default values using `jq` for missing keys like `relays`, `dimmers`, and `type`.
- Creates or ensures default files such as `relayboard_core`, `combined_temp_chart`, and `combined_ruuvi_chart`.

## TFT and Firmware Handling
- Downloads and moves updated TouchDisplay `.tft` files to `/boot/firmware/` with version tagging.
- Places updated NSPanel `.tft` and script files in `~/pekaway/userdata/NSPanel/`.

## System Service and Rule Updates
- Updates `udev` rules and reloads them.
- Updates nginx configuration and restarts the nginx service.

## Node-RED Dependency Management
- Backs up the existing `.node-red/package.json`.
- Compares and merges any additional modules from the previous version, using `jq` to preserve dependencies.
- Automatically accepts changes in auto-update mode; otherwise prompts the user.
- Executes `npm install` to sync packages.
- Records npm install or dependency-check failures as warnings and continues; the log contains details of affected modules.

## System Package Installation
- Installs required application packages explicitly and checks `packages.txt` for additional missing packages.
- Skips foreign architectures, historical kernel packages and missing versioned `libcamera` ABI libraries from the image inventory. Camera applications resolve their matching libraries through APT dependencies.
- Preserves installed camera libraries and does not force an IPA downgrade to reinstall an obsolete camera ABI.
- If a package batch fails, retries its packages individually and records failures. APT update/upgrade failures are recorded as operation warnings when individual affected packages cannot be identified.

## Python Module Installation
- Installs system-wide and user-level Python packages as listed in `piplist.txt`.
- Requires `paho-mqtt>=2,<3` for the Power Unit bridge. Installs it in `/usr/local` without removing Debian-owned files and upgrades stale user-level packages.
- If a requirements batch fails, retries each requirement individually for the affected root or user installation and records failures.
- Verifies the imported Paho version and creates a `CallbackAPIVersion.VERSION2` client as both root and the update user. Logs the version and import path; a failed check is reported as a warning, so the Power Unit bridge may need repair.
- Uses `--break-system-packages` to avoid pip conflicts on Debian Bookworm.
- Installs `bottle` package explicitly for HTTP APIs.

## Log Management Configuration
- Ensures `logrotate.conf` contains `maxsize 60M`, updating or appending if needed.
- Ensures `log2ram.conf` sets `LOG_DISK_SIZE=256M`, updating or appending if missing.
- Restarts `log2ram` service to apply changes.

## WiFi Power Save Service Installation
- Detects if the system is a Raspberry Pi by checking `/proc/device-tree/model`.
- Creates and enables the `wifi-powersave-off.service` systemd unit to disable WiFi power saving at boot.
- The service ensures stable SSH/HTTP access on RPi5 by preventing interface sleep mode.
- The logic is safe to run on RPi4 and other Pis; it will not interfere with unsupported models.

## Node-RED Flows Handling
- Extracts user-created flows labeled "user flow" from existing `flows_pekaway.json` using a `jq` pipeline.
- Downloads the latest core `flows_pekaway.json` from the remote repository.
- Merges core flows with user flows to preserve custom changes and avoid overwriting user-defined tabs, groups, and UI settings.
- Deletes temporary flow files after merging.

## Node-RED Global Context Setup
- Ensures that required global context modules (e.g., `zlib`) are defined in `settings.js`.
- Uncomments or inserts missing entries under `functionGlobalContext`.
- Dynamically constructs context blocks if the section is missing.

## Finalization and Reboot
- Lists package and runtime warnings in the update log, dashboard progress and `package-failures.log` in the update backup directory when these destinations are writable. Warnings are retained in memory during the run if the file cannot be written. Failed updates also print warnings collected before the failure.
- Continues past package warnings, but still rolls back managed files if a later critical validation or the Node-RED service check fails. A running Node-RED service alone does not prove that every module loaded successfully.
- Updates the version number stored in `~/pekaway/version`.
- Sets update flag in `~/pekaway/update` to show update in dashboard.
- Prompts the user for reboot unless in auto-update mode.
- If the reboot is declined, restarts Node-RED to apply as many changes as possible without requiring full system restart.
