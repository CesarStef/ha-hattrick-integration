"""Modello dati dell'integrazione Hattrick: parsing XML CHPP -> dataclass.

Le date CHPP sono in HTT (Europe/Stockholm), formato "yyyy-MM-dd HH:mm:ss".
Il parsing è tollerante: un campo mancante non rompe l'intero file.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

HTT_FORMAT = "%Y-%m-%d %H:%M:%S"
HTT_TIMEZONE = ZoneInfo("Europe/Stockholm")

# Codici CHPP -> etichette (da riconfermare contro la wiki CHPP).
SPECIALTIES = {
    0: "nessuna",
    1: "tecnico",
    2: "veloce",
    3: "potente",
    4: "imprevedibile",
    5: "colpo di testa",
    6: "regista",
}
TRAINING_TYPES = {
    0: "generale",
    1: "resistenza",
    2: "calci piazzati",
    3: "difesa",
    4: "finalizzazione",
    5: "cross",
    6: "gioco",
    7: "passaggi",
    8: "ali",
    9: "portiere",
}
MATCH_TYPES = {
    1: "lega",
    2: "qualificazione",
    3: "coppa",
    4: "amichevole",
    5: "amichevole",
    6: "masters",
    7: "nazionale",
    8: "coppa amichevole",
    10: "masters",
    11: "coppa",
    12: "mondiali",
    50: "allenamento",
    100: "amichevole neutrale",
}
STAFF_TYPES = {
    1: "assistente allenatore",
    2: "medico",
    3: "psicologo",
    4: "portavoce",
    5: "preparatore atletico",
}
TACTIC_TYPES = {
    0: "normale",
    1: "pressing",
    2: "contropiede",
    3: "palla lunga",
    4: "creativa",
    5: "relax",
}


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


def htt_to_aware(value: datetime) -> datetime:
    """Rende aware un datetime naive interpretandolo come HTT (Europe/Stockholm)."""
    if value is datetime.min:
        return value
    return value.replace(tzinfo=HTT_TIMEZONE)


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
    wages: int = 0

    @classmethod
    def from_xml(cls, root: ET.Element) -> Economy:
        economy = root.find("Economy")
        return cls(
            cash=_find_int(economy, "Cash"),
            expected_cash=_find_int(economy, "ExpectedCash"),
            sponsors=_find_int(economy, "Sponsors"),
            wages=_find_int(economy, "Costs/Wages"),
        )


@dataclass
class Player:
    """Giocatore da players.xml."""

    player_id: int
    first_name: str
    nick_name: str
    last_name: str
    number: int
    age: int
    age_days: int
    tsi: int
    form: int
    experience: int
    leadership: int
    salary: int
    specialty: int
    cards: int
    injury_weeks: int
    transfer_listed: bool
    keeper: int
    defender: int
    playmaker: int
    passing: int
    winger: int
    scoring: int
    set_pieces: int
    stamina: int

    @property
    def full_name(self) -> str:
        """Nome completo (senza nickname vuoto)."""
        return " ".join(p for p in (self.first_name, self.nick_name, self.last_name) if p)

    @property
    def role(self) -> str:
        """Ruolo dal skill principale (tra i 5 ruoli di gioco)."""
        skills = {
            "portiere": self.keeper,
            "difensore": self.defender,
            "centrocampista": self.playmaker,
            "ala": self.winger,
            "attaccante": self.scoring,
        }
        return max(skills, key=lambda key: skills[key])

    @property
    def specialty_label(self) -> str:
        """Etichetta della specialità."""
        return SPECIALTIES.get(self.specialty, "sconosciuta")

    @property
    def injured(self) -> bool:
        """True se il giocatore è infortunato."""
        return self.injury_weeks > 0

    @property
    def suspended(self) -> bool:
        """True se il giocatore è squalificato (3+ cartellini)."""
        return self.cards >= 3

    def to_dict(self) -> dict[str, Any]:
        """Rappresentazione JSON-serializzabile per la risposta del servizio."""
        return {
            "player_id": self.player_id,
            "nome": self.full_name,
            "numero": self.number,
            "ruolo": self.role,
            "eta": self.age,
            "giorni_eta": self.age_days,
            "tsi": self.tsi,
            "forma": self.form,
            "esperienza": self.experience,
            "leadership": self.leadership,
            "stipendio": self.salary,
            "specialita": self.specialty_label,
            "cartellini": self.cards,
            "infortunio_settimane": self.injury_weeks,
            "in_lista_trasferimenti": self.transfer_listed,
            "skill": {
                "portiere": self.keeper,
                "difensore": self.defender,
                "centrocampista": self.playmaker,
                "passaggi": self.passing,
                "ala": self.winger,
                "attaccante": self.scoring,
                "calci_piazzati": self.set_pieces,
                "resistenza": self.stamina,
            },
        }

    @classmethod
    def from_xml(cls, elem: ET.Element) -> Player:
        return cls(
            player_id=_find_int(elem, "PlayerID"),
            first_name=_find_text(elem, "FirstName"),
            nick_name=_find_text(elem, "NickName"),
            last_name=_find_text(elem, "LastName"),
            number=_find_int(elem, "PlayerNumber"),
            age=_find_int(elem, "Age"),
            age_days=_find_int(elem, "AgeDays"),
            tsi=_find_int(elem, "TSI"),
            form=_find_int(elem, "PlayerForm"),
            experience=_find_int(elem, "Experience"),
            leadership=_find_int(elem, "Leadership"),
            salary=_find_int(elem, "Salary"),
            specialty=_find_int(elem, "Specialty"),
            cards=_find_int(elem, "Cards"),
            injury_weeks=_find_int(elem, "InjuryWeeks"),
            transfer_listed=_find_int(elem, "TransferListed") == 1,
            keeper=_find_int(elem, "KeeperSkill"),
            defender=_find_int(elem, "DefenderSkill"),
            playmaker=_find_int(elem, "PlaymakerSkill"),
            passing=_find_int(elem, "PassingSkill"),
            winger=_find_int(elem, "WingerSkill"),
            scoring=_find_int(elem, "ScoringSkill"),
            set_pieces=_find_int(elem, "SetPiecesSkill"),
            stamina=_find_int(elem, "StaminaSkill"),
        )


@dataclass
class Players:
    """Rosa completa da players.xml."""

    team_id: int
    team_name: str
    players: list[Player] = field(default_factory=list)

    @property
    def tsi_total(self) -> int:
        """Somma TSI della rosa."""
        return sum(p.tsi for p in self.players)

    @property
    def injured(self) -> list[Player]:
        """Giocatori infortunati."""
        return [p for p in self.players if p.injured]

    @property
    def suspended(self) -> list[Player]:
        """Giocatori squalificati."""
        return [p for p in self.players if p.suspended]

    @property
    def avg_form(self) -> float:
        """Forma media della rosa."""
        if not self.players:
            return 0.0
        return sum(p.form for p in self.players) / len(self.players)

    @property
    def avg_age(self) -> float:
        """Età media della rosa."""
        if not self.players:
            return 0.0
        return sum(p.age + p.age_days / 112 for p in self.players) / len(self.players)

    @property
    def form_by_role(self) -> dict[str, float]:
        """Forma media per reparto (POR/DIF/CC/ATT)."""
        groups: dict[str, list[float]] = {"POR": [], "DIF": [], "CC": [], "ATT": []}
        for p in self.players:
            if p.keeper >= max(p.defender, p.playmaker, p.winger, p.scoring):
                groups["POR"].append(p.form)
            elif p.scoring >= max(p.defender, p.playmaker, p.winger):
                groups["ATT"].append(p.form)
            elif p.defender >= p.playmaker:
                groups["DIF"].append(p.form)
            else:
                groups["CC"].append(p.form)
        return {k: round(sum(v) / len(v), 2) for k, v in groups.items() if v}

    @classmethod
    def from_xml(cls, root: ET.Element) -> Players:
        team = root.find("Team")
        return cls(
            team_id=_find_int(team, "TeamID"),
            team_name=_find_text(team, "TeamName"),
            players=[Player.from_xml(p) for p in team.findall("PlayerList/Player")],
        )


@dataclass
class LeagueMatch:
    """Partita di lega da leaguedetails.xml."""

    match_id: int
    round: int
    date: datetime
    home_id: int
    home_name: str
    home_goals: int | None
    away_id: int
    away_name: str
    away_goals: int | None

    def is_home(self, team_id: int) -> bool:
        """True se la squadra gioca in casa."""
        return self.home_id == team_id

    def opponent(self, team_id: int) -> str:
        """Nome dell'avversario."""
        return self.away_name if self.is_home(team_id) else self.home_name

    def score(self, team_id: int) -> str | None:
        """Risultato dal punto di vista della squadra ('3-1'), None se non giocata."""
        if self.home_goals is None or self.away_goals is None:
            return None
        if self.is_home(team_id):
            return f"{self.home_goals}-{self.away_goals}"
        return f"{self.away_goals}-{self.home_goals}"

    @classmethod
    def from_xml(cls, elem: ET.Element) -> LeagueMatch:
        home = elem.find("HomeTeam")
        away = elem.find("AwayTeam")
        home_goals = _find_text(home, "HomeGoals")
        away_goals = _find_text(away, "AwayGoals")
        return cls(
            match_id=_find_int(elem, "MatchID"),
            round=_find_int(elem, "MatchRound"),
            date=parse_htt_datetime(_find_text(elem, "MatchDate")),
            home_id=_find_int(home, "HomeTeamID"),
            home_name=_find_text(home, "HomeTeamName"),
            home_goals=int(home_goals) if home_goals else None,
            away_id=_find_int(away, "AwayTeamID"),
            away_name=_find_text(away, "AwayTeamName"),
            away_goals=int(away_goals) if away_goals else None,
        )


