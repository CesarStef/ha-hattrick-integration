"""Modello dati dell'integrazione Hattrick: parsing XML CHPP -> dataclass.

Le date CHPP sono in HTT (Europe/Stockholm), formato "yyyy-MM-dd HH:mm:ss".
Il parsing è tollerante: un campo mancante non rompe l'intero file.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime

HTT_FORMAT = "%Y-%m-%d %H:%M:%S"


def _find_text(elem: ET.Element | None, path: str, default: str = "") -> str:
    """Testo del primo nodo in `path`, oppure `default`."""
    if elem is None:
        return default
    node = elem.find(path)
    if node is None or node.text is None:
        return default
    return node.text.strip()


def _find_int(elem: ET.Element | None, path: str, default: int = 0) -> int:
    """Intero del primo nodo in `path`, oppure `default`."""
    try:
        return int(_find_text(elem, path, str(default)))
    except ValueError:
        return default


def parse_htt_datetime(value: str) -> datetime:
    """Converte una data CHPP (HTT) in datetime naive.

    Stringa vuota o malformata -> datetime.min (parsing tollerante).
    """
    try:
        return datetime.strptime(value, HTT_FORMAT)
    except ValueError:
        return datetime.min


@dataclass
class Team:
    """Dati della squadra da teamdetails.xml."""

    team_id: int
    team_name: str
    short_name: str
    arena_id: int
    arena_name: str
    league_id: int
    league_name: str
    region_name: str
    coach_name: str
    coach_level: int
    user_id: int
    login_name: str
    fetched_date: datetime

    @classmethod
    def from_xml(cls, root: ET.Element) -> Team:
        team = root.find("Team")
        user = root.find("User")
        return cls(
            team_id=_find_int(team, "TeamID"),
            team_name=_find_text(team, "TeamName"),
            short_name=_find_text(team, "ShortTeamName"),
            arena_id=_find_int(team, "Arena/ArenaID"),
            arena_name=_find_text(team, "Arena/ArenaName"),
            league_id=_find_int(team, "League/LeagueID"),
            league_name=_find_text(team, "League/LeagueName"),
            region_name=_find_text(team, "Region/RegionName"),
            coach_name=_find_text(team, "Trainer/Name"),
            coach_level=_find_int(team, "Trainer/CoachLevel"),
            user_id=_find_int(root, "UserID"),
            login_name=_find_text(user, "LoginName"),
            fetched_date=parse_htt_datetime(_find_text(root, "FetchedDate")),
        )


@dataclass
class TeamMood:
    """Morale e fiducia dei tifosi da team.xml."""

    morale: str
    confidence: str

    @classmethod
    def from_xml(cls, root: ET.Element) -> TeamMood:
        team = root.find("Team")
        return cls(
            morale=_find_text(team, "TeamSpirit"),
            confidence=_find_text(team, "Confidence"),
        )


@dataclass
class Economy:
    """Dati economici da economy.xml."""

    cash: int
    expected_cash: int
    sponsors: int

    @classmethod
    def from_xml(cls, root: ET.Element) -> Economy:
        economy = root.find("Economy")
        return cls(
            cash=_find_int(economy, "Cash"),
            expected_cash=_find_int(economy, "ExpectedCash"),
            sponsors=_find_int(economy, "Sponsors"),
        )


@dataclass
class HattrickData:
    """Contenitore dei dati aggiornati dal coordinator."""

    team: Team
    mood: TeamMood
    economy: Economy
