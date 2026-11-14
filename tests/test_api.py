"""Test del client CHPP (api.py) con risposte XML finte."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest import mock

import pytest

from custom_components.hattrick import api
from custom_components.hattrick.api import (
    HattrickApiError,
    HattrickAuthError,
    HattrickCHPPClient,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class FakeHass:
    """Sostituto minimo di HomeAssistant per testare il wrapper async."""

    async def async_add_executor_job(self, func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)


def _client() -> HattrickCHPPClient:
    return HattrickCHPPClient("ck", "cs", "at", "ats")


def test_get_file_sync_ok():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session = session_cls.return_value
        session.get.return_value = FakeResponse(200, _fixture("teamdetails.xml"))
        root = _client().get_file_sync("teamdetails")
    assert root.findtext("Team/TeamName") == "Squadra di Test"
    assert root.findtext("UserID") == "1234567"
    # la versione del file viene passata da FILE_VERSIONS
    _, kwargs = session.get.call_args
    assert kwargs["params"]["file"] == "teamdetails"
    assert kwargs["params"]["version"] == "3.6"


def test_get_file_sync_http_401_is_auth_error():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.get.return_value = FakeResponse(401, "")
        with pytest.raises(HattrickAuthError):
            _client().get_file_sync("teamdetails")


def test_get_file_sync_http_429_is_api_error():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.get.return_value = FakeResponse(429, "")
        with pytest.raises(HattrickApiError, match="429"):
            _client().get_file_sync("teamdetails")


def test_get_file_sync_xml_error_token_is_auth_error():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.get.return_value = FakeResponse(200, _fixture("error_auth.xml"))
        with pytest.raises(HattrickAuthError):
            _client().get_file_sync("teamdetails")


def test_get_file_sync_xml_error_generic():
    xml = _fixture("teamdetails.xml").replace(
        "</HattrickData>", "<Error>File not authorized for this CHPP app</Error></HattrickData>"
    )
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.get.return_value = FakeResponse(200, xml)
        with pytest.raises(HattrickApiError, match="not authorized"):
            _client().get_file_sync("teamdetails")


def test_get_file_sync_invalid_xml():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.get.return_value = FakeResponse(200, "non è xml")
        with pytest.raises(HattrickApiError, match="XML non valido"):
            _client().get_file_sync("teamdetails")


async def test_async_get_file_uses_executor():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.get.return_value = FakeResponse(200, _fixture("teamdetails.xml"))
        root = await _client().async_get_file(FakeHass(), "teamdetails")
    assert root.findtext("Team/TeamID") == "7654321"


def test_authorize_url():
    url = HattrickCHPPClient.get_authorize_url("tok123")
    assert url == "https://chpp.hattrick.org/oauth/authorize.aspx?oauth_token=tok123"


def test_user_agent_chpp_manual():
    # CHPP Manual: lo user-agent deve indicare programma e versione
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.headers = {}
        client = _client()
    ua = client._session.headers["User-Agent"]
    assert ua.startswith("hattrick-homeassistant/")
    assert "Home Assistant" in ua


def test_get_request_token_sync_wraps_value_error_as_auth_error():
    # requests-oauthlib solleva TokenRequestDenied (ValueError) se CHPP rifiuta
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.fetch_request_token.side_effect = ValueError("denied")
        with pytest.raises(HattrickAuthError):
            _client().get_request_token_sync()


def test_get_access_token_sync_wraps_value_error_as_auth_error():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.fetch_access_token.side_effect = ValueError("denied")
        with pytest.raises(HattrickAuthError):
            _client().get_access_token_sync("rt", "rts", "bad")


def test_post_file_sync_ok():
    ok_xml = (
        '<?xml version="1.0"?><HattrickData><FileName>matchorders</FileName>'
        "<Version>1.0</Version></HattrickData>"
    )
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session = session_cls.return_value
        session.post.return_value = FakeResponse(200, ok_xml)
        body = "<MatchOrders><MatchID>9002</MatchID></MatchOrders>"
        root = _client().post_file_sync("matchorders", body)
    assert root.findtext("FileName") == "matchorders"
    _, kwargs = session.post.call_args
    assert kwargs["params"]["file"] == "matchorders"
    assert b"<MatchID>9002</MatchID>" in kwargs["data"]
    assert kwargs["headers"]["Content-Type"].startswith("application/xml")


def test_post_file_sync_http_403_is_auth_error():
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.post.return_value = FakeResponse(403, "")
        with pytest.raises(HattrickAuthError):
            _client().post_file_sync("matchorders", "<MatchOrders/>")


def test_post_file_sync_xml_error_is_api_error():
    xml = (
        '<?xml version="1.0"?><HattrickData><Error>Match orders not allowed</Error></HattrickData>'
    )
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.post.return_value = FakeResponse(200, xml)
        with pytest.raises(HattrickApiError, match="not allowed"):
            _client().post_file_sync("matchorders", "<MatchOrders/>")


async def test_async_post_file_uses_executor():
    ok_xml = '<?xml version="1.0"?><HattrickData><FileName>matchorders</FileName></HattrickData>'
    with mock.patch.object(api, "OAuth1Session") as session_cls:
        session_cls.return_value.post.return_value = FakeResponse(200, ok_xml)
        root = await _client().async_post_file(FakeHass(), "matchorders", "<MatchOrders/>")
    assert root.findtext("FileName") == "matchorders"
