"""GMG integration for Home Assistant."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the GMG integration."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GMG from a config entry."""
    from . import climate  # Import climate module here to avoid blocking during init
    await climate.async_setup_entry(hass, entry, hass.helpers.entity_platform.async_add_entities)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload GMG config entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["climate"])
