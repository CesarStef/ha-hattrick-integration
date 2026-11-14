"""Test di diagnostics.py (redatta) e del repair per token revocato."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hattrick.api import HattrickAuthError
from custom_components.hattrick.const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_SECRET,
    CONF_CONSUMER_KEY,
    CONF_CONSUMER_SECRET,
    DOMAIN,
)
from custom_components.hattrick.coordinator import HattrickDataUpdateCoordinator
from custom_components.hattrick.diagnostics import async_get_config_entry_diagnostics
from custom_components.hattrick.repairs import async_create_fix_flow

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
}

ENTRY_DATA = {
    CONF_CONSUMER_KEY: "ck",
    CONF_CONSUMER_SECRET: "cs",
    CONF_ACCESS_TOKEN: "at",
    CONF_ACCESS_TOKEN_SECRET: "ats",
}


class MockCHPPClient:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def async_get_file(self, hass, file: str, **params):
        return ET.fromstring((FIXTURES_DIR / FILES[file]).read_text(encoding="utf-8"))


class FailingAuthClient(MockCHPPClient):
    async def async_get_file(self, hass, file: str, **params):
        raise HattrickAuthError("token revocato")


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, unique_id="1234567", data=ENTRY_DATA)


async def test_diagnostics_redacts_credentials(hass: HomeAssistant):
    entry = _entry()
    entry.add_to_hass(hass)
    with mock.patch("custom_components.hattrick.HattrickCHPPClient", MockCHPPClient):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    result = await async_get_config_entry_diagnostics(hass, entry)
    dump = json.dumps(result)
    # nessun valore reale di secret/token nel dump (la consumer key non è segreta)
    for secret in ("cs", '"at"', '"ats"'):
        assert secret not in dump
    assert result["entry"]["data"][CONF_CONSUMER_SECRET] == "***"
    assert result["entry"]["data"][CONF_ACCESS_TOKEN] == "***"
    assert result["entry"]["data"][CONF_ACCESS_TOKEN_SECRET] == "***"
    # i dati utili restano leggibili
    assert result["data"]["team_name"] == "Squadra di Test"
    assert result["data"]["team_id"] == 7654321
    assert result["coordinator"]["last_update_success"] is True


async def test_auth_error_creates_fixable_issue_and_success_deletes_it(hass: HomeAssistant):
    entry = _entry()
    entry.add_to_hass(hass)
    issue_id = f"token_revocato_{entry.entry_id}"

    coordinator = HattrickDataUpdateCoordinator(hass, entry, FailingAuthClient())
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
    registry = ir.async_get(hass)
    issue = registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.is_fixable is True
    assert issue.data["entry_id"] == entry.entry_id

    # dopo un update riuscito l'issue viene rimossa
    ok_coordinator = HattrickDataUpdateCoordinator(hass, entry, MockCHPPClient())
    await ok_coordinator._async_update_data()
    assert registry.async_get_issue(DOMAIN, issue_id) is None


async def test_repairs_fix_flow_created(hass: HomeAssistant):
    flow = await async_create_fix_flow(hass, "token_revocato_x", {"entry_id": "abc"})
    assert flow is not None
    assert hasattr(flow, "async_step_init")
