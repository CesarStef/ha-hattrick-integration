"""Test del config flow (modalità manuale, automatica, reauth, opzioni)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import pytest
from homeassistant.config_entries import SOURCE_REAUTH, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hattrick.api import HattrickAuthError
from custom_components.hattrick.const import (
    CONF_ACCESS_TOKEN,
    CONF_ACCESS_TOKEN_SECRET,
    CONF_CONSUMER_KEY,
    CONF_CONSUMER_SECRET,
    DOMAIN,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

MANUAL_DATA = {
    CONF_CONSUMER_KEY: "ck",
    CONF_CONSUMER_SECRET: "cs",
    CONF_ACCESS_TOKEN: "at",
    CONF_ACCESS_TOKEN_SECRET: "ats",
}


class FakeCHPPClient:
    """Client CHPP finto per i test del flusso."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    async def async_get_file(self, hass, file: str, **params):
        return ET.fromstring((FIXTURES_DIR / "teamdetails.xml").read_text(encoding="utf-8"))

    def get_request_token_sync(self, callback_url: str = "oob"):
        return ("reqtok", "reqsec")

    @staticmethod
    def get_authorize_url(request_token: str) -> str:
        return f"https://chpp.hattrick.org/oauth/authorize.aspx?oauth_token={request_token}"

    def get_access_token_sync(self, request_token, request_token_secret, verifier):
        if verifier != "good":
            raise HattrickAuthError("verifier non valido")
        return ("newat", "newats")


@pytest.fixture
def mock_client():
    with mock.patch("custom_components.hattrick.config_flow.HattrickCHPPClient", FakeCHPPClient):
        yield


async def test_user_step_shows_form(hass, mock_client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_manual_flow_creates_entry(hass, mock_client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": "manual"})
    assert result["step_id"] == "manual"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], MANUAL_DATA)
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Squadra di Test"
    assert result["data"][CONF_ACCESS_TOKEN] == "at"
    assert result["result"].unique_id == "1234567"


async def test_manual_flow_invalid_auth(hass):
    class BadClient(FakeCHPPClient):
        async def async_get_file(self, hass, file, **params):
            raise HattrickAuthError("token revocato")

    with mock.patch("custom_components.hattrick.config_flow.HattrickCHPPClient", BadClient):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"mode": "manual"}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], MANUAL_DATA)
        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_auth"


async def test_auto_flow_creates_entry(hass, mock_client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": "auto"})
    assert result["step_id"] == "app"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONSUMER_KEY: "ck", CONF_CONSUMER_SECRET: "cs"}
    )
    assert result["step_id"] == "auth"
    assert (
        "authorize.aspx?oauth_token=reqtok" in result["description_placeholders"]["authorize_url"]
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"verifier": "good"})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Squadra di Test"
    assert result["data"][CONF_ACCESS_TOKEN] == "newat"
    assert result["data"][CONF_CONSUMER_KEY] == "ck"


async def test_auto_flow_bad_verifier(hass, mock_client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": "auto"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CONSUMER_KEY: "ck", CONF_CONSUMER_SECRET: "cs"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"verifier": "bad"})
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_verifier"


async def test_auto_flow_request_token_denied_shows_error_not_crash(hass):
    class DeniedClient(FakeCHPPClient):
        def get_request_token_sync(self, callback_url: str = "oob"):
            raise HattrickAuthError("CHPP ha rifiutato il request token")

    with mock.patch("custom_components.hattrick.config_flow.HattrickCHPPClient", DeniedClient):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": "auto"})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_CONSUMER_KEY: "bad", CONF_CONSUMER_SECRET: "bad"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "auth"
        assert result["errors"]["base"] == "invalid_auth"


async def test_duplicate_account_aborts(hass, mock_client):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1234567", data=MANUAL_DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": "manual"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], MANUAL_DATA)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(hass, mock_client):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1234567", data=MANUAL_DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"verifier": "good"})
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_ACCESS_TOKEN] == "newat"


async def test_options_flow(hass, mock_client):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="1234567", data=MANUAL_DATA)
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "scan_interval": 30,
            "enabled_files": ["teamdetails", "economy"],
            "matchday": True,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["scan_interval"] == 30
    assert result["data"]["enabled_files"] == ["teamdetails", "economy"]
    assert result["data"]["matchday"] is True
