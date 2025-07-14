import logging
from typing import List
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN
from .gmg import grill as GMGGrillObject

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the GMG sensor platform."""
    host = config_entry.data["host"]
    gmg = GMGGrillObject(hass, host)

    try:
        state = await gmg.status()
        _LOGGER.info("Connected to GMG grill for sensors at %s: %s", host, state)
    except Exception as e:
        _LOGGER.error("Failed to connect to GMG grill for sensors at %s: %s", host, e)
        return

    async_add_entities([
        GMGProbeSensor(gmg, "probe1_temp", "Probe 1 Temperature"),
        GMGProbeSensor(gmg, "probe2_temp", "Probe 2 Temperature")
    ])

class GMGProbeSensor(SensorEntity):
    def __init__(self, grill, state_key, name):
        self._grill = grill
        self._state_key = state_key
        self._attr_name = f"{self._grill._serial_number} {name}"
        self._attr_unique_id = f"{self._grill._serial_number}_{state_key}"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
        self._attr_should_poll = True  # Enable polling
        self._attr_update_interval = 30  # Update every 30 seconds
        self._state = {}
        _LOGGER.debug("Initializing GMGProbeSensor for %s", self._attr_unique_id)

    @property
    def native_value(self):
        value = self._state.get(self._state_key)
        _LOGGER.debug("Accessing native_value for %s: %s", self._attr_unique_id, value)
        return value

    async def async_update(self):
        _LOGGER.debug("Updating GMGProbeSensor for %s at %s", self._attr_unique_id, self._grill._ip)
        try:
            self._state = await self._grill.status()
            _LOGGER.debug("Sensor update for %s: %s", self._state_key, self._state)
        except Exception as e:
            _LOGGER.error("Sensor update failed for %s: %s", self._state_key, e)
            self._state = {'probe1_temp': None, 'probe2_temp': None}
