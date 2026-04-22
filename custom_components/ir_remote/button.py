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
            learn_uid = f"{device_name}_learn"
            if learn_uid not in added:
                added.add(learn_uid)
                new_entities.append(LearnButton(hass, prefix, device_name))
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
    async_add_entities([ReloadButton(hass, prefix)])


class ReloadButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._attr_name = "Reload Devices"
        self._attr_unique_id = f"ir_remote_{prefix}_reload"
        self._attr_icon = "mdi:reload"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_bridge")},
            name="IR Bridge",
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        await mqtt.async_publish(self.hass, f"{self._prefix}/reload", "1")


class LearnButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, device_name: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._attr_name = f"{device_name} ~ Learn Key".replace("_", " ").title()
        self._attr_unique_id = f"ir_remote_{device_name}_learn"
        self._attr_icon = "mdi:record-circle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        text_entity = self.hass.data[DOMAIN].get("key_name_texts", {}).get(self._device)
        key_name = (text_entity._attr_native_value or "").strip() if text_entity else ""
        if not key_name:
            return
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/record/start",
            json.dumps({"device": self._device, "key": key_name}),
        )


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
