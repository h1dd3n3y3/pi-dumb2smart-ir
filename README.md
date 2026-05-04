# IR Remote (ANAVI IR pHAT) — Home Assistant Integration

[![Deploy](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/deploy.yml)
[![HACS Action](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/hacs.yml/badge.svg)](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/hacs.yml)
[![Hassfest](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/hassfest.yml/badge.svg)](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/hassfest.yml)

Control any IR-controlled device (TV, AC, amplifier) from Home Assistant. A Raspberry Pi with an [ANAVI Infrared pHAT](https://anavi.technology/) sits near your device and fires IR signals on command, communicating over MQTT.

---

## Prerequisites

- Home Assistant with the **MQTT integration** configured
- A running IR bridge — see the [`pi-dumb2smart-ir-bridge`](https://github.com/h1dd3n3y3/pi-dumb2smart-ir-bridge) repo for setup instructions

---

## Installation

### Via HACS (recommended)

1. In Home Assistant, go to **HACS → Integrations**
2. Search for **IR Remote** and install it
3. Restart Home Assistant

### Manual

1. Copy the `custom_components/ir_remote/` folder into your HA config directory:
   ```
   config/custom_components/ir_remote/
   ```
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **IR Remote**
3. Enter the MQTT topic prefix — this must match the prefix configured on the bridge (default: `ir_remote`)

> **Multiple bridges:** add the integration once per bridge, each with its own unique prefix. Not sure what prefix a bridge uses? SSH into the Pi and run `cat /etc/ir-bridge/env`.

---

## What you get

Once configured, the integration creates entities for each remote device the bridge knows about.

### Per remote device

| Entity | Type | Description |
|---|---|---|
| `button.<device>_<key>` | Button | One button per recorded IR key — press to fire the signal |
| `button.<device>_<virtual_key>` | Button | One button per virtual key — press to fire a multi-press sequence |
| `button.<device>_learn_key` | Button (config) | Puts the bridge into recording mode for a new key |
| `button.<device>_delete_key` | Button (config) | Deletes the key named in the Key Name field |
| `button.<device>_rename_key` | Button (config) | Renames a key |
| `button.<device>_enable_repeat` | Button (config) | Enables repeat for the key named in the Repeat Key field |
| `button.<device>_disable_repeat` | Button (config) | Disables repeat for that key |
| `button.<device>_register_multi_press` | Button (config) | Creates a new virtual key |
| `button.<device>_delete_virtual_key` | Button (config) | Deletes a virtual key |
| `number.<device>_<key>_repeat` | Number (config) | Repeat count for a key (appears only when repeat is enabled) |
| `number.<device>_<key>_repeat_delay` | Number (config) | Delay between repeats in ms (appears only when repeat is enabled) |
| `number.<device>_multi_press_count` | Number (config) | Press count for the next virtual key to register |
| `number.<device>_multi_press_delay` | Number (config) | Delay between presses for the next virtual key to register |
| Text inputs | Text (config) | Key Name, New Key Name, Repeat Key, Multi-Press Name, Multi-Press Source Key |

### Bridge-level entities

| Entity | Type | Description |
|---|---|---|
| `button.reload_devices` | Button | Re-reads all device files and refreshes HA entities |
| `button.register_remote` | Button (config) | Creates a new remote using the Device Name field |
| `button.rename_remote` | Button (config) | Renames a remote |
| `button.delete_remote` | Button (config) | Deletes a remote |
| `sensor.ir_recording_status` | Sensor | Current bridge state: `idle`, `recording`, `done`, `error`, `timeout` |
| Text inputs | Text (config) | Device Name, Remote New Name |

---

## Managing remotes and keys

All management is done through the Home Assistant UI.

### Creating a remote

1. Go to **Settings → Devices & Services** and open the **IR Remote** integration
2. Open the **bridge device**
3. Enter a name in the **Device Name** text input (e.g. `samsung_tv`) and press **Register Remote**

Each remote represents one physical IR-controlled device.

### Recording a key

1. Open the remote's device page inside the integration
2. Enter a name in the **Key Name** text input (e.g. `power`, `volume_up`)
3. Press **Learn Key**
4. Point your physical remote at the Pi and press the target button within 30 seconds
5. The **IR Recording Status** sensor transitions `idle` → `recording` → `done`
6. The key name field clears and a new button entity appears in HA automatically

> No restart required. Entities update live via MQTT.

### Deleting a key

1. Open the remote's device page
2. Enter the key name in the **Key Name** field and press **Delete Key**

### Renaming a key

1. Open the remote's device page
2. Enter the current name in **Key Name** and the new name in **New Key Name**
3. Press **Rename Key**

### Deleting or renaming a remote

1. Open the **bridge device**
2. Enter the remote name in the relevant text input and press **Delete Remote** or **Rename Remote**

---

## Repeat

Some devices need a key pressed more than once to register (e.g. some amplifiers). Repeat fires the IR signal N times with a configurable delay between each press.

### Enabling repeat for a key

1. Open the remote's device page
2. Enter the key name in the **Repeat Key** field (e.g. `power`)
3. Press **Enable Repeat**
4. Two new controls appear for that key: **Repeat** (count, 1–10) and **Repeat Delay** (ms)
5. Adjust the values — changes publish to the bridge immediately

### Disabling repeat

1. Enter the key name in the **Repeat Key** field
2. Press **Disable Repeat** — the count and delay controls are removed

---

## Virtual keys

Virtual keys are multi-press macros stored on the bridge. Pressing a virtual key fires an existing key N times with a delay between presses. They appear alongside regular keys and work identically in automations and scripts.

**Example:** create `vol_up_5` to raise volume 5 steps with one tap.

### Creating a virtual key

1. Open the remote's device page
2. Fill in the **Multi-Press Name** field (e.g. `vol_up_5`) — this is the name of the new button
3. Fill in the **Multi-Press Source Key** field (e.g. `vol_up`) — the existing key to repeat
4. Set **Multi-Press Count** (e.g. `5`) and **Multi-Press Delay** (e.g. `150` ms)
5. Press **Register Multi-Press**
6. The bridge creates the virtual key and a new button entity appears automatically

### Deleting a virtual key

1. Enter the virtual key name in the **Multi-Press Name** field
2. Press **Delete Virtual Key**

---

## Services (Actions)

Available under **Developer Tools → Actions**. All services accept an optional `topic_prefix` parameter to target a specific bridge (defaults to `ir_remote`).

| Service | Parameters | Description |
|---|---|---|
| `ir_remote.record_key` | `device`, `key`, `topic_prefix` | Start recording a key |
| `ir_remote.delete_key` | `device`, `key`, `topic_prefix` | Delete a key |
| `ir_remote.rename_key` | `device`, `old_key`, `new_key`, `topic_prefix` | Rename a key |

---

## Architecture

```
Home Assistant  ──MQTT──▶  Mosquitto broker  ──MQTT──▶  IR Bridge (Pi + ANAVI IR pHAT)  ──IR──▶  Device
```

The integration uses `local_push` — the bridge maintains a persistent MQTT connection and pushes state changes instantly. No polling.

---

## Related

- [ANAVI Infrared pHAT](https://anavi.technology/) — the IR hardware
- [PiIR](https://github.com/ts1/PiIR) — IR signal library used by the bridge
- [`pi-dumb2smart-ir-bridge`](https://github.com/h1dd3n3y3/pi-dumb2smart-ir-bridge) — Pi bridge setup and systemd service
