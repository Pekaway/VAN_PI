# 🧭 MQTT Interface: Dometic RC10 Fridge

---

This document describes the MQTT control and telemetry interface for the `DometicRC10` device class, including topic names, payload formats, and Home Assistant MQTT Discovery entities.

---

## ✅ General Topic Structure

All MQTT messages use the base topic prefix:

```
CI/devices/<device_name>/
```

For the Dometic RC10:

```
CI/devices/DometicRC10/
```

---

## 🔁 MQTT Control Topics

The RC10 supports a small set of remote controls: **power**, **mode**, and **set step**.  
Compressor and fans are **status only** (read-only).

> The integration mirrors the fridge’s own panel on startup and **does not overwrite manual settings** unless you send a command. After you do, the bridge asserts your command briefly, then goes back to mirroring the panel.

### 🔌 Power

**Topic:**  
```
.../control/power
```

**Payload Options:**
- `"on"`, `"1"`, `"true"` → turn fridge on  
- `"off"`, `"0"`, `"false"` → turn fridge off

> HA Discovery uses an **optimistic switch**: the UI toggles immediately and is corrected by the next status update.

---

### 🧊 Cooling Mode

**Topic:**  
```
.../control/mode
```

**Payload Options:**
- `"performance"` / `"0"`
- `"silent"` / `"2"`
- `"turbo"` / `"3"`

---

### 📈 Cooling Set Step (1..5)

**Topic:**  
```
.../control/set_step
```

**Payload:** integer or numeric string in the range **1..5**  
Examples: `"1"`, `"3"`, `5`

---

### 📦 Bulk Control Payload (preferred for multi-field writes)

**Topic:**  
```
.../control/full
```

**JSON Payload Example:**
```json
{
  "power": "on",
  "mode": "silent",
  "set_step": 3
}
```````

**Accepted fields:**
- `"power"`: boolean or `"on"/"off"/"1"/"0"`
- `"mode"`: `"performance"|"silent"|"turbo"` or `0|2|3`
- `"set_step"`: `1..5` (number or string)

> Advanced (optional): the payload also accepts `"lock"`, `"sync"`, `"c_mode"` (booleans). These map to internal bits and are primarily diagnostic—most users should **not** set them.

---

## 📤 Status Topics

### Device Status

**Topic:**
```
.../status
```

**Top-level structure:**
- `status.*` → live fridge state
- `diagnostics.*` → flags, error code & text, CI status
- `metrics.*` → publish counters and uptime

**Key Fields:**

`status`  
- `power_on` → boolean  
- `power_source` → `"AC" | "DC12" | "DC24" | "unknown"`  
- `user_mode` → `"performance" | "silent" | "turbo"`  
- `set_step` → `1..5`  
- `compressor_on` → boolean (read-only)  
- `condensor_fan_on` → boolean (read-only)

`diagnostics`  
- `error_code` → `0..127`  
- `error` → human-readable text (mapped)  
- `ai_type` → `"refrigeration"` or `"global"`  
- `fan1_available`, `fan2_available` → booleans  
- `lstat`, `rchange`, `lchange` → flag booleans  
- `page` → page id (uint)

`metrics`  
- `publish_count` → counter  
- `last_valid_age_sec` → seconds since last valid INFO frame  
- `script_runtime` → uptime `DDd, HH:MM` or `HH:MM`

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
  "status": {
    "power_on": true,
    "power_source": "DC12",
    "user_mode": "silent",
    "set_step": 3,
    "compressor_on": true,
    "condensor_fan_on": false
  },
  "diagnostics": {
    "alive": "online",
    "error_code": 0,
    "error": "none",
    "ai_type": "refrigeration",
    "fan1_available": true,
    "fan2_available": false,
    "lstat": false,
    "rchange": false,
    "lchange": false,
    "page": 2
  },
  "metrics": {
    "publish_count": 257,
    "last_valid_age_sec": 0,
    "script_runtime": "00:24"
  }
}
```

---

## 🏠 Home Assistant Auto Discovery

If enabled via `.env` (`HA_DISCO_PREFIX`), the following entities are published with retain:

- **Switch**: Power (`optimistic: true`)
- **Select**: Mode (`performance`, `silent`, `turbo`)
- **Select**: Setting (`1`..`5`)
- **Binary Sensor**: Compressor running
- **Binary Sensor**: Condenser fan running
- **Sensor**: Power source (`AC / DC12 / DC24`)
- **Sensor**: Error code (numeric)
- **Sensor**: Error (human-readable text)

> Lock/Sync/C-Mode are exported as status in the JSON but are **not** exposed as switches in HA (to avoid misleading controls).

---

## ⚠️ Error Codes (mapped)

The `diagnostics.error` string is derived from `error_code`:

- `0` — **none**
- `1` — **W01** Defrost NTC1 defective  
- `2` — **W02** Fridge air NTC2 defective  
- `3` — **E03** No connection between display and power module  
- `4` — **W04** No connection to CI master  
- `10` — **W10** Door open > 2 minutes  
- `11` — **W11** Battery voltage extra-low/high  
- `14` — **W14** Evaporator fan (FAN2) defective  
- `17` — **W17** Defrost heater fault — low current  
- `18` — **E18** Defrost heater fault — high current  
- `19` — **W19** Battery voltage input low  
- `26` — **W26** Ambient sensor defective  
- `32` — **E32** Compressor fault — condenser fan over-current  
- `33` — **E33** Compressor fault — compressor did not start  
- `34` — **E34** Compressor fault — compressor overloaded  
- `35` — **E35** Compressor fault — controller over-temperature  
- other — **unknown**

---

## 🔄 Behavior & Timing Notes

- On startup the bridge **reads INFO** and **mirrors** the fridge’s current settings into its control frame. It **does not** change settings on its own.
- When you send a command, the bridge asserts it for a short window (a few frames) with a **SYNC pulse** and then returns to mirroring the panel.
- Heartbeats are sent roughly every 2 seconds, built from **observed** panel values (so they don’t fight manual changes).
- The HA Power switch is **optimistic**: it flips immediately; the next status will confirm/correct the state.

---

## 🛠️ Example Setup in Node-RED

### 1. 🧲 Subscribing to Status Updates

- **Topic**: `CI/devices/DometicRC10/status`  
- Output: parsed JSON

Optional LWT:
- **Topic**: `CI/devices/DometicRC10/status/LWT`  
- Payload: `"online"` / `"offline"`

---

### 2. 🎛️ Sending Control Commands

Use **MQTT-out** nodes.

#### 🔌 Power
- **Topic**: `CI/devices/DometicRC10/control/power`
- **Payload**: `"on"` / `"off"`

#### 🧊 Mode
- **Topic**: `CI/devices/DometicRC10/control/mode`
- **Payload**: `"performance"`, `"silent"`, or `"turbo"`

#### 📈 Set Step
- **Topic**: `CI/devices/DometicRC10/control/set_step`
- **Payload**: `1..5`

#### 📦 Bulk Control
- **Topic**: `CI/devices/DometicRC10/control/full`
- **Payload** (JSON):
```json
{ "power": "on", "mode": "performance", "set_step": 5 }
```

---

## 📚 Notes

- MQTT publishes are rate-limited by `publish_interval_ms`.  
  Publishing occurs at the end of the device loop when the interval has elapsed.
- Recommended: keep `publish_interval_ms` ≥ 2× your `loop_internal_ms`.
- Compressor and fan are **status only** and cannot be forced by MQTT.
- The panel knob can still be used; the bridge follows manual changes unless you just issued a command.

---

© Pekaway GmbH · Dometic RC10 Integration via CI2MQTT Bridge
