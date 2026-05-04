import json

from homeassistant.components import mqtt
from homeassistant.components.number import NumberEntity, NumberMode
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
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices_added: set[str] = set()

    @callback
    def handle_devices(msg):
        try:
            devices = json.loads(msg.payload)
        except Exception:
            return

        registry = er.async_get(hass)
        for entry_item in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entry_item.domain != "number":
                continue
            uid = entry_item.unique_id
            if uid.endswith("_repeat_count") or uid.endswith("_repeat_delay"):
                registry.async_remove(entry_item.entity_id)
                continue
            if uid in (
                f"ir_remote_{prefix}_{d}_multipress_count" for d in list(entry_data.get("multipress_count_numbers", {}))
                if d not in devices
            ):
                registry.async_remove(entry_item.entity_id)

        new_entities = []
        for device_name in devices:
            if device_name not in devices_added:
                devices_added.add(device_name)
                count_entity = MultiPressCountNumber(hass, prefix, device_name, entry.entry_id)
                delay_entity = MultiPressDelayNumber(hass, prefix, device_name, entry.entry_id)
                entry_data["multipress_count_numbers"][device_name] = count_entity
                entry_data["multipress_delay_numbers"][device_name] = delay_entity
                new_entities.extend([count_entity, delay_entity])

        if new_entities:
            async_add_entities(new_entities)

    await mqtt.async_subscribe(hass, f"{prefix}/devices", handle_devices)


class MultiPressCountNumber(NumberEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, device_name: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._entry_id = entry_id
        self._attr_name = f"{device_name.replace('_', ' ').title()} Virtual Key Count"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_multipress_count"
        self._attr_native_min_value = 2
        self._attr_native_max_value = 20
        self._attr_native_step = 1
        self._attr_native_value = 2.0
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:counter"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()


class MultiPressDelayNumber(NumberEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, device_name: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._entry_id = entry_id
        self._attr_name = f"{device_name.replace('_', ' ').title()} Virtual Key Delay"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_multipress_delay"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 2000
        self._attr_native_step = 50
        self._attr_native_value = 300.0
        self._attr_native_unit_of_measurement = "ms"
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:timer-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
