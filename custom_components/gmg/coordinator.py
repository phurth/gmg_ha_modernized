"""DataUpdateCoordinator for Green Mountain Grill."""
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class GMGCoordinator(DataUpdateCoordinator):
    """Polls one grill over UDP and shares the result with all its entities.

    A single poll per interval replaces per-entity polling. When the grill is
    unreachable (commonly: unplugged), the poll fails and `last_update_success`
    goes False, so every entity reports `unavailable` and recovers automatically
    on the next successful poll.
    """

    def __init__(self, hass: HomeAssistant, grill) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.grill = grill

    async def _async_update_data(self):
        try:
            return await self.grill.status()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with GMG grill: {err}") from err
