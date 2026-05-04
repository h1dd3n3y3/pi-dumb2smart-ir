import json
import logging

_LOGGER = logging.getLogger(__name__)

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
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

    @callback
    def handle_devices(msg):
        try:
            devices = json.loads(msg.payload)
        except Exception:
            return

        new_entities = []

        valid_unique_ids: set[str] = {
            f"ir_remote_{prefix}_reload",
            f"ir_remote_{prefix}_save_remote",
            f"ir_remote_{prefix}_delete_remote",
            f"ir_remote_{prefix}_rename_remote",
        }
        for device_name, keys in devices.items():
            valid_unique_ids.add(f"ir_remote_{prefix}_{device_name}_learn")
            valid_unique_ids.add(f"ir_remote_{prefix}_{device_name}_delete")
            valid_unique_ids.add(f"ir_remote_{prefix}_{device_name}_rename")
            valid_unique_ids.add(f"ir_remote_{prefix}_{device_name}_register_multipress")
            for key in keys:
                valid_unique_ids.add(f"ir_remote_{prefix}_{device_name}_{key}")

        registry = er.async_get(hass)
        for entry_item in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entry_item.domain == "button" and entry_item.unique_id not in valid_unique_ids:
                registry.async_remove(entry_item.entity_id)
                added.discard(entry_item.unique_id.removeprefix(f"ir_remote_{prefix}_"))

        valid_device_ids = {f"ir_{prefix}_{device_name}" for device_name in devices}
        valid_device_ids.add(f"ir_{prefix}_bridge")
        device_reg = dr.async_get(hass)
        for device_entry in dr.async_entries_for_config_entry(device_reg, entry.entry_id):
            identifier = next(
                (id_ for dom, id_ in device_entry.identifiers if dom == DOMAIN), None
            )
            if identifier and identifier not in valid_device_ids:
                device_reg.async_remove_device(device_entry.id)

        for device_name, keys in devices.items():
            learn_uid = f"{device_name}_learn"
            if learn_uid not in added:
                added.add(learn_uid)
                new_entities.append(LearnButton(hass, prefix, device_name, entry.entry_id))
                new_entities.append(DeleteButton(hass, prefix, device_name, entry.entry_id))
                new_entities.append(RenameButton(hass, prefix, device_name, entry.entry_id))
                new_entities.append(RegisterMultiPressButton(hass, prefix, device_name, entry.entry_id))
            for key in keys:
                uid = f"{device_name}_{key}"
                if uid not in added:
                    added.add(uid)
                    new_entities.append(IRRemoteButton(hass, prefix, device_name, key))

        if new_entities:
            async_add_entities(new_entities)

    await mqtt.async_subscribe(hass, f"{prefix}/devices", handle_devices)
    async_add_entities([
        ReloadButton(hass, prefix),
        CreateDeviceButton(hass, prefix, entry.entry_id),
        DeleteDeviceButton(hass, prefix, entry.entry_id),
        RenameDeviceButton(hass, prefix, entry.entry_id),
    ])


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


class CreateDeviceButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._entry_id = entry_id
        self._attr_name = "Register Remote"
        self._attr_unique_id = f"ir_remote_{prefix}_save_remote"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:content-save"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_bridge")},
            name="IR Bridge",
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        text_entity = self.hass.data[DOMAIN][self._entry_id].get("new_device_name_text")
        name = (text_entity._attr_native_value or "").strip() if text_entity else ""
        if not name:
            return
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/device/create",
            json.dumps({"device": name}),
        )
        if text_entity:
            text_entity.clear()


class DeleteDeviceButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._entry_id = entry_id
        self._attr_name = "Delete Remote"
        self._attr_unique_id = f"ir_remote_{prefix}_delete_remote"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:trash-can-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_bridge")},
            name="IR Bridge",
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        text_entity = self.hass.data[DOMAIN][self._entry_id].get("new_device_name_text")
        name = (text_entity._attr_native_value or "").strip() if text_entity else ""
        if not name:
            return
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/device/delete",
            json.dumps({"device": name}),
        )
        if text_entity:
            text_entity.clear()


class RenameDeviceButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._entry_id = entry_id
        self._attr_name = "Rename Remote"
        self._attr_unique_id = f"ir_remote_{prefix}_rename_remote"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:rename-box"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_bridge")},
            name="IR Bridge",
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        old_text = entry_data.get("new_device_name_text")
        new_text = entry_data.get("rename_device_name_text")
        old_name = (old_text._attr_native_value or "").strip() if old_text else ""
        new_name = (new_text._attr_native_value or "").strip() if new_text else ""
        if not old_name or not new_name:
            return
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/device/rename",
            json.dumps({"old": old_name, "new": new_name}),
        )
        if old_text:
            old_text.clear()
        if new_text:
            new_text.clear()


class LearnButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, device_name: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._entry_id = entry_id
        self._attr_name = f"{device_name.replace('_', ' ').title()} Learn Key"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_learn"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:record-circle"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        text_entity = self.hass.data[DOMAIN][self._entry_id]["key_name_texts"].get(self._device)
        key_name = (text_entity._attr_native_value or "").strip().lower() if text_entity else ""
        if not key_name:
            return
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/record/start",
            json.dumps({"device": self._device, "key": key_name}),
        )


class DeleteButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, device_name: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._entry_id = entry_id
        self._attr_name = f"{device_name.replace('_', ' ').title()} Delete Key"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_delete"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:trash-can-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        text_entity = self.hass.data[DOMAIN][self._entry_id]["key_name_texts"].get(self._device)
        key_name = (text_entity._attr_native_value or "").strip().lower() if text_entity else ""
        if not key_name:
            return
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/key/delete",
            json.dumps({"device": self._device, "key": key_name}),
        )
        if text_entity:
            text_entity.clear()


class RenameButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, device_name: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._entry_id = entry_id
        self._attr_name = f"{device_name.replace('_', ' ').title()} Rename Key"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_rename"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:rename-box"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        old_text = entry_data["key_name_texts"].get(self._device)
        new_text = entry_data["rename_target_texts"].get(self._device)
        old_name = (old_text._attr_native_value or "").strip().lower() if old_text else ""
        new_name = (new_text._attr_native_value or "").strip().lower() if new_text else ""
        if not old_name or not new_name:
            return
        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/key/rename",
            json.dumps({"device": self._device, "old": old_name, "new": new_name}),
        )
        if old_text:
            old_text.clear()
        if new_text:
            new_text.clear()


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
        self._attr_name = f"{device_name.replace('_', ' ').title()} {key}"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
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


class RegisterMultiPressButton(ButtonEntity):
    def __init__(self, hass: HomeAssistant, prefix: str, device_name: str, entry_id: str) -> None:
        self.hass = hass
        self._prefix = prefix
        self._device = device_name
        self._entry_id = entry_id
        self._attr_name = f"{device_name.replace('_', ' ').title()} Virtual Key Register"
        self._attr_unique_id = f"ir_remote_{prefix}_{device_name}_register_multipress"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = "mdi:plus-circle-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"ir_{prefix}_{device_name}")},
            name=device_name.replace("_", " ").title(),
            model="ANAVI IR pHAT",
            manufacturer="ANAVI",
        )

    async def async_press(self) -> None:
        entry_data = self.hass.data[DOMAIN][self._entry_id]
        name_text = entry_data["multipress_name_texts"].get(self._device)
        source_text = entry_data["multipress_source_texts"].get(self._device)
        count_num = entry_data["multipress_count_numbers"].get(self._device)
        delay_num = entry_data["multipress_delay_numbers"].get(self._device)

        name = (name_text._attr_native_value or "").strip().lower() if name_text else ""
        source = (source_text._attr_native_value or "").strip().lower() if source_text else ""
        count = int(count_num._attr_native_value) if count_num else 2
        delay_ms = int(delay_num._attr_native_value) if delay_num else 300

        _LOGGER.debug(
            "RegisterMultiPress: device=%s name=%r source=%r count=%s delay_ms=%s",
            self._device, name, source, count, delay_ms,
        )

        if not name or not source:
            _LOGGER.warning(
                "RegisterMultiPress aborted: name=%r source=%r — fill both fields before pressing",
                name, source,
            )
            return

        await mqtt.async_publish(
            self.hass,
            f"{self._prefix}/virtual_key/create",
            json.dumps({"device": self._device, "name": name, "key": source, "repeat": count, "delay_ms": delay_ms}),
        )
        _LOGGER.debug("RegisterMultiPress: published to %s/virtual_key/create", self._prefix)

        if name_text:
            name_text.clear()
        if source_text:
            source_text.clear()


