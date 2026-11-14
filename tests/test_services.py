"""Test dei servizi hattrick.get_match_details e hattrick.get_player."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hattrick.const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_SECRET,
    CONF_CONSUMER_KEY,
    CONF_CONSUMER_SECRET,
    DOMAIN,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

FILES = {
    "teamdetails": "teamdetails.xml",
    "team": "team.xml",
    "club": "club.xml",
    "economy": "economy.xml",
    "players": "players.xml",
    "training": "training.xml",
    "trainingsummary": "trainingsummary.xml",
    "leaguedetails": "leaguedetails.xml",
    "matches": "matches.xml",
    "arenadetails": "arenadetails.xml",
    "worlddetails": "worlddetails.xml",
    "matchdetails": "matchdetails.xml",
    "matchlineup": "matchlineup.xml",
}

ENTRY_DATA = {
    CONF_CONSUMER_KEY: "ck",
    CONF_CONSUMER_SECRET: "cs",
    CONF_ACCESS_TOKEN: "at",
    CONF_ACCESS_TOKEN_SECRET: "ats",
}


class MockCHPPClient:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def async_get_file(self, hass, file: str, **params):
        self.calls.append((file, params))
        return ET.fromstring((FIXTURES_DIR / FILES[file]).read_text(encoding="utf-8"))


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1234567", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    with mock.patch("custom_components.hattrick.HattrickCHPPClient", MockCHPPClient):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_get_match_details_returns_response(hass: HomeAssistant):
    await _setup_entry(hass)
    response = await hass.services.async_call(
        DOMAIN,
        "get_match_details",
        {"match_id": 9001},
        blocking=True,
        return_response=True,
    )
    assert response["match_id"] == 9001
    assert response["home_team"]["goals"] == 3
    assert response["away_team"]["name"] == "Avversari FC"
    assert response["possession_home"] == 55
    assert response["home_ratings"]["CC"] == 9
    assert response["weather"] == "Sunny"


async def test_get_player_returns_response(hass: HomeAssistant):
    await _setup_entry(hass)
    response = await hass.services.async_call(
        DOMAIN,
        "get_player",
        {"player_id": 1002},
        blocking=True,
        return_response=True,
    )
    assert response["player_id"] == 1002
    assert response["nome"] == "Luca Il Muro Bianchi"
    assert response["ruolo"] == "difensore"
    assert response["skill"]["difensore"] == 8
    assert response["infortunio_settimane"] == 2


async def test_get_player_not_found_raises(hass: HomeAssistant):
    await _setup_entry(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "get_player",
            {"player_id": 999999},
            blocking=True,
            return_response=True,
        )


async def test_services_removed_on_unload(hass: HomeAssistant):
    entry = await _setup_entry(hass)
    assert hass.services.has_service(DOMAIN, "get_match_details")
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "get_match_details")
    assert not hass.services.has_service(DOMAIN, "get_player")
