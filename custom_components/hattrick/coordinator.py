"""DataUpdateCoordinator per l'integrazione Hattrick."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HattrickApiError, HattrickAuthError, HattrickCHPPClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import Economy, HattrickData, Team, TeamMood

_LOGGER = logging.getLogger(__name__)


class HattrickDataUpdateCoordinator(DataUpdateCoordinator[HattrickData]):
    """Scarica i file CHPP base e assembla il modello dati HattrickData."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: HattrickCHPPClient,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Inizializza il coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> HattrickData:
        """Scarica i file base e costruisce il modello dati."""
        try:
            team_root = await self.client.async_get_file(self.hass, "teamdetails")
            mood_root = await self.client.async_get_file(self.hass, "team")
            economy_root = await self.client.async_get_file(self.hass, "economy")
        except HattrickAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="auth_error"
            ) from err
        except HattrickApiError as err:
            raise UpdateFailed(str(err)) from err

        return HattrickData(
            team=Team.from_xml(team_root),
            mood=TeamMood.from_xml(mood_root),
            economy=Economy.from_xml(economy_root),
        )
