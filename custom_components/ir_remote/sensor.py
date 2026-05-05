import json

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    prefix = entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)
    added: set[str] = set()
    sensors: list["RecordingStatusSensor"] = []

    @callback
    def handle_devices(msg):
        try:
            devices = json.loads(msg.payload)
        except Exception:
            return

        valid_unique_ids = {
            f"ir_remote_{prefix}_{device_name}_recording_status"
            for device_name in devices
        }
        registry = er.async_get(hass)
        for entry_item in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entry_item.domain == "sensor" and entry_item.unique_id not in valid_unique_ids:
                registry.async_remove(entry_item.entity_id)

        new_entities = []
        for device_name in devices:
            if device_name not in added:
                added.add(device_name)
                sensor = RecordingStatusSensor(prefix, device_name)
                sensors.append(sensor)
                new_entities.append(sensor)

        if new_entities:
            async_add_entities(new_entities)

    @callback
    def handle_status(msg):
        try:
            data = json.loads(msg.payload)
            status = data.get("status", "idle")
            key = data.get("key", "")
        except Exception:
            return

        for sensor in sensors:
            sensor.set_status(status, key)

        if status == "done":
            for text_entity in hass.data[DOMAIN][entry.entry_id]["key_name_texts"].values():
                text_entity.clear()

    await mqtt.async_subscribe(hass, f"{prefix}/devices", handle_devices)
    await mqtt.async_subscribe(hass, f"{prefix}/record/status", handle_status)


class RecordingStatusSensor(SensorEntity):
    def __init__(self, prefix: str, device_name: str) -> None:
        self._attr_name = f"{device_name.replace('_', ' ').title()} IR Recording Status"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_recording_status"
        self._attr_native_value = "idle"
        self._attr_icon = "mdi:record-circle"
        self._attr_extra_state_attributes = {"key": ""}
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    @callback
    def set_status(self, status: str, key: str) -> None:
        self._attr_native_value = status
        self._attr_extra_state_attributes = {"key": key}
        self.async_write_ha_state()
