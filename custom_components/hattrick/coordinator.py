"""DataUpdateCoordinator per l'integrazione Hattrick."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HattrickApiError, HattrickAuthError, HattrickCHPPClient
from .const import (
    DEFAULT_ENABLED_FILES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MATCHDAY_INTERVAL,
    MATCHDAY_WINDOW,
    ON_DEMAND_FILES,
)
from .models import (
    HTT_TIMEZONE,
    Arena,
    Club,
    Economy,
    HattrickData,
    LeagueDetails,
    MatchDetails,
    Matches,
    MatchLineup,
    Players,
    Team,
    TeamMood,
    Training,
    TrainingSummary,
    World,
    htt_to_aware,
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
        matchday: bool = False,
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
        self.base_interval = update_interval
        self.matchday = matchday

    def _auth_issue_id(self) -> str:
        """ID dell'issue (repair) per il token revocato di questa entry."""
        return f"token_revocato_{self.config_entry.entry_id}"

    def _create_auth_issue(self) -> None:
        """Crea un repair fixable: l'utente puo ri-autorizzare l'app da HA."""
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            self._auth_issue_id(),
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="token_revocato",
            issue_domain=DOMAIN,
            data={"entry_id": self.config_entry.entry_id},
            translation_placeholders={"team": self.config_entry.title},
        )

    def _delete_auth_issue(self) -> None:
        """Rimuove il repair quando l'aggiornamento torna a funzionare."""
        ir.async_delete_issue(self.hass, DOMAIN, self._auth_issue_id())

    async def _async_update_data(self) -> HattrickData:
        """Scarica i file abilitati in parallelo e costruisce il modello dati."""
        files = [
            f
            for f in (list(BASE_FILES) + [f for f in self.enabled_files if f not in BASE_FILES])
            if f not in ON_DEMAND_FILES
        ]
        try:
            roots = await asyncio.gather(
                *(self.client.async_get_file(self.hass, file) for file in files)
            )
        except HattrickAuthError as err:
            self._create_auth_issue()
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

        data = HattrickData(
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
        await self._async_fetch_on_demand(data)
        self._apply_matchday_interval(data)
        self._delete_auth_issue()
        return data

    async def _async_fetch_on_demand(self, data: HattrickData) -> None:
        """Scarica matchdetails/matchlineup dell'ultima partita, se abilitati."""
        last = data.matches.last_match if data.matches else None
        if last is None:
            return
        try:
            if "matchdetails" in self.enabled_files:
                root = await self.client.async_get_file(
                    self.hass, "matchdetails", matchID=last.match_id
                )
                data.match_details = MatchDetails.from_xml(root)
            if "matchlineup" in self.enabled_files:
                root = await self.client.async_get_file(
                    self.hass, "matchlineup", matchID=last.match_id
                )
                data.match_lineup = MatchLineup.from_xml(root, data.team.team_id)
        except HattrickAuthError as err:
            self._create_auth_issue()
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="auth_error"
            ) from err
        except HattrickApiError as err:
            raise UpdateFailed(str(err)) from err

    def _apply_matchday_interval(self, data: HattrickData) -> None:
        """Riduce l'intervallo a 5 min dentro la finestra di partita (se matchday attivo)."""
        if not self.matchday:
            return
        nxt = data.matches.next_match if data.matches else None
        if nxt is None or nxt.date is datetime.min:
            self.update_interval = self.base_interval
            return
        now_htt = datetime.now(HTT_TIMEZONE)
        kickoff = htt_to_aware(nxt.date)
        if abs(kickoff - now_htt) <= MATCHDAY_WINDOW:
            self.update_interval = MATCHDAY_INTERVAL
        else:
            self.update_interval = self.base_interval
