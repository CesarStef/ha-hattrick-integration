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


def _state(hass: HomeAssistant, key: str):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"7654321_{key}")
    assert entity_id is not None, f"entità mancante: {key}"
    return hass.states.get(entity_id)


async def test_sensor_rosa(hass: HomeAssistant):
    await _setup_entry(hass)
    assert _state(hass, "giocatori").state == "3"
    assert _state(hass, "tsi_totale").state == str(80000 + 60000 + 45000)
    assert _state(hass, "infortunati").state == "1"
    assert _state(hass, "squalificati").state == "1"
    assert _state(hass, "forma_squadra").state == str(round((6 + 5 + 7) / 3, 2))


async def test_sensor_rosa_attributi(hass: HomeAssistant):
    await _setup_entry(hass)
    giocatori = _state(hass, "giocatori").attributes["giocatori"]
    assert len(giocatori) == 3
    assert giocatori[0]["nome"] == "Mario Rossi"
    assert giocatori[0]["ruolo"] == "portiere"
    assert giocatori[1]["infortunio_settimane"] == 2
    assert giocatori[2]["squalificato"] is True
    infortunati = _state(hass, "infortunati").attributes["infortunati"]
    assert infortunati == [{"id": 1002, "nome": "Luca Il Muro Bianchi", "settimane": 2}]
    squalificati = _state(hass, "squalificati").attributes["squalificati"]
    assert squalificati[0]["cartellini"] == 3
    forma = _state(hass, "forma_squadra").attributes["forma_per_reparto"]
    assert forma["POR"] == 6.0
    assert forma["ATT"] == 7.0


async def test_sensor_club(hass: HomeAssistant):
    await _setup_entry(hass)
    assert _state(hass, "fanclub").state == "1500"
    assert _state(hass, "settore_giovanile").state == "5"
    staff = _state(hass, "staff")
    assert staff.state == "3"
    assert staff.attributes["medico"]["livello"] == 4
    assert staff.attributes["psicologo"]["nome"] == "Sig.ra Calma"


async def test_sensor_classifica(hass: HomeAssistant):
    await _setup_entry(hass)
    posizione = _state(hass, "posizione")
    assert posizione.state == "3"
    assert posizione.attributes["girone"] == "Serie Test"
    assert posizione.attributes["giornata"] == 5
    assert posizione.attributes["numero_squadre"] == 8


async def test_sensor_partite(hass: HomeAssistant):
    await _setup_entry(hass)
    prossima = _state(hass, "prossima_partita")
    assert prossima.attributes["match_id"] == 9002
    assert prossima.attributes["avversario"] == "Altra Squadra"
    assert prossima.attributes["casa_trasferta"] == "trasferta"
    assert prossima.attributes["tipo"] == "lega"
    # 19:30 HTT (CET, UTC+1 a novembre) -> 18:30 UTC nello stato HA
    assert prossima.state == "2026-11-14T18:30:00+00:00"
    ultima = _state(hass, "ultima_partita")
    assert ultima.state == "3-1"
    assert ultima.attributes["avversario"] == "Avversari FC"
    assert ultima.attributes["casa_trasferta"] == "casa"
    programmate = _state(hass, "partite_programmate")
    assert programmate.state == "2"
    assert len(programmate.attributes["prossime"]) == 2
    assert programmate.attributes["prossime"][1]["tipo"] == "coppa"


async def test_sensor_economia_estesa(hass: HomeAssistant):
    await _setup_entry(hass)
    assert _state(hass, "entrate_previste").state == "4800000"
    assert _state(hass, "entrate_previste").attributes["stipendi"] == 350000
    assert _state(hass, "stipendi").state == "350000"
