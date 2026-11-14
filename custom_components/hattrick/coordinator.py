"""DataUpdateCoordinator per l'integrazione Hattrick."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HattrickApiError, HattrickAuthError, HattrickCHPPClient
from .const import DEFAULT_ENABLED_FILES, DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import (
    Arena,
    Club,
    Economy,
    HattrickData,
    LeagueDetails,
    Matches,
    Players,
    Team,
    TeamMood,
    Training,
    TrainingSummary,
    World,
)

_LOGGER = logging.getLogger(__name__)

# File sempre scaricati: servono per device, unique_id e sensor base.
BASE_FILES: tuple[str, ...] = ("teamdetails", "team", "economy")

# Parser per i file opzionali del ciclo standard.
OPTIONAL_PARSERS = {
    "club": Club,
    "players": Players,
    "training": Training,
    "trainingsummary": TrainingSummary,
    "leaguedetails": LeagueDetails,
    "matches": Matches,
    "arenadetails": Arena,
    "worlddetails": World,
}


class HattrickDataUpdateCoordinator(DataUpdateCoordinator[HattrickData]):
    """Scarica i file CHPP abilitati e assembla il modello dati HattrickData."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: HattrickCHPPClient,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
        enabled_files: tuple[str, ...] | list[str] = DEFAULT_ENABLED_FILES,
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
        self.enabled_files = tuple(enabled_files)

    async def _async_update_data(self) -> HattrickData:
        """Scarica i file abilitati in parallelo e costruisce il modello dati."""
        files = list(BASE_FILES) + [f for f in self.enabled_files if f not in BASE_FILES]
        try:
            roots = await asyncio.gather(
                *(self.client.async_get_file(self.hass, file) for file in files)
            )
        except HattrickAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="auth_error"
            ) from err
        except HattrickApiError as err:
            raise UpdateFailed(str(err)) from err

        data_by_file = dict(zip(files, roots, strict=True))
        optional: dict[str, object] = {}
        for file, parser in OPTIONAL_PARSERS.items():
            if file in data_by_file:
                optional[file] = parser.from_xml(data_by_file[file])

        return HattrickData(
            team=Team.from_xml(data_by_file["teamdetails"]),
            mood=TeamMood.from_xml(data_by_file["team"]),
            economy=Economy.from_xml(data_by_file["economy"]),
            club=optional.get("club"),  # type: ignore[arg-type]
            players=optional.get("players"),  # type: ignore[arg-type]
            training=optional.get("training"),  # type: ignore[arg-type]
            training_summary=optional.get("trainingsummary"),  # type: ignore[arg-type]
            league=optional.get("leaguedetails"),  # type: ignore[arg-type]
            matches=optional.get("matches"),  # type: ignore[arg-type]
            arena=optional.get("arenadetails"),  # type: ignore[arg-type]
            world=optional.get("worlddetails"),  # type: ignore[arg-type]
        )
