"""GMG integration."""

from homeassistant.core import HomeAssistant

DOMAIN = "gmg"

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Legacy fallback: manually load climate platform."""
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform("climate", DOMAIN, {}, config)
    )
    return True
