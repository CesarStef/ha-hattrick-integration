# 03 — Architettura della custom integration di Home Assistant

Questo documento descrive la struttura del codice dell'integrazione, i file principali e
il ruolo di ciascuno. Il codice vive in `custom_components/hattrick/`.

Riferimenti ufficiali:

- Developer docs HA: <https://developers.home-assistant.io>
- Blueprint moderno per custom integration: <https://github.com/jpawlowski/ha-integration-blueprint>
- Manifest: <https://developers.home-assistant.io/docs/en/creating_integration_manifest.html>

## 1. Struttura delle cartelle

```
ha-hattrick-integration/
├── README.md
├── hacs.json                          # metadati per HACS
├── docs/                              # questa documentazione
├── custom_components/
│   └── hattrick/
│       ├── __init__.py                # setup/unload della config entry
│       ├── manifest.json              # metadati dell'integrazione
│       ├── const.py                   # costanti, versioni file CHPP, default
│       ├── api.py                     # client CHPP (OAuth1 + XML)
│       ├── models.py                  # dataclass del modello dati
│       ├── coordinator.py             # DataUpdateCoordinator
│       ├── config_flow.py             # flusso di configurazione UI + reauth + options
│       ├── entity.py                  # classe base entità (device_info)
│       ├── sensor.py                  # piattaforma sensor
│       ├── services.py                # registrazione servizi (azioni)
│       ├── services.yaml              # descrizioni dei servizi per la UI
│       ├── strings.json               # testi UI (base, inglese)
│       ├── icons.json                 # icone dei servizi
│       └── translations/
│           ├── en.json
│           └── it.json
├── tests/                             # test automatici (pytest)
│   ├── conftest.py
│   ├── fixtures/                      # XML CHPP di esempio
│   └── test_*.py
└── .github/workflows/
    ├── hassfest.yaml                  # validazione manifest (action ufficiale HA)
    └── hacs.yaml                      # validazione HACS
```

## 2. manifest.json

```json
{
  "domain": "hattrick",
  "name": "Hattrick",
  "codeowners": ["@stefanocattonar"],
  "config_flow": true,
  "documentation": "https://github.com/stefanocattonar/ha-hattrick-integration",
  "integration_type": "hub",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/stefanocattonar/ha-hattrick-integration/issues",
  "requirements": ["requests-oauthlib==2.0.0"],
  "version": "0.1.0"
}
```

Note sulle scelte:

- `domain: "hattrick"` deve corrispondere al nome della cartella e non cambierà mai
  (gli entity_id e le automazioni degli utenti dipendono da esso).
- `config_flow: true`: l'integrazione si configura dalla UI di HA
  (Impostazioni → Dispositivi e servizi → Aggiungi integrazione → "Hattrick").
- `integration_type: "hub"`: una config entry dà accesso a molte entità raggruppate in
  un unico dispositivo (la squadra).
- `iot_class: "cloud_polling"`: parliamo con un servizio cloud (CHPP) a intervalli.
- `requirements`: `requests-oauthlib` pinnato a versione esatta (regola di hassfest).
  `requests` è già presente in HA, non va listed. Le chiamate bloccanti girano in
  executor (vedi `api.py`).
- `version`: obbligatorio per le custom integration (HACS la usa per gli aggiornamenti).
- Le chiavi vanno tenute **ordinate alfabeticamente** dopo `domain` e `name` (hassfest lo
  controlla).

## 3. hacs.json

```json
{
  "name": "Hattrick",
  "render_readme": true,
  "homeassistant": "2025.1.0"
}
```

`homeassistant` indica la versione minima di HA supportata.

## 4. Flusso dei dati (panoramica)

```
config_flow.py  →  crea ConfigEntry con credenziali OAuth (token) e opzioni
        ↓
__init__.py     →  async_setup_entry: crea client API + coordinator, fa primo refresh,
                   registra piattaforme (sensor) e servizi, aggiunge update listener
        ↓
coordinator.py  →  ogni SCAN_INTERVAL chiama client.refresh_all() che scarica i file
                   CHPP, parse XML → dataclass (models.py), aggiorna coordinator.data
        ↓
sensor.py       →  le entità leggono coordinator.data e aggiornano stato/attributi
        ↓
services.py     →  le azioni (es. set_match_orders) chiamano il client in scrittura e
                   poi fanno refresh del coordinator
```

## 5. Descrizione dei moduli

### `const.py`

- `DOMAIN = "hattrick"`
- chiavi di configurazione: `CONF_CONSUMER_KEY`, `CONF_CONSUMER_SECRET`,
  `CONF_ACCESS_TOKEN`, `CONF_ACCESS_TOKEN_SECRET`, `CONF_SCAN_INTERVAL`, ecc.
- `DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)`, `MIN_SCAN_INTERVAL = timedelta(minutes=5)`
- `FILE_VERSIONS`: mappa file CHPP → versione (es. `{"teamdetails": "3.6", ...}`)
- `CHPP_BASE_URL = "https://chpp.hattrick.org"`

### `api.py` — client CHPP

Classe `HattrickCHPPClient`:

