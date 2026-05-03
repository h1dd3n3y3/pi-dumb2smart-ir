# IR Remote (ANAVI pHAT) — Home Assistant Integration

[![Deploy](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/h1dd3n3y3/pi-dumb2smart-ir/actions/workflows/deploy.yml)

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

## Recording a new key

1. Enter the **device name** and **key name** in the text inputs
2. Press **Learn New Key** for the target device
3. Watch the **IR Recording Status** sensor — it will show `recording`
4. Point your physical remote at the Pi and press the button **3 times**
5. Status changes to `done` — the new button appears automatically in HA

> No restart required for new keys. Entities update live via MQTT discovery.

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
Home Assistant  ──MQTT──▶  Mosquitto broker  ──MQTT──▶  IR Bridge (Pi + ANAVI pHAT)  ──IR──▶  Device
```

The integration uses `local_push` — the bridge maintains a persistent MQTT connection and pushes state changes instantly. No polling.

---

## Related

- [ANAVI Infrared pHAT](https://anavi.technology/) — the IR hardware
- [PiIR](https://github.com/ts1/PiIR) — IR signal library used by the bridge
- [`pi-dumb2smart-ir-bridge`](https://github.com/h1dd3n3y3/pi-dumb2smart-ir-bridge) — Pi bridge setup and systemd service
