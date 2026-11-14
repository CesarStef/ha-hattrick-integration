"""Servizi (azioni) del dominio hattrick con risposta (supports_response)."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import HattrickDataUpdateCoordinator
from .models import MatchDetails, Players

_LOGGER = logging.getLogger(__name__)

SERVICE_GET_MATCH_DETAILS = "get_match_details"
SERVICE_GET_PLAYER = "get_player"

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
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_PLAYER,
        handle_get_player,
        schema=GET_PLAYER_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Rimuove i servizi quando non resta nessuna entry configurata."""
    if _coordinators(hass):
        return
    hass.data.get(DOMAIN, {}).pop("services_registered", None)
    hass.services.async_remove(DOMAIN, SERVICE_GET_MATCH_DETAILS)
    hass.services.async_remove(DOMAIN, SERVICE_GET_PLAYER)
