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
3. Enter the MQTT topic prefix (default: `ir_remote`) — must match what the bridge uses

---

## What you get

Once configured, the integration creates entities for each remote device the bridge knows about.

### Per recorded device

| Entity | Type | Description |
|---|---|---|
| `button.<device>_<key>` | Button | One button per recorded IR key — press to fire the signal |
| `button.<device>_learn_new_key` | Button | Puts the bridge into recording mode for a new key on this device |
| `button.<device>_delete_remote` | Button | Deletes the entire device and all its keys |
| `button.<device>_rename_remote` | Button | Renames the device using the text input |

### Bridge-level entities

| Entity | Type | Description |
|---|---|---|
| `button.reload_devices` | Button | Re-reads all device files and refreshes HA entities |
| `button.create_new_remote` | Button | Creates a new empty device using the text input |
| `button.rename_remote` | Button | Renames a device |
| `button.delete_remote` | Button | Deletes a device |
| `sensor.ir_recording_status` | Sensor | Current bridge state: `idle`, `recording`, `done`, `error`, `timeout` |
| Text inputs | Text | Input fields for device name, key name, rename targets |

---

## Managing remotes and keys

All management is done through the Home Assistant UI.

### Creating a remote

1. Go to **Settings → Devices & Services** and open the **IR Remote** integration
2. Open the **bridge device**
3. Enter a name in the **Device Name** text input (e.g. `samsung_tv`) and press **Create New Remote**

Each remote represents one physical IR-controlled device.

### Recording a key

1. Open the remote's device page inside the integration
2. Enter a name in the **Key Name** text input (e.g. `power`, `volume_up`)
3. Press **Learn Key**
4. Point your physical remote at the Pi and press the target button within 30 seconds
5. The **IR Recording Status** sensor transitions `idle` → `recording` → `done`
6. The key name field clears and a new button entity appears in HA automatically

> No restart required. Entities update live via MQTT discovery.

### Deleting a key

1. Open the remote's device page
2. Press the **Delete Key** button next to the key you want to remove

### Renaming a key

1. Open the remote's device page
2. Enter the new name in the **Rename Key** text input
3. Press **Rename Key**

### Deleting or renaming a remote

1. Open the **bridge device**
2. Enter the remote name in the relevant text input and press **Delete Remote** or **Rename Remote**

---

## Services (Actions)

Available under **Developer Tools → Actions**:

| Service | Parameters | Description |
|---|---|---|
| `ir_remote.record_key` | `device`, `key` | Start recording a key |
| `ir_remote.delete_key` | `device`, `key` | Delete a key |
| `ir_remote.rename_key` | `device`, `old_key`, `new_key` | Rename a key |

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
