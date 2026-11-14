"""Costanti dell'integrazione Hattrick."""

from datetime import timedelta

DOMAIN = "hattrick"

# Endpoint CHPP (vedi docs/02-chpp-api.md)
CHPP_BASE_URL = "https://chpp.hattrick.org"
CHPP_XML_URL = f"{CHPP_BASE_URL}/chppxml.ashx"
OAUTH_REQUEST_TOKEN_URL = f"{CHPP_BASE_URL}/oauth/requesttoken.aspx"
OAUTH_AUTHORIZE_URL = f"{CHPP_BASE_URL}/oauth/authorize.aspx"
OAUTH_ACCESS_TOKEN_URL = f"{CHPP_BASE_URL}/oauth/accesstoken.aspx"

# Chiavi di configurazione (config entry / options)
CONF_CONSUMER_KEY = "consumer_key"
CONF_CONSUMER_SECRET = "consumer_secret"
CONF_ACCESS_TOKEN = "access_token"
CONF_ACCESS_TOKEN_SECRET = "access_token_secret"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLED_FILES = "enabled_files"
CONF_MATCHDAY = "matchday"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)
MIN_SCAN_INTERVAL = timedelta(minutes=5)
MAX_SCAN_INTERVAL = timedelta(minutes=60)

# Modalità matchday: polling ridotto dentro la finestra di partita (HTT).
MATCHDAY_INTERVAL = timedelta(minutes=5)
MATCHDAY_WINDOW = timedelta(hours=3)

# File CHPP scaricati nel ciclo standard del coordinator.
# Le versioni sono quelle dichiarate dalla wiki CHPP: da riconfermare a ogni
# aggiornamento della documentazione ufficiale (devblog.hattrick.org).
FILE_VERSIONS: dict[str, str] = {
    "teamdetails": "3.6",
    "team": "1.5",
    "club": "1.5",
    "economy": "1.5",
    "players": "3.0",
    "training": "1.8",
    "trainingsummary": "1.5",
    "leaguedetails": "2.5",
    "matches": "3.0",
    "arenadetails": "1.5",
    "worlddetails": "1.2",
}

# File disponibili ma non nel ciclo standard (on-demand o opzionali)
OPTIONAL_FILES: tuple[str, ...] = (
    "matchdetails",
    "matchlineup",
    "matchesarchive",
    "cup",
    "cups",
    "alliances",
)

DEFAULT_ENABLED_FILES: tuple[str, ...] = tuple(FILE_VERSIONS)
