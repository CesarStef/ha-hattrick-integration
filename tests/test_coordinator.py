"""Test del DataUpdateCoordinator (coordinator.py)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hattrick.api import HattrickApiError, HattrickAuthError
from custom_components.hattrick.const import DOMAIN
from custom_components.hattrick.coordinator import HattrickDataUpdateCoordinator

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class MockCHPPClient:
    """Client CHPP finto che legge le fixture XML."""

    def __init__(self, files: dict[str, str] | None = None, error: Exception | None = None) -> None:
        self._files = files or {}
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
    client = MockCHPPClient(
        files={
            "teamdetails": "teamdetails.xml",
            "team": "team.xml",
            "economy": "economy.xml",
        }
    )
    coordinator = HattrickDataUpdateCoordinator(hass, entry, client)
    data = await coordinator._async_update_data()
    assert data.team.team_name == "Squadra di Test"
    assert data.team.team_id == 7654321
    assert data.mood.morale == "excellent"
    assert data.mood.confidence == "wonderful"
    assert data.economy.cash == 5000000


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
