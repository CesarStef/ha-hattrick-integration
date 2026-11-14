"""Entità base dell'integrazione Hattrick."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HattrickDataUpdateCoordinator


class HattrickEntity(CoordinatorEntity[HattrickDataUpdateCoordinator]):
    """Entità collegata al coordinator, con device_info della squadra."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HattrickDataUpdateCoordinator) -> None:
        """Inizializza l'entità con il device della squadra."""
        super().__init__(coordinator)
        team = coordinator.data.team
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(team.team_id))},
            name=team.team_name,
            manufacturer="Hattrick",
            model="Squadra",
            configuration_url="https://www.hattrick.org",
        )