- costruita con le 4 credenziali OAuth;
- usa `requests_oauthlib.OAuth1Session`;
- `async_get_file(hass, name, **params)`: wrapper async che esegue la GET in executor
  (`hass.async_add_executor_job`), con timeout e gestione eccezioni;
- metodi di convenience: `get_teamdetails()`, `get_players()`, `get_matches()`,
  `get_economy()`, `get_training()`, `get_leaguedetails()`, `get_matchdetails(match_id)`,
  `get_matchlineup(match_id)`, `get_arena()`, `get_club()`, `get_team()`, `get_world()`;
- `send_match_orders(payload: dict)`: POST a `matchorders` per scrivere gli ordini;
- `parse_xml(text)`: `xml.etree.ElementTree` → dataclass di `models.py`;
- solleva `HattrickAuthError` (→ reauth) e `HattrickApiError` (→ UpdateFailed).

### `models.py` — modello dati

Dataclass pure: `Team`, `User`, `Player`, `Match`, `MatchDetails`, `Economy`, `Training`,
`LeagueStanding`, `Arena`, `Club`, `WorldInfo`, e il contenitore `HattrickData`.
Funzioni `from_xml(element)` per il parsing. Dettagli in `docs/05`.

### `coordinator.py`

`HattrickDataUpdateCoordinator(DataUpdateCoordinator[HattrickData])`:

- `update_method` chiama `client.refresh_all()` che scarica in sequenza i file abilitati
  e assembla `HattrickData`;
- gestisce `HattrickAuthError` → `ConfigEntryAuthFailed`; altri errori → `UpdateFailed`;
- `scan_interval` presa dalle opzioni della config entry (default 15 min);
- espone `last_update_success` e `FetchedDate` per diagnostica.

### `config_flow.py`

- `async_step_user`: scelta modalità — **automatica** (OAuth 3-legged dentro HA) o
  **manuale** (l'utente incolla le 4 credenziali ottenute da chpp.hattrick.org).
- Flusso automatico: `async_step_auth` mostra l'URL `authorize.aspx` (aperto dall'utente
  nel browser) e un campo per il **verifier**; poi scambia verifier → access token.
- Validazione: prima di creare la entry chiama `teamdetails` per verificare token e
  ottenere `UserID`/`TeamID` → `unique_id` della entry (impedisce doppioni).
- `async_step_reauth` / `reauth_confirm`: se il token viene revocato, HA riapre il
  flusso di autorización.
- `OptionsFlow`: intervallo di polling, file CHPP da abilitare/disabilitare, modalità
  "matchday" (polling più frequente nelle finestre partita).

Dettagli del flusso utente in `docs/06`.

### `__init__.py`

- `async_setup_entry`: crea client + coordinator, primo `async_config_entry_first_refresh`,
  `entry.async_on_unload(entry.add_update_listener(...))` per le opzioni,
  `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)` con
  `PLATFORMS = [Platform.SENSOR]`;
- `async_unload_entry`: unload delle piattaforme e rimozione servizi se è l'ultima entry.

### `entity.py`

`HattrickEntity(CoordinatorEntity)` con `device_info`:

```python
DeviceInfo(
    identifiers={(DOMAIN, str(team_id))},
    name=team_name,
    manufacturer="Hattrick",
    model="Squadra",
    configuration_url="https://www.hattrick.org",
)
```

`unique_id` di ogni entità = `f"{team_id}_{chiave}"` (stabile tra i riavvii).

### `sensor.py`

Lista di `SensorEntityDescription` (chiave, nome/traduzione, icona, device_class,
state_class, unità) + classi sensor specifiche. Catalogo completo in `docs/04`.

### `services.py` + `services.yaml`

Registrazione dei servizi del dominio `hattrick` (es. `hattrick.set_match_orders`,
`hattrick.refresh`) con schéma `voluptuous` e selettori; descrizioni in `services.yaml`
per la UI (campi, selettori, esempi). I testi vanno in `strings.json`/`translations`.

### `strings.json` / `translations/*.json`

Tutti i testi rivolti all'utente (config flow, nomi entità, errori, servizi) vivono qui,
mai hardcoded nel codice. Lingue: `en` (base in `strings.json`) e `it`.

## 6. Dipendenze e versione Python

- HA supporta le custom integration in Python; useremo le API stabili di
  `homeassistant` (helpers coordinator, config flow, entity platform).
- `requests-oauthlib` è l'unica dipendenza esterna (pinnata nel manifest).
- Nessun database proprio: lo stato vive nel coordinator e nello `recorder` di HA.

## 7. Convenzioni di codice

- Type hints ovunque; dataclass per il modello.
- Niente testo user-facing nel codice: solo chiavi di traduzione.
- Log con `logging.getLogger(__name__)`; **mai** loggare token, consumer secret o dati
  sensibili (mascherare con `...`).
- Errori utente → eccezioni HA (`HomeAssistantError`, `ConfigEntryAuthFailed`,
  `UpdateFailed`) con `translation_key`.
- Test con `pytest-homeassistant-custom-component` (vedi `docs/07`).
