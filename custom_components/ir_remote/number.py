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
    entry_data["key_options"] = {}
    entry_data["latest_key_options"] = {}
    added: set[str] = set()

    @callback
    def handle_devices(msg):
        try:
            devices = json.loads(msg.payload)
        except Exception:
            return

        valid_unique_ids: set[str] = set()
        for device_name, keys in devices.items():
            for key in keys:
                valid_unique_ids.add(f"ir_remote_{prefix}_{device_name}_{key}_repeat_count")
                valid_unique_ids.add(f"ir_remote_{prefix}_{device_name}_{key}_repeat_delay")

        registry = er.async_get(hass)
        for entry_item in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entry_item.domain == "number" and entry_item.unique_id not in valid_unique_ids:
                registry.async_remove(entry_item.entity_id)

        new_entities = []
        for device_name, keys in devices.items():
            device_options = entry_data["key_options"].setdefault(device_name, {})
            latest = entry_data["latest_key_options"].get(device_name, {})
            for key in keys:
                uid = f"{device_name}_{key}"
                if uid not in added:
                    added.add(uid)
                    key_opts = latest.get(key, {})
                    count_entity = RepeatCountNumber(
                        hass, prefix, device_name, key, entry.entry_id,
                        initial=float(key_opts.get("repeat", 1)),
                    )
                    delay_entity = RepeatDelayNumber(
                        hass, prefix, device_name, key, entry.entry_id,
                        initial=float(key_opts.get("delay_ms", 300)),
                    )
                    device_options[key] = {"count": count_entity, "delay": delay_entity}
                    new_entities.extend([count_entity, delay_entity])

        if new_entities:
            async_add_entities(new_entities)

    @callback
    def handle_key_options(msg):
        try:
            all_options = json.loads(msg.payload)
        except Exception:
            return

        entry_data["latest_key_options"] = all_options

        for device_name, keys in all_options.items():
            for key, opts in keys.items():
                entities = entry_data["key_options"].get(device_name, {}).get(key)
                if not entities:
                    continue
                if "repeat" in opts:
                    entities["count"]._attr_native_value = float(opts["repeat"])
                    entities["count"].async_write_ha_state()
                if "delay_ms" in opts:
                    entities["delay"]._attr_native_value = float(opts["delay_ms"])
                    entities["delay"].async_write_ha_state()

    await mqtt.async_subscribe(hass, f"{prefix}/devices", handle_devices)
    await mqtt.async_subscribe(hass, f"{prefix}/key_options", handle_key_options)


class RepeatCountNumber(NumberEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        prefix: str,
        device_name: str,
        key: str,
        entry_id: str,
        initial: float = 1.0,
    ) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._key = key
        self._entry_id = entry_id
        label = f"{device_name} {key}".replace("_", " ").title()
        self._attr_name = f"{label} Repeat"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_{key}_repeat_count"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 10
        self._attr_native_step = 1
        self._attr_native_value = initial
        self._attr_mode = NumberMode.BOX
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:repeat"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
        sibling = self.hass.data[DOMAIN][self._entry_id]["key_options"].get(self._device, {}).get(self._key, {})
        delay = int(sibling["delay"]._attr_native_value) if sibling.get("delay") else 300
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/key/set_options",
            json.dumps({"device": self._device, "key": self._key, "repeat": int(value), "delay_ms": delay}),
        )


class RepeatDelayNumber(NumberEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        prefix: str,
        device_name: str,
        key: str,
        entry_id: str,
        initial: float = 300.0,
    ) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._key = key
        self._entry_id = entry_id
        label = f"{device_name} {key}".replace("_", " ").title()
        self._attr_name = f"{label} Repeat Delay"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_{key}_repeat_delay"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 2000
        self._attr_native_step = 50
        self._attr_native_value = initial
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
        sibling = self.hass.data[DOMAIN][self._entry_id]["key_options"].get(self._device, {}).get(self._key, {})
        count = int(sibling["count"]._attr_native_value) if sibling.get("count") else 1
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/key/set_options",
            json.dumps({"device": self._device, "key": self._key, "repeat": count, "delay_ms": int(value)}),
        )
