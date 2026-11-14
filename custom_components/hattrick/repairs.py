"""Repairs flow: token CHPP revocato -> riapre la reauth della config entry."""

from __future__ import annotations

from typing import Any

from homeassistant.components.repairs.models import RepairsFlow
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.core import HomeAssistant

from .const import DOMAIN


class HattrickReauthRepairFlow(RepairsFlow):
    """Fix flow che riavvia il flusso di re-auth OAuth per la entry coinvolta."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Delega alla reauth della config entry indicata nell'issue."""
        entry_id = (self.data or {}).get("entry_id")
        return await self.hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry_id},
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, Any]
) -> RepairsFlow:
    """Crea il fix flow per un'issue fixable del dominio hattrick."""
    return HattrickReauthRepairFlow()
