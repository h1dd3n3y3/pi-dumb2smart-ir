import json

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
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
    added = set()

    @callback
    def handle_devices(msg):
        try:
            devices = json.loads(msg.payload)
        except Exception:
            return

        new_entities = []
        for device_name, keys in devices.items():
            for key in keys:
                uid = f"{device_name}_{key}"
                if uid not in added:
                    added.add(uid)
                    new_entities.append(
                        IRRemoteButton(hass, prefix, device_name, key)
                    )

        if new_entities:
            async_add_entities(new_entities)

    await mqtt.async_subscribe(hass, f"{prefix}/devices", handle_devices)


class IRRemoteButton(ButtonEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        prefix: str,
        device_name: str,
        key: str,
    ) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._key = key
        self._attr_name = f"{device_name} {key}".replace("_", " ").title()
        self._attr_unique_id = f"ir_remote_{device_name}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/{self._device}/send",
            self._key,
        )