@dataclass
class LeagueDetails:
    """Dati del girone da leaguedetails.xml."""

    league_level_unit_id: int
    league_level_unit_name: str
    league_level: int
    max_teams: int
    current_round: int
    position: int
    matches: list[LeagueMatch] = field(default_factory=list)

    @classmethod
    def from_xml(cls, root: ET.Element) -> LeagueDetails:
        team = root.find("Team")
        return cls(
            league_level_unit_id=_find_int(team, "LeagueLevelUnitID"),
            league_level_unit_name=_find_text(team, "LeagueLevelUnitName"),
            league_level=_find_int(team, "LeagueLevel"),
            max_teams=_find_int(team, "MaxNumberOfTeams"),
            current_round=_find_int(team, "CurrentMatchRound"),
            position=_find_int(team, "TeamPosition"),
            matches=[LeagueMatch.from_xml(m) for m in team.findall("MatchList/Match")],
        )


@dataclass
class Match:
    """Partita da matches.xml (tutte le competizioni)."""

    match_id: int
    date: datetime
    match_type: int
    home_id: int
    home_name: str
    home_goals: int | None
    away_id: int
    away_name: str
    away_goals: int | None
    arena_id: int
    arena_name: str

    @property
    def match_type_label(self) -> str:
        """Etichetta del tipo di partita."""
        return MATCH_TYPES.get(self.match_type, "altro")

    @property
    def is_played(self) -> bool:
        """True se la partita è stata giocata."""
        return self.home_goals is not None and self.away_goals is not None

    def is_home(self, team_id: int) -> bool:
        """True se la squadra gioca in casa."""
        return self.home_id == team_id

    def opponent(self, team_id: int) -> str:
        """Nome dell'avversario."""
        return self.away_name if self.is_home(team_id) else self.home_name

    def score(self, team_id: int) -> str | None:
        """Risultato dal punto di vista della squadra, None se non giocata."""
        if not self.is_played:
            return None
        if self.is_home(team_id):
            return f"{self.home_goals}-{self.away_goals}"
        return f"{self.away_goals}-{self.home_goals}"

    @classmethod
    def from_xml(cls, elem: ET.Element) -> Match:
        home = elem.find("HomeTeam")
        away = elem.find("AwayTeam")
        arena = elem.find("Arena")
        home_goals = _find_text(home, "HomeGoals")
        away_goals = _find_text(away, "AwayGoals")
        return cls(
            match_id=_find_int(elem, "MatchID"),
            date=parse_htt_datetime(_find_text(elem, "MatchDate")),
            match_type=_find_int(elem, "MatchType"),
            home_id=_find_int(home, "HomeTeamID"),
            home_name=_find_text(home, "HomeTeamName"),
            home_goals=int(home_goals) if home_goals else None,
            away_id=_find_int(away, "AwayTeamID"),
            away_name=_find_text(away, "AwayTeamName"),
            away_goals=int(away_goals) if away_goals else None,
            arena_id=_find_int(arena, "ArenaID"),
            arena_name=_find_text(arena, "ArenaName"),
        )


