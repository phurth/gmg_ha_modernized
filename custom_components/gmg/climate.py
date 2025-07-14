import logging
from typing import List
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .gmg import grill as GMGGrillObject

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the GMG climate platform."""
    host = config_entry.data["host"]
    gmg = GMGGrillObject(hass, host)

    try:
        state = await gmg.status()
        _LOGGER.info("Connected to GMG grill at %s: %s", host, state)
    except Exception as e:
        _LOGGER.error("Failed to connect to GMG grill at %s: %s", host, e)
        return

    async_add_entities([GMGGrillClimate(gmg)])

class GMGGrillClimate(ClimateEntity):
    def __init__(self, grill):
        self._grill = grill
        self._state = {}
        self._attr_name = self._grill._serial_number
        self._attr_unique_id = self._grill._serial_number
        self._attr_should_poll = True  # Enable polling
        self._attr_update_interval = 30  # Update every 30 seconds
        _LOGGER.debug("Initializing GMGGrillClimate for %s", self._attr_unique_id)

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def temperature_unit(self):
        return UnitOfTemperature.FAHRENHEIT

    @property
    def current_temperature(self):
        value = self._state.get("temp")
        _LOGGER.debug("Accessing current_temperature for %s: %s", self._attr_unique_id, value)
        return value

    @property
    def target_temperature(self):
        value = self._state.get("grill_set_temp")
        _LOGGER.debug("Accessing target_temperature for %s: %s", self._attr_unique_id, value)
        return value

    @property
    def hvac_mode(self):
        state = HVACMode.HEAT if self._state.get("on") else HVACMode.OFF
        _LOGGER.debug("Accessing hvac_mode for %s: %s (on: %s)", self._attr_unique_id, state, self._state.get("on"))
        return state

    @property
    def hvac_modes(self) -> List[str]:
        return [HVACMode.HEAT, HVACMode.OFF]

    @property
    def min_temp(self):
        return 150

    @property
    def max_temp(self):
        return 500

    async def set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp:
            try:
                await self._grill.set_temp(int(temp))
                _LOGGER.debug("Set grill temp to %s for %s", temp, self._attr_unique_id)
                await self.async_update()
            except Exception as e:
                _LOGGER.error("Failed to set temp for %s: %s", self._attr_unique_id, e)

    async def async_update(self):
        _LOGGER.debug("Updating GMGGrillClimate for %s at %s", self._attr_unique_id, self._grill._ip)
        try:
            self._state = await self._grill.status()
            _LOGGER.debug("Grill update for %s: %s", self._attr_unique_id, self._state)
        except Exception as e:
            _LOGGER.error("Update failed for %s: %s", self._attr_unique_id, e)
            self._state = {'on': 0, 'temp': None, 'grill_set_temp': None}
