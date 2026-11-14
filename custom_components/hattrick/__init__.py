"""Integrazione Hattrick per Home Assistant."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import HattrickCHPPClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_SECRET,
    CONF_CONSUMER_KEY,
    CONF_CONSUMER_SECRET,
    CONF_ENABLED_FILES,
    CONF_MATCHDAY,
    CONF_SCAN_INTERVAL,
    DEFAULT_ENABLED_FILES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import HattrickDataUpdateCoordinator
from .services import async_setup_services, async_unload_services

PLATFORMS: list[Platform] = [Platform.SENSOR]

type HattrickConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: HattrickConfigEntry) -> bool:
    """Configura l'integrazione dalla config entry."""
    client = HattrickCHPPClient(
        entry.data[CONF_CONSUMER_KEY],
        entry.data[CONF_CONSUMER_SECRET],
        entry.data[CONF_ACCESS_TOKEN],
        entry.data[CONF_ACCESS_TOKEN_SECRET],
    )
    interval_minutes = entry.options.get(
        CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60)
    )
    enabled_files = entry.options.get(CONF_ENABLED_FILES, list(DEFAULT_ENABLED_FILES))
    matchday = entry.options.get(CONF_MATCHDAY, False)
    coordinator = HattrickDataUpdateCoordinator(
        hass,
        entry,
        client,
        update_interval=timedelta(minutes=interval_minutes),
        enabled_files=enabled_files,
        matchday=matchday,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HattrickConfigEntry) -> bool:
    """Rimuove l'integrazione."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        await async_unload_services(hass)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: HattrickConfigEntry) -> None:
    """Ricarica l'entry quando cambiano le opzioni."""
    await hass.config_entries.async_reload(entry.entry_id)