@dataclass
class Matches:
    """Partite recenti e future da matches.xml."""

    team_id: int
    team_name: str
    matches: list[Match] = field(default_factory=list)

    @property
    def upcoming(self) -> list[Match]:
        """Partite non ancora giocate, dalla più vicina."""
        return sorted((m for m in self.matches if not m.is_played), key=lambda m: m.date)

    @property
    def played(self) -> list[Match]:
        """Partite giocate, dalla più recente."""
        return sorted((m for m in self.matches if m.is_played), key=lambda m: m.date, reverse=True)

    @property
    def next_match(self) -> Match | None:
        """Prossima partita in programma."""
        return self.upcoming[0] if self.upcoming else None

    @property
    def last_match(self) -> Match | None:
        """Ultima partita giocata."""
        return self.played[0] if self.played else None

    @classmethod
    def from_xml(cls, root: ET.Element) -> Matches:
        team = root.find("Team")
        return cls(
            team_id=_find_int(team, "TeamID"),
            team_name=_find_text(team, "TeamName"),
            matches=[Match.from_xml(m) for m in team.findall("MatchList/Match")],
        )


@dataclass
class Training:
    """Allenamento corrente da training.xml."""

    team_id: int
    team_name: str
    training_type: int
    training_intensity: int
    stamina_part: int

    @property
    def training_type_label(self) -> str:
        """Etichetta del tipo di allenamento."""
        return TRAINING_TYPES.get(self.training_type, "sconosciuto")

    @classmethod
    def from_xml(cls, root: ET.Element) -> Training:
        team = root.find("Team")
        return cls(
            team_id=_find_int(team, "TeamID"),
            team_name=_find_text(team, "TeamName"),
            training_type=_find_int(team, "TrainingType"),
            training_intensity=_find_int(team, "TrainingIntensity"),
            stamina_part=_find_int(team, "StaminaTrainingPart"),
        )


