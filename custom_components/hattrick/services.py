"""Servizi (azioni) del dominio hattrick con risposta (supports_response)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import HattrickApiError, HattrickAuthError
from .const import DOMAIN
from .coordinator import HattrickDataUpdateCoordinator
from .models import TACTIC_TYPES, MatchDetails, Players

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_MATCH_DETAILS = "get_match_details"
SERVICE_GET_PLAYER = "get_player"
SERVICE_SET_MATCH_ORDERS = "set_match_orders"

CONF_MATCH_ID = "match_id"
CONF_PLAYER_ID = "player_id"
CONF_CONFIG_ENTRY = "config_entry"

GET_MATCH_DETAILS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MATCH_ID): cv.positive_int,
        vol.Optional(CONF_CONFIG_ENTRY): str,
    }
)
GET_PLAYER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLAYER_ID): cv.positive_int,
        vol.Optional(CONF_CONFIG_ENTRY): str,
    }
)
SET_MATCH_ORDERS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MATCH_ID): cv.positive_int,
        vol.Optional(CONF_CONFIG_ENTRY): str,
        vol.Optional("tactic_type"): vol.All(vol.Coerce(int), vol.In(list(TACTIC_TYPES))),
        vol.Optional("tactic_skill"): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
        vol.Optional("attitude"): vol.All(vol.Coerce(int), vol.In([-1, 0, 1])),
        vol.Optional("captain_id"): cv.positive_int,
        vol.Optional("set_pieces_taker_id"): cv.positive_int,
        vol.Optional("penalty_takers"): vol.All(cv.ensure_list, [cv.positive_int]),
        vol.Optional("lineup"): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required("player_id"): cv.positive_int,
                        vol.Required("position_code"): vol.All(
                            vol.Coerce(int), vol.Range(min=100, max=120)
                        ),
                    }
                )
            ],
        ),
    }
)


def _build_match_orders_xml(data: dict[str, Any]) -> str:
    """Costruisce il corpo XML per matchorders.xml dai dati della chiamata.

    I nomi dei campi seguono la wiki CHPP (da riconfermare): MatchID, TacticType,
    TacticSkill, Attitude, Lineup/Player, CaptainID, SetPiecesTakerID,
    PenaltyTakers.
    """
    parts = ["<MatchOrders>", f"<MatchID>{data[CONF_MATCH_ID]}</MatchID>"]
    if "tactic_type" in data:
        parts.append(f"<TacticType>{data['tactic_type']}</TacticType>")
    if "tactic_skill" in data:
        parts.append(f"<TacticSkill>{data['tactic_skill']}</TacticSkill>")
    if "attitude" in data:
        parts.append(f"<Attitude>{data['attitude']}</Attitude>")
    lineup = data.get("lineup") or []
    if lineup:
        parts.append("<Lineup>")
        for entry in lineup:
            parts.append(
                f"<Player><PlayerID>{entry['player_id']}</PlayerID>"
                f"<PositionCode>{entry['position_code']}</PositionCode></Player>"
            )
        parts.append("</Lineup>")
    if "captain_id" in data:
        parts.append(f"<CaptainID>{data['captain_id']}</CaptainID>")
    if "set_pieces_taker_id" in data:
        parts.append(f"<SetPiecesTakerID>{data['set_pieces_taker_id']}</SetPiecesTakerID>")
    penalty_takers = data.get("penalty_takers") or []
    if penalty_takers:
        parts.append("<PenaltyTakers>")
        for player_id in penalty_takers:
            parts.append(f"<PenaltyTakerID>{player_id}</PenaltyTakerID>")
        parts.append("</PenaltyTakers>")
    parts.append("</MatchOrders>")
    return "".join(parts)


class HattrickServiceError(HomeAssistantError):
    """Errore sollevato dai servizi hattrick."""


def _coordinators(hass: HomeAssistant) -> list[HattrickDataUpdateCoordinator]:
    """Tutti i coordinator attivi (una entry = una squadra)."""
    return [
        value
        for key, value in hass.data.get(DOMAIN, {}).items()
        if key != "services_registered" and isinstance(value, HattrickDataUpdateCoordinator)
    ]


def _coordinator_for(hass: HomeAssistant, call: ServiceCall) -> HattrickDataUpdateCoordinator:
    """Sceglie il coordinator: da `config_entry` se dato, altrimenti il primo."""
    coordinators = _coordinators(hass)
    if not coordinators:
        raise ServiceValidationError("Nessuna squadra Hattrick configurata")
    entry_id = call.data.get(CONF_CONFIG_ENTRY)
    if entry_id:
        for coordinator in coordinators:
            if coordinator.config_entry.entry_id == entry_id:
                return coordinator
        raise ServiceValidationError(f"Config entry Hattrick non trovata: {entry_id}")
    return coordinators[0]


async def async_setup_services(hass: HomeAssistant) -> None:
    """Registra i servizi del dominio (una sola volta)."""
    if hass.data.get(DOMAIN, {}).get("services_registered"):
        return
    hass.data.setdefault(DOMAIN, {})["services_registered"] = True

    async def handle_get_match_details(call: ServiceCall) -> dict[str, Any]:
        """Restituisce i dettagli di una partita (matchdetails.xml)."""
        coordinator = _coordinator_for(hass, call)
        match_id = call.data[CONF_MATCH_ID]
        try:
            root = await coordinator.client.async_get_file(hass, "matchdetails", matchID=match_id)
        except Exception as err:
            raise HattrickServiceError(f"Errore CHPP: {err}") from err
        return MatchDetails.from_xml(root).to_dict()

    async def handle_get_player(call: ServiceCall) -> dict[str, Any]:
        """Restituisce i dati di un giocatore (players.xml?playerID=...)."""
        coordinator = _coordinator_for(hass, call)
        player_id = call.data[CONF_PLAYER_ID]
        try:
            root = await coordinator.client.async_get_file(hass, "players", playerID=player_id)
        except Exception as err:
            raise HattrickServiceError(f"Errore CHPP: {err}") from err
        players = Players.from_xml(root)
        player = next((p for p in players.players if p.player_id == player_id), None)
        if player is None:
            raise ServiceValidationError(f"Giocatore {player_id} non trovato nella rosa")
        return player.to_dict()

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_MATCH_DETAILS,
        handle_get_match_details,
        schema=GET_MATCH_DETAILS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_set_match_orders(call: ServiceCall) -> dict[str, Any]:
        """Invia gli ordini di partita a CHPP (POST matchorders.xml) e refresha."""
        coordinator = _coordinator_for(hass, call)
        match_id = call.data[CONF_MATCH_ID]
        body = _build_match_orders_xml(call.data)
        try:
            await coordinator.client.async_post_file(hass, "matchorders", body)
        except HattrickAuthError as err:
            raise HattrickServiceError(
                "Autorizzazione CHPP mancante o revocata: riesegui la configurazione"
            ) from err
        except HattrickApiError as err:
            raise HattrickServiceError(f"Errore CHPP: {err}") from err
        _LOGGER.info("Ordini partita inviati per match %s", match_id)
        await coordinator.async_request_refresh()
        return {"success": True, "match_id": match_id}

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PLAYER,
        handle_get_player,
        schema=GET_PLAYER_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MATCH_ORDERS,
        handle_set_match_orders,
        schema=SET_MATCH_ORDERS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Rimuove i servizi quando non resta nessuna entry configurata."""
    if _coordinators(hass):
        return
    hass.data.get(DOMAIN, {}).pop("services_registered", None)
    hass.services.async_remove(DOMAIN, SERVICE_GET_MATCH_DETAILS)
    hass.services.async_remove(DOMAIN, SERVICE_GET_PLAYER)
    hass.services.async_remove(DOMAIN, SERVICE_SET_MATCH_ORDERS)
