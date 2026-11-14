"""Test del parsing XML -> dataclass (models.py)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from custom_components.hattrick.models import (
    Arena,
    Club,
    Economy,
    LeagueDetails,
    MatchDetails,
    Matches,
    MatchLineup,
    Players,
    Team,
    TeamMood,
    Training,
    TrainingSummary,
    World,
)

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
    assert team.fetched_date == datetime.min


def test_economy_wages():
    economy = Economy.from_xml(_root("economy.xml"))
    assert economy.wages == 350000


def test_players_from_xml():
    players = Players.from_xml(_root("players.xml"))
    assert players.team_id == 7654321
    assert len(players.players) == 3
    keeper = players.players[0]
    assert keeper.player_id == 1001
    assert keeper.full_name == "Mario Rossi"
    assert keeper.role == "portiere"
    assert keeper.specialty_label == "nessuna"
    assert not keeper.injured
    assert not keeper.suspended
    assert players.tsi_total == 80000 + 60000 + 45000
    assert [p.player_id for p in players.injured] == [1002]
    assert [p.player_id for p in players.suspended] == [1003]
    assert players.avg_form == (6 + 5 + 7) / 3
    assert players.form_by_role["POR"] == 6.0
    assert players.form_by_role["ATT"] == 7.0


def test_leaguedetails_from_xml():
    league = LeagueDetails.from_xml(_root("leaguedetails.xml"))
    assert league.league_level_unit_name == "Serie Test"
    assert league.league_level == 3
    assert league.max_teams == 8
    assert league.current_round == 5
    assert league.position == 3
    assert len(league.matches) == 2
    played = league.matches[0]
    assert played.score(7654321) == "3-1"
    assert played.opponent(7654321) == "Avversari FC"
    assert played.is_home(7654321)
    upcoming = league.matches[1]
    assert upcoming.score(7654321) is None
    assert upcoming.opponent(7654321) == "Altra Squadra"
    assert not upcoming.is_home(7654321)


def test_matches_from_xml():
    matches = Matches.from_xml(_root("matches.xml"))
    assert matches.team_id == 7654321
    assert len(matches.matches) == 3
    last = matches.last_match
    assert last is not None
    assert last.match_id == 9001
    assert last.score(7654321) == "3-1"
    assert last.match_type_label == "lega"
    nxt = matches.next_match
    assert nxt is not None
    assert nxt.match_id == 9002
    assert nxt.opponent(7654321) == "Altra Squadra"
    assert not nxt.is_home(7654321)
    assert len(matches.upcoming) == 2
    assert matches.upcoming[1].match_type_label == "coppa"


def test_training_from_xml():
    training = Training.from_xml(_root("training.xml"))
    assert training.training_type == 6
    assert training.training_type_label == "gioco"
    assert training.training_intensity == 100
    assert training.stamina_part == 10


def test_trainingsummary_from_xml():
    summary = TrainingSummary.from_xml(_root("trainingsummary.xml"))
    assert len(summary.weeks) == 2
    last = summary.last_week
    assert last is not None
    assert last.season == 75
    assert last.week == 46
    assert last.training_type_label == "gioco"


def test_arenadetails_from_xml():
    arena = Arena.from_xml(_root("arenadetails.xml"))
    assert arena.arena_id == 7654322
    assert arena.arena_name == "Stadio di Test"
    assert arena.total_capacity == 50000
    assert arena.sectors == {"terraces": 20000, "basic": 15000, "roof": 10000, "vip": 5000}


def test_club_from_xml():
    club = Club.from_xml(_root("club.xml"))
    assert club.fanclub_size == 1500
    assert club.fanclub_name == "Fan Club di Test"
    assert club.youth_level == 5
    assert club.youth_name == "Giovanili di Test"
    assert len(club.staff) == 3
    assert club.staff[0].staff_type_label == "medico"
    assert club.staff[0].level == 4


def test_worlddetails_from_xml():
    world = World.from_xml(_root("worlddetails.xml"))
    assert world.season == 75
    assert world.server_time == datetime(2026, 11, 14, 10, 30, 0)
    assert world.countries == 1
    league = world.league(12345)
    assert league is not None
    assert league.league_name == "Serie Test"
    assert league.training_date == datetime(2026, 11, 15, 3, 30, 0)
    assert league.economy_date == datetime(2026, 11, 15, 3, 45, 0)
    assert world.league(99999) is None


def test_matchdetails_from_xml():
    details = MatchDetails.from_xml(_root("matchdetails.xml"))
    assert details.match_id == 9001
    assert details.match_date == datetime(2026, 11, 7, 19, 30, 0)
    assert details.home_id == 7654321
    assert details.home_name == "Squadra di Test"
    assert details.home_goals == 3
    assert details.away_name == "Avversari FC"
    assert details.away_goals == 1
    assert details.arena_name == "Stadio di Test"
    assert details.weather == "Sunny"
    assert details.sold_total == 48000
    assert details.referee_name == "Arbitro Test"
    assert details.possession_home == 55
    assert details.shots_home == 12
    assert details.shots_away == 6
    assert details.home_ratings == {"POR": 8, "DIF": 7, "CC": 9, "ATT": 8}
    assert details.away_ratings["ATT"] == 5
    as_dict = details.to_dict()
    assert as_dict["home_team"]["goals"] == 3
    assert as_dict["home_ratings"]["CC"] == 9


def test_matchlineup_from_xml_home_team():
    lineup = MatchLineup.from_xml(_root("matchlineup.xml"), team_id=7654321)
    assert lineup.match_id == 9001
    assert lineup.team_id == 7654321
    assert lineup.formation == "433"
    assert lineup.tactic_type == 1
    assert lineup.tactic_label == "pressing"
    assert lineup.tactic_skill == 5
    assert lineup.ratings == {"POR": 8, "DIF": 7, "CC": 9, "ATT": 8}
    as_dict = lineup.to_dict()
    assert as_dict["tactic"] == "pressing"
    assert as_dict["formation"] == "433"


def test_matchlineup_from_xml_away_team():
    lineup = MatchLineup.from_xml(_root("matchlineup.xml"), team_id=8000001)
    assert lineup.formation == "442"
    assert lineup.tactic_type == 0
    assert lineup.tactic_label == "normale"
    assert lineup.ratings["CC"] == 7
