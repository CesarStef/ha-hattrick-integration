"""Integrazione Hattrick per Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = []

type HattrickConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: HattrickConfigEntry) -> bool:
    """Configura l'integrazione dalla config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HattrickConfigEntry) -> bool:
    """Rimuove l'integrazione."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
