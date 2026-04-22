import json

from homeassistant.components import mqtt
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    prefix = entry.data.get(CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX)
    added = set()

    hass.data[DOMAIN].setdefault("key_name_texts", {})

    @callback
    def handle_devices(msg):
        try:
            devices = json.loads(msg.payload)
        except Exception:
            return

        new_entities = []
        for device_name in devices:
            if device_name not in added:
                added.add(device_name)
                entity = KeyNameText(device_name)
                hass.data[DOMAIN]["key_name_texts"][device_name] = entity
                new_entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    await mqtt.async_subscribe(hass, f"{prefix}/devices", handle_devices)


class KeyNameText(TextEntity):
    def __init__(self, device_name: str) -> None:
        self._attr_name = f"{device_name.replace('_', ' ').title()} Key Name"
        self._attr_unique_id = f"ir_remote_{device_name}_key_name"
        self._attr_native_value = ""
        self._attr_native_min = 0
        self._attr_native_max = 64
        self._attr_available = True
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:keyboard"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_set_value(self, value: str) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()

    @callback
    def clear(self) -> None:
        self._attr_native_value = ""
        self.async_write_ha_state()
