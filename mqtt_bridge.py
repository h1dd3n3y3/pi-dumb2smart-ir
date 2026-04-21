#!/usr/bin/env python3
"""MQTT bridge for ANAVI IR pHAT — anonymous broker connection.

Connects to the MQTT broker without credentials (anonymous access).
Publishes:
  - ir_remote/devices       retained JSON device+key map (for HA integration)
  - homeassistant/button/.. MQTT Discovery configs (for native HA MQTT)
  - ir_remote/availability  online/offline LWT

Subscribes to:
  - ir_remote/<device>/send  payload = key name → fires IR signal

Environment variables:
    MQTT_HOST   broker hostname/IP  (default: homeassistant.local)
    MQTT_PORT   broker port         (default: 1883)
"""

import glob
import json
import os
import sys

import paho.mqtt.client as mqtt
import piir  # type: ignore

TX_GPIO = 17

MQTT_HOST = os.getenv("MQTT_HOST", "pi5.local")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

DISCOVERY_PREFIX = "homeassistant"
BASE_TOPIC = "ir_remote"
AVAILABILITY_TOPIC = f"{BASE_TOPIC}/availability"
DEVICES_TOPIC = f"{BASE_TOPIC}/devices"


# ---------------------------------------------------------------------------
# Device helpers
# ---------------------------------------------------------------------------

def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def load_all_devices() -> dict:
    """Return {device_name: [key, ...]} for every valid *.json in script dir."""
    devices = {}
    for path in sorted(glob.glob(os.path.join(_script_dir(), "*.json"))):
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path) as f:
                data = json.load(f)
            keys = list(data.get("keys", {}).keys())
            if keys:
                devices[name] = keys
        except Exception as exc:
            print(f"[WARN] Skipping {path}: {exc}")
    return devices


# ---------------------------------------------------------------------------
# MQTT Discovery
# ---------------------------------------------------------------------------

def publish_discovery(client: mqtt.Client, devices: dict) -> None:
    for device_name, keys in devices.items():
        device_id = f"ir_{device_name}"
        command_topic = f"{BASE_TOPIC}/{device_name}/send"
        for key in keys:
            unique_id = f"{device_id}_{key}"
            config = {
                "name": key.replace("_", " ").title(),
                "unique_id": unique_id,
                "command_topic": command_topic,
                "payload_press": key,
                "availability_topic": AVAILABILITY_TOPIC,
                "device": {
                    "identifiers": [device_id],
                    "name": device_name.replace("_", " ").title(),
                    "model": "ANAVI IR pHAT",
                    "manufacturer": "ANAVI",
                },
            }
            topic = f"{DISCOVERY_PREFIX}/button/{unique_id}/config"
            client.publish(topic, json.dumps(config), retain=True)

    print(f"[INFO] Discovery published for {len(devices)} device(s).")


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------

def on_connect(client, userdata, flags, rc, properties=None):
    if rc != 0:
        print(f"[ERROR] MQTT connect failed (rc={rc}). Retrying...")
        return

    print(f"[INFO] Connected to {MQTT_HOST}:{MQTT_PORT}")
    client.publish(AVAILABILITY_TOPIC, "online", retain=True)

    devices = load_all_devices()
    if not devices:
        print("[WARN] No device JSON files found — nothing to publish.")
        return

    client.publish(DEVICES_TOPIC, json.dumps(devices), retain=True)
    publish_discovery(client, devices)

    for device_name in devices:
        topic = f"{BASE_TOPIC}/{device_name}/send"
        client.subscribe(topic)
        print(f"[INFO] Subscribed to {topic}")


def on_message(client, userdata, msg):
    parts = msg.topic.split("/")
    if len(parts) != 3:
        return

    device_name = parts[1]
    key = msg.payload.decode().strip()
    device_path = os.path.join(_script_dir(), f"{device_name}.json")

    try:
        remote = piir.Remote(device_path, TX_GPIO)
        remote.send(key)
        print(f"[INFO] Sent: {device_name}/{key}")
    except Exception as exc:
        print(f"[ERROR] Failed to send {device_name}/{key}: {exc}")


def on_disconnect(client, userdata, rc, properties=None, reasoncode=None):
    if rc != 0:
        print(f"[WARN] Unexpected disconnect (rc={rc}). paho will reconnect.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.will_set(AVAILABILITY_TOPIC, "offline", retain=True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except Exception as exc:
        print(f"[ERROR] Cannot connect to {MQTT_HOST}:{MQTT_PORT}: {exc}")
        sys.exit(1)

    client.loop_forever()


if __name__ == "__main__":
    main()
