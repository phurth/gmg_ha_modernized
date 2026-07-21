"""GMG integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import GMGCoordinator
from .gmg import grill as GMGGrill

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the GMG integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up GMG from a config entry."""
    host = entry.data["host"]
    grill = GMGGrill(hass, host)

    # Identity comes from the serial. Persist it once so entities keep a stable
    # unique_id even across restarts while the grill is unplugged (offline).
    serial = entry.data.get("serial")
    if serial:
        grill._serial_number = serial
    else:
        try:
            serial = await grill.serial()
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning("Could not read serial from GMG grill at %s: %s", host, e)
        if serial:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, "serial": serial}
            )

    coordinator = GMGCoordinator(hass, grill)
    # Prime the first poll but don't fail setup if the grill is currently
    # unreachable: entities come up 'unavailable' and recover when it's back.
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload GMG config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
