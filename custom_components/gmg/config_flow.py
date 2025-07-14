from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN

DATA_SCHEMA = vol.Schema({
    vol.Required("host"): str,
})

class GMGConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GMG."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="GMG Grill", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA
        )
