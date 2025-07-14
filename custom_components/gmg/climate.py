"""Green Mountain Grill integration."""

import logging
from typing import List
from .gmg.grill import grill
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_FAN_ONLY,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.const import ATTR_TEMPERATURE, TEMP_FAHRENHEIT

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the GMG grill using hardcoded IP."""
    _LOGGER.debug("Setting up GMG with host: %s", config.get("host"))

    ip = config.get("host")
    grill_name = config.get("grill_name", "GMG Grill")

    my_grill = grill(ip)

    try:
        state = my_grill.status()
        _LOGGER.debug("Initial grill state: %s", state)
    except Exception as e:
        _LOGGER.error("Failed to connect to GMG grill at %s: %s", ip, e)
        return

    entities = [GmgGrill(my_grill)]
    for count in range(1, 3):  # probe 1 and 2
        entities.append(GmgGrillProbe(my_grill, count))

    add_entities(entities)


class GmgGrill(ClimateEntity):
    """Representation of a Green Mountain Grill smoker."""

    def __init__(self, grill_obj) -> None:
        self._grill = grill_obj
        self._unique_id = f"{self._grill._serial_number}"
        self._state = {}
        self.update()

    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None or temperature == self._state.get('grill_set_temp'):
            return

        if self._state.get('on') == 0:
            _LOGGER.warning("Grill is off; cannot set temperature.")
            return

        if self._state.get('temp', 0) < 145:
            _LOGGER.warning("Grill must be above 150°F to set temperature. Current: %s", self._state.get('temp'))
            return

        try:
            self._grill.set_temp(int(temperature))
            _LOGGER.debug("Set grill temp to %s", temperature)
        except Exception as e:
            _LOGGER.error("Error setting grill temperature: %s", e)

    def set_hvac_mode(self, hvac_mode: str) -> None:
        try:
            if hvac_mode == HVAC_MODE_HEAT:
                self._grill.power_on()
            elif hvac_mode == HVAC_MODE_FAN_ONLY:
                self._grill.power_on_cool()
            elif hvac_mode == HVAC_MODE_OFF:
                self._grill.power_off()
            else:
                _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
        except Exception as e:
            _LOGGER.error("Error setting HVAC mode: %s", e)

        self.update()

    def turn_off(self):
        return self._grill.power_off()

    def update(self) -> None:
        _LOGGER.warning("GmgGrill.update() called")
    
        try:
            self._state = self._grill.status()
            _LOGGER.warning("Grill state: %s", self._state)
        except Exception as e:
            _LOGGER.error("Failed to update grill state: %s", e)

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def icon(self):
        return "mdi:grill"

    @property
    def hvac_modes(self) -> List[str]:
        return [HVAC_MODE_HEAT, HVAC_MODE_FAN_ONLY, HVAC_MODE_OFF]

    @property
    def hvac_mode(self):
        mode = self._state.get("on")
        if mode == 1:
            return HVAC_MODE_HEAT
        elif mode == 2:
            return HVAC_MODE_FAN_ONLY
        return HVAC_MODE_OFF

    @property
    def name(self):
        return self._unique_id

    @property
    def temperature_unit(self):
        return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        return self._state.get("temp")

    @property
    def target_temperature_step(self):
        return 1

    @property
    def target_temperature(self):
        return self._state.get("grill_set_temp")

    @property
    def max_temp(self):
        return self._grill.MAX_TEMP_F

    @property
    def min_temp(self):
        return self._grill.MIN_TEMP_F

    @property
    def unique_id(self):
        return self._unique_id


class GmgGrillProbe(ClimateEntity):
    """Representation of a GMG food probe."""

    def __init__(self, grill_obj, probe_count) -> None:
        self._grill = grill_obj
        self._probe_count = probe_count
        self._unique_id = f"{self._grill._serial_number}_probe_{probe_count}"
        self._state = {}
        self.update()

    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        try:
            self._grill.set_temp_probe(int(temperature), self._probe_count)
        except Exception as e:
            _LOGGER.error("Error setting probe temperature: %s", e)

    def update(self) -> None:
        _LOGGER.warning("GmgGrillProbe.update() called (probe %s)", self._probe_count)
    
        try:
            self._state = self._grill.status()
            _LOGGER.warning("Probe %s state: %s", self._probe_count, self._state)
        except Exception as e:
            _LOGGER.error("Failed to update probe state: %s", e)


    @property
    def hvac_modes(self) -> List[str]:
        return [HVAC_MODE_OFF]

    @property
    def hvac_mode(self):
        temp = self._state.get(f"probe{self._probe_count}_temp", 89)
        if self._state.get("on") == 1 and temp != 89:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    @property
    def supported_features(self):
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def icon(self):
        return "mdi:thermometer-lines"

    @property
    def name(self):
        return self._unique_id

    @property
    def temperature_unit(self):
        return TEMP_FAHRENHEIT

    @property
    def current_temperature(self):
        return self._state.get(f"probe{self._probe_count}_temp")

    @property
    def target_temperature_step(self):
        return 1

    @property
    def target_temperature(self):
        return self._state.get(f"probe{self._probe_count}_set_temp")

    @property
    def max_temp(self):
        return self._grill.MAX_TEMP_F_PROBE

    @property
    def min_temp(self):
        return self._grill.MIN_TEMP_F_PROBE

    @property
    def unique_id(self):
        return self._unique_id


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up climate platform from config entry."""
    config = {
        "host": "192.168.1.190",  # replace with your actual grill IP
        "grill_name": "GMG12301304",
    }

    await hass.async_add_executor_job(
        setup_platform, hass, config, async_add_entities
    )
