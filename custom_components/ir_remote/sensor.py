import json

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    prefix = entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)
    sensor = RecordingStatusSensor(prefix)
    async_add_entities([sensor])

    @callback
    def handle_status(msg):
        try:
            data = json.loads(msg.payload)
            sensor.set_status(data.get("status", "idle"), data.get("key", ""))
        except Exception:
            pass

    await mqtt.async_subscribe(hass, f"{prefix}/record/status", handle_status)


class RecordingStatusSensor(SensorEntity):
    def __init__(self, prefix: str) -> None:
        self._attr_name = "IR Recording Status"
        self._attr_unique_id = f"ir_remote_{prefix}_recording_status"
        self._attr_native_value = "idle"
        self._attr_icon = "mdi:record-circle"
        self._attr_extra_state_attributes = {"key": ""}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_bridge")},
            name="IR Bridge",
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    @callback
    def set_status(self, status: str, key: str) -> None:
        self._attr_native_value = status
        self._attr_extra_state_attributes = {"key": key}
        self.async_write_ha_state()
