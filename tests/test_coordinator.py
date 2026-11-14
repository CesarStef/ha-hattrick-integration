"""Test del DataUpdateCoordinator (coordinator.py)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hattrick.api import HattrickApiError, HattrickAuthError
from custom_components.hattrick.const import DOMAIN, MATCHDAY_INTERVAL
from custom_components.hattrick.coordinator import HattrickDataUpdateCoordinator
from custom_components.hattrick.models import (
    HTT_TIMEZONE,
    Economy,
    HattrickData,
    Match,
    Matches,
    Team,
    TeamMood,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

ALL_FILES = {
    "teamdetails": "teamdetails.xml",
    "team": "team.xml",
    "economy": "economy.xml",
    "club": "club.xml",
    "players": "players.xml",
    "training": "training.xml",
    "trainingsummary": "trainingsummary.xml",
    "leaguedetails": "leaguedetails.xml",
    "matches": "matches.xml",
    "arenadetails": "arenadetails.xml",
    "worlddetails": "worlddetails.xml",
}


class MockCHPPClient:
    """Client CHPP finto che legge le fixture XML."""

    def __init__(self, files: dict[str, str] | None = None, error: Exception | None = None) -> None:
        self._files = files or ALL_FILES
        self._error = error

    async def async_get_file(self, hass, file: str, **params):
        if self._error is not None:
            raise self._error
        return ET.fromstring((FIXTURES_DIR / self._files[file]).read_text(encoding="utf-8"))


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Squadra di Test",
        unique_id="1234567",
        data={
            "consumer_key": "ck",
            "consumer_secret": "cs",
            "access_token": "at",
            "access_token_secret": "ats",
        },
    )


async def test_coordinator_update_ok(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = HattrickDataUpdateCoordinator(hass, entry, MockCHPPClient())
    data = await coordinator._async_update_data()
    assert data.team.team_name == "Squadra di Test"
    assert data.team.team_id == 7654321
    assert data.mood.morale == "excellent"
    assert data.mood.confidence == "wonderful"
    assert data.economy.cash == 5000000
    assert data.economy.wages == 350000
    assert data.players is not None
    assert len(data.players.players) == 3
    assert data.league is not None
    assert data.league.position == 3
    assert data.matches is not None
    assert data.matches.next_match is not None
    assert data.matches.next_match.match_id == 9002
    assert data.training is not None
    assert data.training.training_type_label == "gioco"
    assert data.training_summary is not None
    assert data.arena is not None
    assert data.arena.total_capacity == 50000
    assert data.club is not None
    assert data.club.fanclub_size == 1500
    assert data.world is not None
    assert data.world.season == 75


async def test_coordinator_enabled_files_subset(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = HattrickDataUpdateCoordinator(
        hass, entry, MockCHPPClient(), enabled_files=["teamdetails", "team", "economy"]
    )
    data = await coordinator._async_update_data()
    assert data.team.team_id == 7654321
    assert data.players is None
    assert data.matches is None
    assert data.world is None


def _match_at(when: datetime) -> Match:
    return Match(
        match_id=1,
        date=when.replace(tzinfo=None),
        match_type=1,
        home_id=8000002,
        home_name="Avversario",
        home_goals=None,
        away_id=7654321,
        away_name="Squadra di Test",
        away_goals=None,
        arena_id=1,
        arena_name="Stadio",
    )


def _data_with_next_match(when: datetime) -> HattrickData:
    team = Team.from_xml(ET.fromstring((FIXTURES_DIR / "teamdetails.xml").read_text()))
    return HattrickData(
        team=team,
        mood=TeamMood(morale="excellent", confidence="wonderful"),
        economy=Economy(cash=1, expected_cash=1, sponsors=1),
        matches=Matches(team_id=team.team_id, team_name=team.team_name, matches=[_match_at(when)]),
    )


async def test_coordinator_matchday_inside_window(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = HattrickDataUpdateCoordinator(
        hass, entry, MockCHPPClient(), update_interval=timedelta(minutes=15), matchday=True
    )
    soon = datetime.now(HTT_TIMEZONE) + timedelta(hours=1)
    coordinator._apply_matchday_interval(_data_with_next_match(soon))
    assert coordinator.update_interval == MATCHDAY_INTERVAL


async def test_coordinator_matchday_outside_window(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = HattrickDataUpdateCoordinator(
        hass, entry, MockCHPPClient(), update_interval=timedelta(minutes=15), matchday=True
    )
    far = datetime.now(HTT_TIMEZONE) + timedelta(days=3)
    coordinator._apply_matchday_interval(_data_with_next_match(far))
    assert coordinator.update_interval == timedelta(minutes=15)


async def test_coordinator_matchday_disabled_keeps_interval(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = HattrickDataUpdateCoordinator(
        hass, entry, MockCHPPClient(), update_interval=timedelta(minutes=15), matchday=False
    )
    soon = datetime.now(HTT_TIMEZONE) + timedelta(hours=1)
    coordinator._apply_matchday_interval(_data_with_next_match(soon))
    assert coordinator.update_interval == timedelta(minutes=15)


async def test_coordinator_auth_error_raises_config_entry_auth_failed(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = HattrickDataUpdateCoordinator(
        hass, entry, MockCHPPClient(error=HattrickAuthError("token revocato"))
    )
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_api_error_raises_update_failed(hass):
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = HattrickDataUpdateCoordinator(
        hass, entry, MockCHPPClient(error=HattrickApiError("HTTP 500"))
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
