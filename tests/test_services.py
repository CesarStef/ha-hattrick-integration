"""Test dei servizi hattrick.get_match_details e hattrick.get_player."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hattrick.api import HattrickApiError
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
        self.posts: list[tuple[str, str]] = []
        self.post_error: Exception | None = None

    async def async_get_file(self, hass, file: str, **params):
        self.calls.append((file, params))
        return ET.fromstring((FIXTURES_DIR / FILES[file]).read_text(encoding="utf-8"))

    async def async_post_file(self, hass, file: str, body: str, **params):
        if self.post_error is not None:
            raise self.post_error
        self.posts.append((file, body))
        return ET.fromstring(
            '<?xml version="1.0"?><HattrickData><FileName>matchorders</FileName>'
            "<Version>1.0</Version></HattrickData>"
        )


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
    assert not hass.services.has_service(DOMAIN, "set_match_orders")
    assert not hass.services.has_service(DOMAIN, "refresh")


async def test_set_match_orders_posts_xml_and_returns_success(hass: HomeAssistant):
    entry = await _setup_entry(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    response = await hass.services.async_call(
        DOMAIN,
        "set_match_orders",
        {
            "match_id": 9002,
            "tactic_type": 1,
            "tactic_skill": 5,
            "attitude": 1,
            "captain_id": 1001,
            "set_pieces_taker_id": 1003,
            "penalty_takers": [1003, 1002],
            "lineup": [
                {"player_id": 1001, "position_code": 100},
                {"player_id": 1002, "position_code": 101},
            ],
        },
        blocking=True,
        return_response=True,
    )
    assert response == {"success": True, "match_id": 9002}
    assert len(coordinator.client.posts) == 1
    file, body = coordinator.client.posts[0]
    assert file == "matchorders"
    assert "<MatchID>9002</MatchID>" in body
    assert "<TacticType>1</TacticType>" in body
    assert "<TacticSkill>5</TacticSkill>" in body
    assert "<Attitude>1</Attitude>" in body
    assert "<CaptainID>1001</CaptainID>" in body
    assert "<SetPiecesTakerID>1003</SetPiecesTakerID>" in body
    assert "<PenaltyTakerID>1003</PenaltyTakerID>" in body
    assert "<PenaltyTakerID>1002</PenaltyTakerID>" in body
    assert "<PlayerID>1001</PlayerID><PositionCode>100</PositionCode>" in body
    assert "<PlayerID>1002</PlayerID><PositionCode>101</PositionCode>" in body
    # il servizio ha forzato un refresh del coordinator
    assert any(file == "teamdetails" for file, _ in coordinator.client.calls[1:])


async def test_set_match_orders_minimal_body(hass: HomeAssistant):
    entry = await _setup_entry(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    response = await hass.services.async_call(
        DOMAIN,
        "set_match_orders",
        {"match_id": 9002},
        blocking=True,
        return_response=True,
    )
    assert response["success"] is True
    _, body = coordinator.client.posts[0]
    assert body == "<MatchOrders><MatchID>9002</MatchID></MatchOrders>"


async def test_set_match_orders_api_error_raises(hass: HomeAssistant):
    entry = await _setup_entry(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.client.post_error = HattrickApiError("permesso negato")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "set_match_orders",
            {"match_id": 9002},
            blocking=True,
            return_response=True,
        )


async def test_refresh_triggers_coordinator_update(hass: HomeAssistant):
    entry = await _setup_entry(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    calls_before = len(coordinator.client.calls)
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    await hass.async_block_till_done()
    assert len(coordinator.client.calls) > calls_before


async def test_refresh_with_config_entry(hass: HomeAssistant):
    entry = await _setup_entry(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    calls_before = len(coordinator.client.calls)
    await hass.services.async_call(
        DOMAIN, "refresh", {"config_entry": entry.entry_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert len(coordinator.client.calls) > calls_before


async def test_refresh_unknown_config_entry_raises(hass: HomeAssistant):
    await _setup_entry(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "refresh", {"config_entry": "inesistente"}, blocking=True
        )