@dataclass
class TrainingWeek:
    """Riepilogo settimanale da trainingsummary.xml."""

    season: int
    week: int
    training_type: int
    training_intensity: int

    @property
    def training_type_label(self) -> str:
        """Etichetta del tipo di allenamento della settimana."""
        return TRAINING_TYPES.get(self.training_type, "sconosciuto")

    @classmethod
    def from_xml(cls, elem: ET.Element) -> TrainingWeek:
        return cls(
            season=_find_int(elem, "Season"),
            week=_find_int(elem, "Week"),
            training_type=_find_int(elem, "TrainingType"),
            training_intensity=_find_int(elem, "TrainingIntensity"),
        )


@dataclass
class TrainingSummary:
    """Riepilogo allenamenti da trainingsummary.xml."""

    team_id: int
    team_name: str
    weeks: list[TrainingWeek] = field(default_factory=list)

    @property
    def last_week(self) -> TrainingWeek | None:
        """Ultima settimana di allenamento registrata."""
        return self.weeks[-1] if self.weeks else None

    @classmethod
    def from_xml(cls, root: ET.Element) -> TrainingSummary:
        team = root.find("Team")
        return cls(
            team_id=_find_int(team, "TeamID"),
            team_name=_find_text(team, "TeamName"),
            weeks=[
                TrainingWeek.from_xml(w)
                for w in team.findall("TrainingSummaryList/TrainingSummary")
            ],
        )


@dataclass
class Arena:
    """Stadio da arenadetails.xml."""

    arena_id: int
    arena_name: str
    team_id: int
    team_name: str
    total_capacity: int
    terraces: int
    basic: int
    roof: int
    vip: int

    @property
    def sectors(self) -> dict[str, int]:
        """Capacità per settore."""
        return {
            "terraces": self.terraces,
            "basic": self.basic,
            "roof": self.roof,
            "vip": self.vip,
        }

    @classmethod
    def from_xml(cls, root: ET.Element) -> Arena:
        arena = root.find("Arena")
        team = arena.find("Team") if arena is not None else None
        capacity = arena.find("CurrentCapacity") if arena is not None else None
        return cls(
            arena_id=_find_int(arena, "ArenaID"),
            arena_name=_find_text(arena, "ArenaName"),
            team_id=_find_int(team, "TeamID"),
            team_name=_find_text(team, "TeamName"),
            total_capacity=_find_int(capacity, "TotalCapacity"),
            terraces=_find_int(capacity, "Terraces"),
            basic=_find_int(capacity, "Basic"),
            roof=_find_int(capacity, "Roof"),
            vip=_find_int(capacity, "VIP"),
        )


