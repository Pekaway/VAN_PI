# 🧭 MQTT Interface: Truma Combi Heater

---

This document describes the MQTT control and telemetry interface for the `TrumaCombiHeater` device class, including topic names, payload formats, and integration with Home Assistant via MQTT Discovery.

---

## Note: A Truma CP plus with CI connector is needed to run this application.

## ✅ General Topic Structure

All MQTT messages use the base topic prefix:

```
CI/devices/<device_name>/
```

which in case of the Truma Combi Heater translates to

```
CI/devices/TrumaCombiHeater/
```
---

## 🔁 MQTT Control Topics

### Note: The Truma CP plus will ignore any incoming control commands if it is in manual mode! Manual mode is active if the Truma CP plus backlight is on or other events have been triggered like timers, infrared remote or iNetBox commands!

Each control topic accepts a payload string (or number, or JSON where specified).

### 🔥 Water Heater Mode

**Topic:**  
```
.../control/water/target
```

**Payload Options:**

- `"off"`, `"0"`, `"false"` → Turn off water heating
- `"eco"`, `"40"`, `"on"`, `"true"` → ECO mode (40°C)
- `"hot"`, `"60"` → HOT mode (60°C)

---

### ⚡ Energy Source

**Topic:**  
```
.../control/energy
```

**Payload Options:**

- `"fuel"`, `"gas"`, `"1"` → Fuel only
- `"electric"`, `"electricity"`, `"2"` → Electric only
- `"mix"`, `"both"`, `"3"` → Fuel + Electric

---

### ⚙️ Power Limit

**Topic:**  
```
.../control/powerlimit
```

**Payload Options:**

- `"900"`, `"1"` → Limit to 900 W
- `"1800"`, `"2"` → Limit to 1800 W

Note: Power limit is used only in case of Truma Combi gas and Truma Combi diesel with electro option.

---

### 🌬️ Air Mode

**Topic:**  
```
.../control/air/mode
```

**Payload Options:**

- `"normal"` / `"heat"`
- `"auto"` / `"automatic"`

Note: Automatic climate control is available only from CP plus firmware version 4.00.00 and if ACC = ON in the Truma CP plus settings menu.

---

### 🌡️ Air Target Temperature

**Topic:**  
```
.../control/air/target
```

**Payload Options:**

- `"off"`, `"0"`, `"false"` → Disable air heating
- `"on"`, `"true"` → Set to default 20°C
- Integer value (e.g. `"21"`) → Set temperature

> Valid ranges:
> - Normal mode: 5–30°C
> - Auto mode: 18–25°C

---

### 🕒 CP Plus Time

**Topic:**  
```
.../control/cpplus/time
```

**JSON Payload Example:**
```json
{
  "hour": 14,
  "minute": 30,
  "second": 0,
  "format": 24
}
```

- `"format"` is optional (`24` default, `12` for AM/PM). 
- `"hour"` has to be set in 24h format always.
- Reports will always show 24h format
- The format is only needed to change the time format displayed in the Truma CP plus panel.

---

### 📦 Bulk Control Payload (preferred way to control the Truma Combi Heater)

**Topic:**  
```
.../control/full
```

**JSON Payload Example:**
```json
{
  "water": "eco",
  "energy": "mix",
  "powerlimit": 900,
  "air_mode": "normal",
  "air_target": 21
}
```

---

### ♻️ Metrics Reset

**Topic:**  
```
.../control/metrics/reset
```

**Payload:** `"true"`, `"yes"`, `"1"`, or `"reset"`

The following metrics will reset:

- `"publish_count"`
- `"manual_mode_count"`

---

## 📤 Status Topics

### Device Status

**Topic:**
```
.../status
```

**Example Fields:**
- `air.target`, `air.mode`, `water.target`
- `diagnostics.error`, `diagnostics.energy`, `diagnostics.power_limit`, `diagnostics.flags`
- `diagnostics.model`, `diagnostics.manual_mode_active`
- `metrics.publish_count`, `metrics.script_runtime`, `metrics.manual_mode_count`
- `metrics.heater_fw`, `metrics.cpplus_fw`, `metrics.cpplus_time`

### LWT Topic

**Topic:**
```
.../status/LWT
```

**Payload:** `"online"` / `"offline"`

---

## 🧪 Sample Status Payload

```json
{
  "air": {
    "mode": "normal",
    "target": "off"
  },
  "diagnostics": {
    "alive": "online",
    "energy": "fuel",
    "error": "none",
    "error_severity": "none",
    "flags": "230v ",
    "manual_mode_active": false,
    "model": "Combi Gas 4 E",
    "power_limit": 900
  },
  "metrics": {
    "cpplus_fw": "v4.5.2 (Build 4594)",
    "cpplus_time": "09:30:04",
    "heater_fw": "v2.0.1 (Build 1)",
    "last_valid_age_sec": 0,
    "manual_mode_count": 0,
    "publish_count": "10.433",
    "script_runtime": "16:30"
  },
  "water": {
    "target": "off"
  }
}
```

### 🔍 Explanation

