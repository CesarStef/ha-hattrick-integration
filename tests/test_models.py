"""Test del parsing XML -> dataclass (models.py)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from custom_components.hattrick.models import Economy, Team, TeamMood

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _root(name: str) -> ET.Element:
    return ET.fromstring((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_team_from_xml():
    team = Team.from_xml(_root("teamdetails.xml"))
    assert team.team_id == 7654321
    assert team.team_name == "Squadra di Test"
    assert team.short_name == "SDT"
    assert team.arena_id == 7654322
    assert team.league_id == 12345
    assert team.league_name == "Serie Test"
    assert team.region_name == "Regione Test"
    assert team.coach_name == "Allenatore Test"
    assert team.coach_level == 5
    assert team.user_id == 1234567
    assert team.login_name == "manager_test"
    assert team.fetched_date == datetime(2026, 11, 14, 10, 30, 0)


def test_team_mood_from_xml():
    mood = TeamMood.from_xml(_root("team.xml"))
    assert mood.morale == "excellent"
    assert mood.confidence == "wonderful"


def test_economy_from_xml():
    economy = Economy.from_xml(_root("economy.xml"))
    assert economy.cash == 5000000
    assert economy.expected_cash == 4800000
    assert economy.sponsors == 120000


def test_parsing_tollerante_campi_mancanti():
    xml = "<HattrickData><Team><TeamID>1</TeamID></Team></HattrickData>"
    team = Team.from_xml(ET.fromstring(xml))
    assert team.team_id == 1
    assert team.team_name == ""
    assert team.coach_level == 0
