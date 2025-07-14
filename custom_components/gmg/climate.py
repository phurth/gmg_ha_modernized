import logging
from typing import List
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import TEMP_FAHRENHEIT, ATTR_TEMPERATURE

from .const import DOMAIN
from .gmg import grill as GMGGrillObject

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
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
        self._attr_should_poll = True
        self.update()

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE

    @property
    def temperature_unit(self):
        return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        return self._state.get("temp")

    @property
    def target_temperature(self):
        return self._state.get("grill_set_temp")

    @property
    def hvac_mode(self):
        return HVACMode.HEAT if self._state.get("on") else HVACMode.OFF

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
                _LOGGER.debug("Set grill temp to %s", temp)
            except Exception as e:
                _LOGGER.error("Failed to set temp: %s", e)

    async def update(self):
        try:
            self._state = await self._grill.status()
            _LOGGER.debug("Grill update: %s", self._state)
        except Exception as e:
            _LOGGER.error("Update failed: %s", e)
