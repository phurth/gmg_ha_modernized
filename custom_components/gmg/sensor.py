import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the GMG probe sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([
        GMGProbeSensor(coordinator, "probe1_temp", "Probe 1 Temperature"),
        GMGProbeSensor(coordinator, "probe2_temp", "Probe 2 Temperature"),
    ])


class GMGProbeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

    def __init__(self, coordinator, state_key, name):
        super().__init__(coordinator)
        self._state_key = state_key
        self._attr_name = name
        serial = coordinator.grill._serial_number or coordinator.grill._ip
        self._attr_unique_id = f"{serial}_{state_key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(self._state_key)
