from homeassistant.config_entries import ConfigEntry, async_setup_platforms, async_forward_entry_unload
from homeassistant.core import HomeAssistant

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GMG from a config entry."""
    await async_forward_entry_setup(hass, config_entry, "climate")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload GMG config entry."""
    return await async_forward_entry_unload(hass, entry, "climate")
