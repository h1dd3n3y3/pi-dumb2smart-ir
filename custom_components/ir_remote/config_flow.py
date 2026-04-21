import asyncio
import json

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.core import callback

from .const import CONF_TOPIC_PREFIX, DEFAULT_TOPIC_PREFIX, DOMAIN


class IRRemoteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            prefix = user_input[CONF_TOPIC_PREFIX]

            if not self.hass.services.has_service("mqtt", "publish"):
                errors["base"] = "mqtt_not_configured"
            else:
                received = asyncio.Event()
                payload_holder = {}

                @callback
                def on_devices(msg):
                    try:
                        payload_holder["devices"] = json.loads(msg.payload)
                        received.set()
                    except Exception:
                        pass

                unsub = await mqtt.async_subscribe(
                    self.hass, f"{prefix}/devices", on_devices
                )
                try:
                    await asyncio.wait_for(received.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    errors["base"] = "pi_offline"
                finally:
                    unsub()

                if not errors:
                    if not payload_holder.get("devices"):
                        errors["base"] = "no_devices"
                    else:
                        await self.async_set_unique_id(prefix)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=f"IR Remote ({prefix})",
                            data=user_input,
                        )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_TOPIC_PREFIX, default=DEFAULT_TOPIC_PREFIX): str,
            }),
            errors=errors,
        )