- **air.mode**: `"normal"` – the air heater is in normal mode.
- **air.target**: `"off"` – air heating is currently turned off.
- **water.target**: `"off"` – water heating is off.
- **diagnostics.alive**: `"online"` – the device is considered online.
- **diagnostics.energy**: `"fuel"` – the system is using fuel as the energy source.
- **diagnostics.error** & **error_severity**: `"none"` – no current error.
- **diagnostics.flags**: `"230v "` – indicates the presence of a 230V connection.
- **diagnostics.manual_mode_active**: `false` – manual override is not active.
- **diagnostics.model**: `"Combi Gas 4 E"` – detected model from identifier response.
- **diagnostics.power_limit**: `900` – current power limit in watts.
- **metrics.cpplus_fw**: `"v4.5.2 (Build 4594)"` – firmware version of the CP Plus control panel.
- **metrics.cpplus_time**: `"09:30:04"` – internal time of the CP Plus.
- **metrics.heater_fw**: `"v2.0.1 (Build 1)"` – heater firmware version.
- **metrics.last_valid_age_sec**: `0` – seconds since the last valid frame was received. Should always be 0.
- **metrics.manual_mode_count**: `0` – number of times manual override was activated.
- **metrics.publish_count**: `"10.433"` – number of MQTT publishes (dot-separated for readability).
- **metrics.script_runtime**: `"16:30"` – uptime of the script in HH:MM.

## 🏠 Home Assistant Auto Discovery

If enabled via `.env` (`HA_DISCO_PREFIX`), the following entities are created:

- **Climate**: Air target control (mode + temperature)
- **Selects**: Water mode, energy source, power limit
- **Sensors**: Error, flags, CP Plus time, firmware, runtime, publish counter, manual mode counter
- **Binary Sensor**: Manual mode

All entities are published with retain and match HA standards.

---

## 📚 Notes

- MQTT publishes are rate-limited by `publish_interval_ms` in `.env`
- MQTT publishing happens ad the end of the individual device loop and if the interval time has passed.
    - Therefore `publish_interval_ms` should always be at least twice the value of `loop_internal_ms`
- Some diagnostics will only be read once at startup of the script, for example firmware versions and the model
- Manual mode (from control panel) overrides current settings
- During manual mode, the control panel does ignore any input from external

---

## 🛠️ Example Setup in Node-RED

### 1. 🧲 Subscribing to Status Updates

Use an **MQTT-in** node to receive live data:

- **Topic**: `CI/devices/TrumaCombiHeater/status`
- **Output**: Parsed JSON (`auto` option)

This provides:
- Air heater mode and target temperature
- Water heater mode
- Diagnostic flags, energy mode, power limits
- Internal CP Plus time
- Manual mode state and runtime counters
- Firmware versions (heater + CP Plus)

Optional:
- Add a second **MQTT-in** node for availability:
  - **Topic**: `CI/devices/TrumaCombiHeater/status/LWT`
  - Payload: `"online"` or `"offline"`

---

### 2. 🎛️ Sending Control Commands

Use **MQTT-out** nodes to publish control messages.
You can send payloads from **inject** or **function** nodes.

#### 💧 Water Heater Mode
- **Topic**: `CI/devices/TrumaCombiHeater/control/water/target`
- **Payload** (string): `"off"`, `"eco"`, or `"hot"`

#### 🌡️ Air Heater Target
- **Topic**: `CI/devices/TrumaCombiHeater/control/air/target`
- **Payload** (string or float):
  - `"off"` to disable heating
  - `"20"` or any valid °C as string or number (range depends on mode)

#### ⚙️ Air Mode
- **Topic**: `CI/devices/TrumaCombiHeater/control/air/mode`
- **Payload**: `"normal"` or `"automatic"`

#### ⚡ Energy Source
- **Topic**: `CI/devices/TrumaCombiHeater/control/energy`
- **Payload**: `"fuel"`, `"electricity"`, or `"mix"`

#### 🔌 Power Limit
- **Topic**: `CI/devices/TrumaCombiHeater/control/powerlimit`
- **Payload**: `"900"` or `"1800"`

#### ⏱️ Set CP Plus Internal Time
- **Topic**: `CI/devices/TrumaCombiHeater/control/cpplus/time`
- **Payload** (JSON):
```json
{
  "hour": 9,
  "minute": 30,
  "second": 0,
  "format": 24
}
```

#### 📦 Bulk Control (Recommended for full config)
- **Topic**: `CI/devices/TrumaCombiHeater/control/full`
- **Payload** (JSON):
```json
{
  "water": "eco",
  "energy": "mix",
  "powerlimit": 1800,
  "air_mode": "normal",
  "air_target": 22
}
```

### 3. 🧪 Debugging & Flow Design Tips

- Use **debug** nodes to inspect `msg.payload` from `status` topics.
- Use **inject nodes** to quickly send test control values.
- Group controls in a **UI dashboard** with toggles, sliders, and dropdowns.
- Wire `status` MQTT-in → `switch` nodes to show alerts on fault conditions.

---

© Pekaway GmbH · Truma Combi Heater Integration via CI2MQTT Bridge
