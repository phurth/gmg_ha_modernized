"""Green Mountain Grill - Home Assistant Climate Integration."""

import logging
from typing import List
from .gmg.grill import grill as GMGGrillObject

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import TEMP_FAHRENHEIT, ATTR_TEMPERATURE

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up GMG grill platform."""
    _LOGGER.warning("Setting up GMG grill platform...")

    ip = config.get("host")
    gmg = GMGGrillObject(ip)

    try:
        _LOGGER.warning("Attempting initial connection to GMG grill at %s", ip)
        status = gmg.status()
        _LOGGER.warning("Initial status from grill: %s", status)
    except Exception as e:
        _LOGGER.error("Failed to reach GMG grill at %s: %s", ip, e)
        return

    entities = [GMGGrillClimate(gmg)]
    add_entities(entities)


class GMGGrillClimate(ClimateEntity):
    """A basic GMG grill climate entity."""

    def __init__(self, grill):
        _LOGGER.warning("GMGGrillClimate __init__ called")
        self._grill = grill
        self._state = {}
        self._attr_name = self._grill._serial_number
        self._attr_unique_id = self._grill._serial_number

        self.update()

    @property
    def should_poll(self) -> bool:
        return True

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

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
        return HVAC_MODE_HEAT if self._state.get("on") else HVAC_MODE_OFF

    @property
    def hvac_modes(self) -> List[str]:
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]

    @property
    def min_temp(self):
        return 150

    @property
    def max_temp(self):
        return 500

    def set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.warning("Set temp requested: %s", temp)
        if temp:
            try:
                self._grill.set_temp(int(temp))
                _LOGGER.warning("Set temp to %s", temp)
            except Exception as e:
                _LOGGER.error("Failed to set temp: %s", e)

    def update(self):
        _LOGGER.warning("GMGGrillClimate.update() called")
        try:
            self._state = self._grill.status()
            _LOGGER.warning("Updated state: %s", self._state)
        except Exception as e:
            _LOGGER.error("Update failed: %s", e)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up climate platform from config entry."""
    config = {
        "host": "192.168.1.190",  # 🔧 Replace with your grill's IP
    }

    await hass.async_add_executor_job(
        setup_platform, hass, config, async_add_entities
    )
