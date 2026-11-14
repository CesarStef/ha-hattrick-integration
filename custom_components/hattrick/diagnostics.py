"""Diagnostics redatte per l'integrazione Hattrick.

Mai includere token, secret o password nel dump: `_redact` maschera ricorsivamente
ogni chiave il cui nome contiene "secret", "token" o "password".
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import HattrickDataUpdateCoordinator

REDACTED = "***"
_SENSITIVE_MARKERS = ("secret", "token", "password")


def _redact(value: Any) -> Any:
    """Maschera ricorsivamente i valori sensibili in dict/liste."""
    if isinstance(value, dict):
        return {
            key: (
                REDACTED if any(m in str(key).lower() for m in _SENSITIVE_MARKERS) else _redact(val)
            )
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Dump diagnostico della config entry, con credenziali redatte."""
    coordinator: HattrickDataUpdateCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    data = coordinator.data if coordinator is not None else None
    return {
        "entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
            "data": _redact(dict(entry.data)),
            "options": _redact(dict(entry.options)),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success
            if coordinator is not None
            else None,
            "update_interval": (
                str(coordinator.update_interval) if coordinator is not None else None
            ),
            "enabled_files": list(coordinator.enabled_files) if coordinator is not None else [],
            "matchday": coordinator.matchday if coordinator is not None else None,
        },
        "data": {
            "team_id": data.team.team_id,
            "team_name": data.team.team_name,
            "league": data.team.league_name,
            "cash": data.economy.cash,
            "players": len(data.players.players) if data.players else 0,
            "position": data.league.position if data.league else None,
            "last_match": data.matches.last_match.score(data.team.team_id)
            if data.matches and data.matches.last_match
            else None,
            "next_match_id": data.matches.next_match.match_id
            if data.matches and data.matches.next_match
            else None,
            "has_match_details": data.match_details is not None,
            "has_match_lineup": data.match_lineup is not None,
        }
        if data is not None
        else None,
    }