@dataclass
class StaffMember:
    """Membro dello staff da club.xml."""

    name: str
    staff_type: int
    level: int
    cost: int

    @property
    def staff_type_label(self) -> str:
        """Etichetta del ruolo dello staff."""
        return STAFF_TYPES.get(self.staff_type, "altro")

    @classmethod
    def from_xml(cls, elem: ET.Element) -> StaffMember:
        return cls(
            name=_find_text(elem, "Name"),
            staff_type=_find_int(elem, "StaffType"),
            level=_find_int(elem, "StaffLevel"),
            cost=_find_int(elem, "Cost"),
        )


@dataclass
class Club:
    """Dati del club da club.xml."""

    team_id: int
    team_name: str
    fanclub_size: int
    fanclub_name: str
    youth_level: int
    youth_name: str
    staff: list[StaffMember] = field(default_factory=list)

    @classmethod
    def from_xml(cls, root: ET.Element) -> Club:
        team = root.find("Team")
        fanclub = team.find("Fanclub") if team is not None else None
        youth = team.find("YouthSquad") if team is not None else None
        return cls(
            team_id=_find_int(team, "TeamID"),
            team_name=_find_text(team, "TeamName"),
            fanclub_size=_find_int(fanclub, "FanclubSize"),
            fanclub_name=_find_text(fanclub, "FanclubName"),
            youth_level=_find_int(youth, "YouthLevel"),
            youth_name=_find_text(youth, "YouthSquadName"),
            staff=[StaffMember.from_xml(s) for s in team.findall("StaffList/Staff")],
        )


@dataclass
class LeagueInfo:
    """Lega in worlddetails.xml, con le prossime date di update HT."""

    league_id: int
    league_name: str
    training_date: datetime
    economy_date: datetime
    series_match_date: datetime
    cup_match_date: datetime

    @classmethod
    def from_xml(cls, elem: ET.Element) -> LeagueInfo:
        return cls(
            league_id=_find_int(elem, "LeagueID"),
            league_name=_find_text(elem, "LeagueName"),
            training_date=parse_htt_datetime(_find_text(elem, "TrainingDate")),
            economy_date=parse_htt_datetime(_find_text(elem, "EconomyDate")),
            series_match_date=parse_htt_datetime(_find_text(elem, "SeriesMatchDate")),
            cup_match_date=parse_htt_datetime(_find_text(elem, "CupMatchDate")),
        )


@dataclass
class World:
    """Dati globali HT da worlddetails.xml."""

    season: int
    server_time: datetime
    countries: int
    leagues: list[LeagueInfo] = field(default_factory=list)

    def league(self, league_id: int) -> LeagueInfo | None:
        """Informazioni della lega con l'ID dato, se presente."""
        return next((lg for lg in self.leagues if lg.league_id == league_id), None)

    @classmethod
    def from_xml(cls, root: ET.Element) -> World:
        world = root.find("World")
        leagues = [
            LeagueInfo.from_xml(lg) for lg in world.findall("CountryList/Country/LeagueList/League")
        ]
        return cls(
            season=_find_int(world, "Season"),
            server_time=parse_htt_datetime(_find_text(root, "FetchedDate")),
            countries=len(world.findall("CountryList/Country")),
            leagues=leagues,
        )


def _ratings(elem: ET.Element | None, prefix: str) -> dict[str, int]:
    """Dizionario dei rating di reparto (POR/DIF/CC/ATT) da un nodo ratings."""
    if elem is None:
        return {}
    return {
        "POR": _find_int(elem, f"{prefix}Goalkeeper"),
        "DIF": _find_int(elem, f"{prefix}Defense"),
        "CC": _find_int(elem, f"{prefix}Midfield"),
        "ATT": _find_int(elem, f"{prefix}Attack"),
    }


