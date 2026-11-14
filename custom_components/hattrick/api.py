"""Client per le API CHPP di Hattrick (OAuth 1.0a).

Questo modulo è volutamente independiente da Home Assistant: usa solo
`requests`/`requests-oauthlib` e solleva eccezioni proprie. Il coordinator
(T6) le traduce in `UpdateFailed` / `ConfigEntryAuthFailed`.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from functools import partial
from typing import TYPE_CHECKING, Any

import requests
from requests_oauthlib import OAuth1Session

from .const import (
    CHPP_XML_URL,
    FILE_VERSIONS,
    OAUTH_ACCESS_TOKEN_URL,
    OAUTH_AUTHORIZE_URL,
    OAUTH_REQUEST_TOKEN_URL,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class HattrickApiError(Exception):
    """Errore generico restituito dalle API CHPP."""


class HattrickAuthError(HattrickApiError):
    """Errore di autenticazione: token non valido o revocato (serve reauth)."""


class HattrickCHPPClient:
    """Client OAuth 1.0a per i file XML di CHPP."""

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str = "",
        access_token_secret: str = "",
    ) -> None:
        """Crea il client. Senza access token serve solo per il flusso OAuth."""
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._session = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token or None,
            resource_owner_secret=access_token_secret or None,
        )

    # ------------------------------------------------------------------
    # Flusso OAuth 1.0a a tre zampe (usato dal config flow, task T7)
    # ------------------------------------------------------------------

    def get_request_token_sync(self, callback_url: str = "oob") -> tuple[str, str]:
        """Passo 1: ottiene request token e request token secret."""
        session = OAuth1Session(
            self._consumer_key,
            client_secret=self._consumer_secret,
            callback_uri=callback_url,
        )
        try:
            token = session.fetch_request_token(OAUTH_REQUEST_TOKEN_URL, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as err:
            raise HattrickApiError(f"Errore nel richiedere il request token: {err}") from err
        return token["oauth_token"], token["oauth_token_secret"]

    @staticmethod
    def get_authorize_url(request_token: str) -> str:
        """URL a cui l'utente deve andare per autorizzare l'app su Hattrick."""
        return f"{OAUTH_AUTHORIZE_URL}?oauth_token={request_token}"

    def get_access_token_sync(
        self, request_token: str, request_token_secret: str, verifier: str
    ) -> tuple[str, str]:
        """Passo 3: scambia request token + verifier con l'access token."""
        session = OAuth1Session(
            self._consumer_key,
            client_secret=self._consumer_secret,
            resource_owner_key=request_token,
            resource_owner_secret=request_token_secret,
            verifier=verifier,
        )
        try:
            token = session.fetch_access_token(OAUTH_ACCESS_TOKEN_URL, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as err:
            raise HattrickAuthError(f"Verifier non valido o scaduto: {err}") from err
        return token["oauth_token"], token["oauth_token_secret"]

    # ------------------------------------------------------------------
    # Lettura dei file XML CHPP
    # ------------------------------------------------------------------

    def get_file_sync(self, file: str, **params: Any) -> ET.Element:
        """Scarica un file CHPP (bloccante) e restituisce la root dell'XML.

        Solleva HattrickAuthError se le credenziali non sono valide,
        HattrickApiError per ogni altro errore.
        """
        version = params.pop("version", None) or FILE_VERSIONS.get(file, "1.0")
        query: dict[str, Any] = {"file": file, "version": version, **params}
        try:
            resp = self._session.get(CHPP_XML_URL, params=query, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as err:
            raise HattrickApiError(f"Errore di rete verso CHPP: {err}") from err

        if resp.status_code in (401, 403):
            raise HattrickAuthError("Credenziali CHPP non valide o token revocato")
        if resp.status_code == 429:
            raise HattrickApiError("Limite di download CHPP superato (HTTP 429)")
        if resp.status_code != 200:
            raise HattrickApiError(f"CHPP ha risposto con HTTP {resp.status_code}")

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as err:
            raise HattrickApiError(f"XML non valido ricevuto da CHPP: {err}") from err

        error = root.findtext("Error")
        if error:
            lowered = error.lower()
            if "token" in lowered or "auth" in lowered or "verifier" in lowered:
                raise HattrickAuthError(error)
            raise HattrickApiError(error)
        return root

    async def async_get_file(self, hass: HomeAssistant, file: str, **params: Any) -> ET.Element:
        """Versione async di get_file_sync, eseguita in executor."""
        return await hass.async_add_executor_job(partial(self.get_file_sync, file, **params))
