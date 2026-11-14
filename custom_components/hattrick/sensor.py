"""Piattaforma sensor dell'integrazione Hattrick (fase M1: sensor base)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HattrickDataUpdateCoordinator
from .entity import HattrickEntity
from .models import HattrickData, htt_to_aware

StateValue = str | int | float | None


def _world_attrs(data: HattrickData) -> dict[str, Any]:
    """Attributi del sensor server_time: stagione e prossimi update HT della lega."""
    if data.world is None:
        return {}
    attrs: dict[str, Any] = {
        "stagione": data.world.season,
        "paesi": data.world.countries,
    }
    league = data.world.league(data.team.league_id)
    if league is not None:
        attrs["prossimo_training"] = htt_to_aware(league.training_date).isoformat()
        attrs["prossima_economy"] = htt_to_aware(league.economy_date).isoformat()
        attrs["prossima_giornata"] = htt_to_aware(league.series_match_date).isoformat()
        attrs["prossima_coppa"] = htt_to_aware(league.cup_match_date).isoformat()
    return attrs


@dataclass(frozen=True, kw_only=True)
class HattrickSensorEntityDescription(SensorEntityDescription):
    """Descrizione di un sensor Hattrick con funzioni per stato e attributi."""

    value_fn: Callable[[HattrickData], StateValue]
    attrs_fn: Callable[[HattrickData], dict[str, Any]] | None = None


SENSORS: tuple[HattrickSensorEntityDescription, ...] = (
    HattrickSensorEntityDescription(
        key="team_name",
        translation_key="team_name",
        icon="mdi:shield",
        value_fn=lambda data: data.team.team_name,
        attrs_fn=lambda data: {
            "team_id": data.team.team_id,
            "lega": data.team.league_name,
            "regione": data.team.region_name,
            "allenatore": data.team.coach_name,
            "livello_allenatore": data.team.coach_level,
        },
    ),
    HattrickSensorEntityDescription(
        key="morale",
        translation_key="morale",
        icon="mdi:emoticon",
        value_fn=lambda data: data.mood.morale,
    ),
    HattrickSensorEntityDescription(
        key="fiducia_tifosi",
        translation_key="fiducia_tifosi",
        icon="mdi:account-group",
        value_fn=lambda data: data.mood.confidence,
    ),
    HattrickSensorEntityDescription(
        key="cassa",
        translation_key="cassa",
        icon="mdi:cash",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.economy.cash,
        attrs_fn=lambda data: {
            "cassa_prevista": data.economy.expected_cash,
            "sponsor": data.economy.sponsors,
        },
    ),
    HattrickSensorEntityDescription(
        key="giocatori",
        translation_key="giocatori",
        icon="mdi:account-multiple",
        value_fn=lambda data: len(data.players.players) if data.players else None,
        attrs_fn=lambda data: (
            {
                "giocatori": [
                    {
                        "id": p.player_id,
                        "nome": p.full_name,
                        "ruolo": p.role,
                        "eta": p.age,
                        "forma": p.form,
                        "tsi": p.tsi,
                        "stipendio": p.salary,
                        "infortunio_settimane": p.injury_weeks,
                        "squalificato": p.suspended,
                        "specialita": p.specialty_label,
                    }
                    for p in data.players.players
                ]
            }
            if data.players
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="tsi_totale",
        translation_key="tsi_totale",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.players.tsi_total if data.players else None,
        attrs_fn=lambda data: {
            "tsi_medio": round(data.players.tsi_total / len(data.players.players), 0)
            if data.players and data.players.players
            else 0,
            "eta_media": round(data.players.avg_age, 1) if data.players else 0,
        },
    ),
    HattrickSensorEntityDescription(
        key="infortunati",
        translation_key="infortunati",
        icon="mdi:bandage",
        value_fn=lambda data: len(data.players.injured) if data.players else None,
        attrs_fn=lambda data: (
            {
                "infortunati": [
                    {"id": p.player_id, "nome": p.full_name, "settimane": p.injury_weeks}
                    for p in data.players.injured
                ]
            }
            if data.players
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="squalificati",
        translation_key="squalificati",
        icon="mdi:card-remove",
        value_fn=lambda data: len(data.players.suspended) if data.players else None,
        attrs_fn=lambda data: (
            {
                "squalificati": [
                    {"id": p.player_id, "nome": p.full_name, "cartellini": p.cards}
                    for p in data.players.suspended
                ]
            }
            if data.players
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="forma_squadra",
        translation_key="forma_squadra",
        icon="mdi:heart-pulse",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: round(data.players.avg_form, 2) if data.players else None,
        attrs_fn=lambda data: (
            {"forma_per_reparto": data.players.form_by_role} if data.players else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="fanclub",
        translation_key="fanclub",
        icon="mdi:account-heart",
        value_fn=lambda data: data.club.fanclub_size if data.club else None,
        attrs_fn=lambda data: {"nome_fanclub": data.club.fanclub_name} if data.club else {},
    ),
    HattrickSensorEntityDescription(
        key="settore_giovanile",
        translation_key="settore_giovanile",
        icon="mdi:school",
        value_fn=lambda data: data.club.youth_level if data.club else None,
        attrs_fn=lambda data: {"nome_giovanile": data.club.youth_name} if data.club else {},
    ),
    HattrickSensorEntityDescription(
        key="staff",
        translation_key="staff",
        icon="mdi:briefcase",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: len(data.club.staff) if data.club else None,
        attrs_fn=lambda data: (
            {
                s.staff_type_label: {"nome": s.name, "livello": s.level, "costo": s.cost}
                for s in data.club.staff
            }
            if data.club
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="posizione",
        translation_key="posizione",
        icon="mdi:podium",
        value_fn=lambda data: data.league.position if data.league else None,
        attrs_fn=lambda data: (
            {
                "lega": data.team.league_name,
                "girone": data.league.league_level_unit_name,
                "livello": data.league.league_level,
                "giornata": data.league.current_round,
                "numero_squadre": data.league.max_teams,
            }
            if data.league
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="prossima_partita",
        translation_key="prossima_partita",
        icon="mdi:calendar-clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: (
            htt_to_aware(data.matches.next_match.date)
            if data.matches and data.matches.next_match
            else None
        ),
        attrs_fn=lambda data: (
            {
                "match_id": data.matches.next_match.match_id,
                "avversario": data.matches.next_match.opponent(data.team.team_id),
                "casa_trasferta": "casa"
                if data.matches.next_match.is_home(data.team.team_id)
                else "trasferta",
                "tipo": data.matches.next_match.match_type_label,
                "stadio": data.matches.next_match.arena_name,
            }
            if data.matches and data.matches.next_match
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="ultima_partita",
        translation_key="ultima_partita",
        icon="mdi:scoreboard",
        value_fn=lambda data: (
            data.matches.last_match.score(data.team.team_id)
            if data.matches and data.matches.last_match
            else None
        ),
        attrs_fn=lambda data: (
            {
                "match_id": data.matches.last_match.match_id,
                "avversario": data.matches.last_match.opponent(data.team.team_id),
                "data": htt_to_aware(data.matches.last_match.date).isoformat(),
                "tipo": data.matches.last_match.match_type_label,
                "casa_trasferta": "casa"
                if data.matches.last_match.is_home(data.team.team_id)
                else "trasferta",
            }
            if data.matches and data.matches.last_match
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="partite_programmate",
        translation_key="partite_programmate",
        icon="mdi:calendar-multiple",
        value_fn=lambda data: len(data.matches.upcoming) if data.matches else None,
        attrs_fn=lambda data: (
            {
                "prossime": [
                    {
                        "data": htt_to_aware(m.date).isoformat(),
                        "avversario": m.opponent(data.team.team_id),
                        "casa_trasferta": "casa" if m.is_home(data.team.team_id) else "trasferta",
                        "tipo": m.match_type_label,
                        "match_id": m.match_id,
                    }
                    for m in data.matches.upcoming[:5]
                ]
            }
            if data.matches
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="entrate_previste",
        translation_key="entrate_previste",
        icon="mdi:cash-plus",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.economy.expected_cash,
        attrs_fn=lambda data: {
            "sponsor": data.economy.sponsors,
            "stipendi": data.economy.wages,
        },
    ),
    HattrickSensorEntityDescription(
        key="stipendi",
        translation_key="stipendi",
        icon="mdi:cash-minus",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.economy.wages,
    ),
    HattrickSensorEntityDescription(
        key="allenatore",
        translation_key="allenatore",
        icon="mdi:whistle",
        value_fn=lambda data: data.team.coach_name,
        attrs_fn=lambda data: {"livello": data.team.coach_level},
    ),
    HattrickSensorEntityDescription(
        key="allenamento",
        translation_key="allenamento",
        icon="mdi:dumbbell",
        value_fn=lambda data: data.training.training_type_label if data.training else None,
        attrs_fn=lambda data: (
            {
                "tipo": data.training.training_type,
                "intensita": data.training.training_intensity,
                "parte_stamina": data.training.stamina_part,
            }
            if data.training
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="progresso_allenamento",
        translation_key="progresso_allenamento",
        icon="mdi:chart-timeline-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            data.training_summary.last_week.training_type_label
            if data.training_summary and data.training_summary.last_week
            else None
        ),
        attrs_fn=lambda data: (
            {
                "settimane": [
                    {
                        "stagione": w.season,
                        "settimana": w.week,
                        "tipo": w.training_type_label,
                        "intensita": w.training_intensity,
                    }
                    for w in data.training_summary.weeks
                ]
            }
            if data.training_summary
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="stadio",
        translation_key="stadio",
        icon="mdi:stadium",
        value_fn=lambda data: data.arena.total_capacity if data.arena else None,
        attrs_fn=lambda data: (
            {
                "nome": data.arena.arena_name,
                "arena_id": data.arena.arena_id,
                "settori": data.arena.sectors,
            }
            if data.arena
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="server_time",
        translation_key="server_time",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: htt_to_aware(data.world.server_time) if data.world else None,
        attrs_fn=_world_attrs,
    ),
    HattrickSensorEntityDescription(
        key="dettaglio_ultima_partita",
        translation_key="dettaglio_ultima_partita",
        icon="mdi:chart-box",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (
            sum(data.match_details.home_ratings.values()) if data.match_details else None
        ),
        attrs_fn=lambda data: (
            {
                "match_id": data.match_details.match_id,
                "data": htt_to_aware(data.match_details.match_date).isoformat(),
                "casa": data.match_details.home_name,
                "trasferta": data.match_details.away_name,
                "risultato": f"{data.match_details.home_goals}-{data.match_details.away_goals}",
                "possesso_casa": data.match_details.possession_home,
                "tiri_casa": data.match_details.shots_home,
                "tiri_trasferta": data.match_details.shots_away,
                "rating_casa": data.match_details.home_ratings,
                "rating_trasferta": data.match_details.away_ratings,
                "meteo": data.match_details.weather,
                "stadio": data.match_details.arena_name,
                "spettatori": data.match_details.sold_total,
                "arbitro": data.match_details.referee_name,
            }
            if data.match_details
            else {}
        ),
    ),
    HattrickSensorEntityDescription(
        key="tattica_ultima_partita",
        translation_key="tattica_ultima_partita",
        icon="mdi:strategy",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.match_lineup.tactic_label if data.match_lineup else None,
        attrs_fn=lambda data: (
            {
                "match_id": data.match_lineup.match_id,
                "formazione": data.match_lineup.formation,
                "tattica": data.match_lineup.tactic_label,
                "livello_tattica": data.match_lineup.tactic_skill,
                "rating": data.match_lineup.ratings,
            }
            if data.match_lineup
            else {}
        ),
    ),
)


class HattrickSensor(HattrickEntity, SensorEntity):
    """Sensor Hattrick generico guidato dalla descrizione."""

    entity_description: HattrickSensorEntityDescription

    def __init__(
        self,
        coordinator: HattrickDataUpdateCoordinator,
        description: HattrickSensorEntityDescription,
    ) -> None:
        """Inizializza il sensor con unique_id stabile."""
        super().__init__(coordinator)
        self.entity_description = description
        team_id = coordinator.data.team.team_id
        self._attr_unique_id = f"{team_id}_{description.key}"

    @property
    def native_value(self) -> StateValue:
        """Valore corrente del sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Attributi aggiuntivi del sensor."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea i sensor dalla config entry."""
    coordinator: HattrickDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(HattrickSensor(coordinator, desc) for desc in SENSORS)
