"""Config flow dell'integrazione Hattrick.

Due modalità di autenticazione (vedi docs/06-configurazione-utente.md):
- "auto": flusso OAuth 3-legged guidato (request token -> authorize URL -> verifier)
- "manual": l'utente incolla le 4 credenziali ottenute da chpp.hattrick.org
Più il flusso di reauth quando il token viene revocato.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithConfigEntry,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .api import HattrickApiError, HattrickAuthError, HattrickCHPPClient
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
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .models import Team

_LOGGER = logging.getLogger(__name__)

MODE_AUTO = "auto"
MODE_MANUAL = "manual"

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required("mode", default=MODE_AUTO): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[MODE_AUTO, MODE_MANUAL],
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="auth_mode",
            )
        )
    }
)

MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONSUMER_KEY): str,
        vol.Required(CONF_CONSUMER_SECRET): str,
        vol.Required(CONF_ACCESS_TOKEN): str,
        vol.Required(CONF_ACCESS_TOKEN_SECRET): str,
    }
)

VERIFIER_SCHEMA = vol.Schema({vol.Required("verifier"): str})


class CannotConnect(HomeAssistantError):
    """Impossibile connettersi a CHPP."""


class InvalidAuth(HomeAssistantError):
    """Credenziali CHPP non valide."""


async def _async_validate_team(
    hass: HomeAssistant,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_token_secret: str,
) -> Team:
    """Chiama teamdetails.xml per validare le credenziali e leggere il team."""
    client = HattrickCHPPClient(consumer_key, consumer_secret, access_token, access_token_secret)
    try:
        root = await client.async_get_file(hass, "teamdetails")
    except HattrickAuthError as err:
        raise InvalidAuth(str(err)) from err
    except HattrickApiError as err:
        raise CannotConnect(str(err)) from err
    team = Team.from_xml(root)
    if team.user_id == 0:
        raise InvalidAuth("CHPP non ha restituito uno UserID valido")
    return team


class HattrickConfigFlow(ConfigFlow, domain=DOMAIN):
    """Gestisce il config flow di Hattrick."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> HattrickOptionsFlow:
        """Restituisce il flusso delle opzioni."""
        return HattrickOptionsFlow(config_entry)

    def __init__(self) -> None:
        """Stato temporaneo del flusso OAuth."""
        self._consumer_key = ""
        self._consumer_secret = ""
        self._request_token = ""
        self._request_token_secret = ""
        self._authorize_url = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Scelta della modalità di autenticazione."""
        if user_input is not None:
            if user_input["mode"] == MODE_MANUAL:
                return await self.async_step_manual()
            return await self.async_step_auth()
        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)

    # ------------------------------------------------------------------
    # Modalità manuale
    # ------------------------------------------------------------------

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """L'utente incolla consumer key/secret e access token/secret."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                team = await _async_validate_team(
                    self.hass,
                    user_input[CONF_CONSUMER_KEY],
                    user_input[CONF_CONSUMER_SECRET],
                    user_input[CONF_ACCESS_TOKEN],
                    user_input[CONF_ACCESS_TOKEN_SECRET],
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(str(team.user_id))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=team.team_name, data=user_input)
        return self.async_show_form(step_id="manual", data_schema=MANUAL_SCHEMA, errors=errors)

    # ------------------------------------------------------------------
    # Modalità automatica (OAuth 3-legged)
    # ------------------------------------------------------------------

    async def _async_ensure_request_token(self, errors: dict[str, str]) -> None:
        """Ottiene il request token da CHPP (passo 1 dell'OAuth)."""
        if self._request_token:
            return
        client = HattrickCHPPClient(self._consumer_key, self._consumer_secret)
        try:
            (
                self._request_token,
                self._request_token_secret,
            ) = await self.hass.async_add_executor_job(client.get_request_token_sync)
        except HattrickApiError as err:
            errors["base"] = "cannot_connect"
            _LOGGER.warning("Impossibile ottenere il request token CHPP: %s", err)
        else:
            self._authorize_url = HattrickCHPPClient.get_authorize_url(self._request_token)

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Mostra l'URL di autorizzazione e raccoglie il verifier."""
        errors: dict[str, str] = {}
        await self._async_ensure_request_token(errors)
        if user_input is not None and not errors:
            client = HattrickCHPPClient(self._consumer_key, self._consumer_secret)
            try:
                access_token, access_token_secret = await self.hass.async_add_executor_job(
                    partial(
                        client.get_access_token_sync,
                        self._request_token,
                        self._request_token_secret,
                        user_input["verifier"],
                    )
                )
            except HattrickAuthError:
                errors["base"] = "invalid_verifier"
            except HattrickApiError:
                errors["base"] = "cannot_connect"
            else:
                try:
                    team = await _async_validate_team(
                        self.hass,
                        self._consumer_key,
                        self._consumer_secret,
                        access_token,
                        access_token_secret,
                    )
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(str(team.user_id))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=team.team_name,
                        data={
                            CONF_CONSUMER_KEY: self._consumer_key,
                            CONF_CONSUMER_SECRET: self._consumer_secret,
                            CONF_ACCESS_TOKEN: access_token,
                            CONF_ACCESS_TOKEN_SECRET: access_token_secret,
                        },
                    )
        return self.async_show_form(
            step_id="auth",
            data_schema=VERIFIER_SCHEMA,
            errors=errors,
            description_placeholders={"authorize_url": self._authorize_url},
        )

    # ------------------------------------------------------------------
    # Reauth (token revocato)
    # ------------------------------------------------------------------

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Riapre il flusso OAuth quando il token viene revocato."""
        self._consumer_key = entry_data[CONF_CONSUMER_KEY]
        self._consumer_secret = entry_data[CONF_CONSUMER_SECRET]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Nuovo verifier -> nuovo access token -> entry aggiornata."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        await self._async_ensure_request_token(errors)
        if user_input is not None and not errors:
            client = HattrickCHPPClient(self._consumer_key, self._consumer_secret)
            try:
                access_token, access_token_secret = await self.hass.async_add_executor_job(
                    partial(
                        client.get_access_token_sync,
                        self._request_token,
                        self._request_token_secret,
                        user_input["verifier"],
                    )
                )
            except HattrickAuthError:
                errors["base"] = "invalid_verifier"
            except HattrickApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={
                        CONF_ACCESS_TOKEN: access_token,
                        CONF_ACCESS_TOKEN_SECRET: access_token_secret,
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=VERIFIER_SCHEMA,
            errors=errors,
            description_placeholders={"authorize_url": self._authorize_url},
        )


class HattrickOptionsFlow(OptionsFlowWithConfigEntry):
    """Opzioni dell'integrazione: intervallo di polling e file abilitati."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Form delle opzioni."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds() // 60)
        )
        current_files = self.config_entry.options.get(
            CONF_ENABLED_FILES, list(DEFAULT_ENABLED_FILES)
        )
        current_matchday = self.config_entry.options.get(CONF_MATCHDAY, False)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current_interval): (
                        selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                min=MIN_SCAN_INTERVAL.total_seconds() // 60,
                                max=MAX_SCAN_INTERVAL.total_seconds() // 60,
                                step=1,
                                unit_of_measurement="min",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        )
                    ),
                    vol.Required(CONF_ENABLED_FILES, default=current_files): (
                        selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=list(DEFAULT_ENABLED_FILES),
                                multiple=True,
                                mode=selector.SelectSelectorMode.LIST,
                            )
                        )
                    ),
                    vol.Required(CONF_MATCHDAY, default=current_matchday): (
                        selector.BooleanSelector()
                    ),
                }
            ),
        )
