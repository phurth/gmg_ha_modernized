from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GMG from a config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "climate")
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload GMG config entry."""
    return await hass.config_entries.async_forward_entry_unload(entry, "climate")