@dataclass
class MatchDetails:
    """Dettaglio di una partita da matchdetails.xml (on-demand, richiede matchID)."""

    match_id: int
    match_date: datetime
    home_id: int
    home_name: str
    home_goals: int
    away_id: int
    away_name: str
    away_goals: int
    arena_name: str
    weather: str
    sold_total: int
    referee_name: str
    possession_home: int
    shots_home: int
    shots_away: int
    home_ratings: dict[str, int]
    away_ratings: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Rappresentazione JSON-serializzabile per la risposta del servizio."""
        return {
            "match_id": self.match_id,
            "match_date": self.match_date.isoformat(),
            "home_team": {"id": self.home_id, "name": self.home_name, "goals": self.home_goals},
            "away_team": {"id": self.away_id, "name": self.away_name, "goals": self.away_goals},
            "arena": self.arena_name,
            "weather": self.weather,
            "sold_total": self.sold_total,
            "referee": self.referee_name,
            "possession_home": self.possession_home,
            "shots_home": self.shots_home,
            "shots_away": self.shots_away,
            "home_ratings": self.home_ratings,
            "away_ratings": self.away_ratings,
        }

    @classmethod
    def from_xml(cls, root: ET.Element) -> MatchDetails:
        home = root.find("HomeTeam")
        away = root.find("AwayTeam")
        arena = root.find("Arena")
        referee = root.find("MatchReferee")
        stats = root.find("MatchStatistics")
        return cls(
            match_id=_find_int(root, "MatchID"),
            match_date=parse_htt_datetime(_find_text(root, "MatchDate")),
            home_id=_find_int(home, "HomeTeamID"),
            home_name=_find_text(home, "HomeTeamName"),
            home_goals=_find_int(home, "HomeGoals"),
            away_id=_find_int(away, "AwayTeamID"),
            away_name=_find_text(away, "AwayTeamName"),
            away_goals=_find_int(away, "AwayGoals"),
            arena_name=_find_text(arena, "ArenaName"),
            weather=_find_text(arena, "Weather"),
            sold_total=_find_int(arena, "SoldTotal"),
            referee_name=_find_text(referee, "RefereeName"),
            possession_home=_find_int(stats, "PossessionHome"),
            shots_home=_find_int(stats, "ShotsHome"),
            shots_away=_find_int(stats, "ShotsAway"),
            home_ratings=_ratings(
                stats.find("HomeRatings") if stats is not None else None, "Rating"
            ),
            away_ratings=_ratings(
                stats.find("AwayRatings") if stats is not None else None, "Rating"
            ),
        )


@dataclass
class MatchLineup:
    """Formazione e tattica di una partita da matchlineup.xml (on-demand, matchID)."""

    match_id: int
    match_date: datetime
    team_id: int
    formation: str
    tactic_type: int
    tactic_skill: int
    ratings: dict[str, int]

    @property
    def tactic_label(self) -> str:
        """Etichetta della tattica usata."""
        return TACTIC_TYPES.get(self.tactic_type, "sconosciuta")

    def to_dict(self) -> dict[str, Any]:
        """Rappresentazione JSON-serializzabile."""
        return {
            "match_id": self.match_id,
            "match_date": self.match_date.isoformat(),
            "team_id": self.team_id,
            "formation": self.formation,
            "tactic": self.tactic_label,
            "tactic_skill": self.tactic_skill,
            "ratings": self.ratings,
        }

    @classmethod
    def from_xml(cls, root: ET.Element, team_id: int) -> MatchLineup:
        """Legge il lato (casa/trasferta) della squadra con `team_id`."""
        home = root.find("HomeTeam")
        away = root.find("AwayTeam")
        side = home if _find_int(home, "HomeTeamID") == team_id else away
        ratings = side.find("Ratings") if side is not None else None
        return cls(
            match_id=_find_int(root, "MatchID"),
            match_date=parse_htt_datetime(_find_text(root, "MatchDate")),
            team_id=team_id,
            formation=_find_text(side, "TeamFormation"),
            tactic_type=_find_int(side, "TacticType"),
            tactic_skill=_find_int(side, "TacticSkill"),
            ratings=_ratings(ratings, "Rating"),
        )


@dataclass
class HattrickData:
    """Contenitore dei dati aggiornati dal coordinator.

    I file base (team/mood/economy) sono sempre presenti; gli altri sono
    None se il file corrispondente è disabilitato nelle opzioni.
    """

    team: Team
    mood: TeamMood
    economy: Economy
    club: Club | None = None
    players: Players | None = None
    training: Training | None = None
    training_summary: TrainingSummary | None = None
    league: LeagueDetails | None = None
    matches: Matches | None = None
    arena: Arena | None = None
    world: World | None = None
    match_details: MatchDetails | None = None
    match_lineup: MatchLineup | None = None
