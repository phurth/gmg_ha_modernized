import logging

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """Set up the GMG climate entity from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([GMGGrillClimate(coordinator)])


class GMGGrillClimate(CoordinatorEntity, ClimateEntity):
    _attr_has_entity_name = True
    _attr_name = None  # entity takes the device name
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_target_temperature_step = 1
    _attr_icon = "mdi:grill"
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator):
        super().__init__(coordinator)
        grill = coordinator.grill
        serial = grill._serial_number or grill._ip
        self._attr_unique_id = serial
        self._attr_min_temp = grill.MIN_TEMP_F
        self._attr_max_temp = grill.MAX_TEMP_F
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=serial,
            manufacturer="Green Mountain Grills",
            model="Wi-Fi Grill",
        )

    @property
    def _data(self):
        return self.coordinator.data or {}

    @property
    def current_temperature(self):
        return self._data.get("temp")

    @property
    def target_temperature(self):
        return self._data.get("grill_set_temp")

    @property
    def hvac_mode(self):
        return HVACMode.HEAT if self._data.get("on") else HVACMode.OFF

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        try:
            await self.coordinator.grill.set_temp(int(temp))
        except Exception as e:
            _LOGGER.error("Failed to set temp for %s: %s", self._attr_unique_id, e)
            return
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.HEAT:
            await self.async_turn_on()
        elif hvac_mode == HVACMode.OFF:
            await self.async_turn_off()

    async def async_turn_on(self):
        try:
            await self.coordinator.grill.power_on()
        except Exception as e:
            _LOGGER.error("Failed to power on %s: %s", self._attr_unique_id, e)
            return
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self):
        try:
            await self.coordinator.grill.power_off()
        except Exception as e:
            _LOGGER.error("Failed to power off %s: %s", self._attr_unique_id, e)
            return
        await self.coordinator.async_request_refresh()
