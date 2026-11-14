"""Piattaforma sensor dell'integrazione Hattrick (fase M1: sensor base)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HattrickDataUpdateCoordinator
from .entity import HattrickEntity
from .models import HattrickData

StateValue = str | int | float | None


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
