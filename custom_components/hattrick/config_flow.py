"""Config flow dell'integrazione Hattrick.

Flusso completo (OAuth automatico + manuale + reauth) implementato nel task T7.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN

DATA_SCHEMA = vol.Schema({vol.Required("placeholder"): str})


class HattrickConfigFlow(ConfigFlow, domain=DOMAIN):
    """Gestisce il config flow di Hattrick."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Passo iniziale (placeholder, completato nel task T7)."""
        if user_input is not None:
            return self.async_create_entry(title="Hattrick", data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)
