"""Test dei sensor base dopo il setup della config entry."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
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


async def _setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1234567", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    with mock.patch("custom_components.hattrick.HattrickCHPPClient", MockCHPPClient):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_sensors_created_with_expected_states(hass: HomeAssistant):
    await _setup_entry(hass)
    registry = er.async_get(hass)
    expected = {
        "team_name": "Squadra di Test",
        "morale": "excellent",
        "fiducia_tifosi": "wonderful",
        "cassa": "5000000",
    }
    for key, value in expected.items():
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"7654321_{key}")
        assert entity_id is not None, f"entità mancante: {key}"
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == value


async def test_sensor_attributes(hass: HomeAssistant):
    await _setup_entry(hass)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, "7654321_cassa")
    state = hass.states.get(entity_id)
    assert state.attributes["cassa_prevista"] == 4800000
    assert state.attributes["sponsor"] == 120000


async def test_device_info_groups_entities(hass: HomeAssistant):
    await _setup_entry(hass)
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={(DOMAIN, "7654321")})
    assert device is not None
    assert device.name == "Squadra di Test"
    assert device.manufacturer == "Hattrick"
    entity_registry = er.async_get(hass)
    entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, "7654321_morale")
    entry = entity_registry.async_get(entity_id)
    assert entry.device_id == device.id
