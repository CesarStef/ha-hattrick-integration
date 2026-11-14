# 10 — Handoff: stato attuale e come riprendere in una nuova sessione

Documento di passaggio: fotografa lo stato del repo al **2026-11-14** e dice
esattamente da dove ripartire. Aggiornarlo a ogni milestone.

## 1. Stato del repository

- Branch `main`, remote `origin` = `https://github.com/CesarStef/ha-hattrick-integration.git`
- Ultimo commit su main: `38f17e4` (pushato). Tag `v0.1.0` pushato.
- **Milestone M1 completata**: documentazione (docs/01–09), scheletro
  `custom_components/hattrick/`, client CHPP, coordinator, config flow completo,
  4 sensor base, CI hassfest+HACS, 26 test verdi, coverage 90%.

```
ha-hattrick-integration/
├── README.md
├── hacs.json
├── pyproject.toml                 # ruff (py313, line-length 100) + pytest
├── requirements_test.txt          # ruff, pytest, pytest-asyncio, pytest-cov,
│                                  #   pytest-homeassistant-custom-component, requests-oauthlib
├── .github/workflows/             # hassfest.yaml, hacs.yaml
├── custom_components/hattrick/
│   ├── manifest.json              # domain hattrick, config_flow, cloud_polling, version 0.1.0
│   ├── const.py                   # endpoint CHPP, CONF_*, FILE_VERSIONS, intervalli
│   ├── api.py                     # HattrickCHPPClient (OAuth 1.0a) + HattrickApiError/AuthError
│   ├── models.py                  # Team, TeamMood, Economy, HattrickData + parser XML
│   ├── coordinator.py             # HattrickDataUpdateCoordinator (teamdetails/team/economy)
│   ├── config_flow.py             # auto OAuth / manuale / reauth / options flow
│   ├── entity.py                  # HattrickEntity + device_info squadra
│   ├── sensor.py                  # sensor: team_name, morale, fiducia_tifosi, cassa
│   ├── __init__.py                # setup/unload entry, client+coordinator, PLATFORMS=[SENSOR]
│   ├── strings.json
│   └── translations/{en,it}.json
├── docs/                          # 01-09 documentazione + piano, 10 questo handoff
└── tests/
    ├── conftest.py                # sys.path + auto_enable_custom_integrations
    ├── fixtures/                  # teamdetails.xml, team.xml, economy.xml, error_auth.xml
    ├── test_api.py                # 8 test client CHPP
    ├── test_models.py             # 4 test parsing
    ├── test_coordinator.py        # 3 test coordinator
    ├── test_config_flow.py        # 8 test config flow + options
    └── test_sensor.py             # 3 test sensor/device
```

Commit recenti:

```
38f17e4 T9+T10: traduzioni verificate e coverage M1 (tag v0.1.0)
67a1933 T8: sensor base + setup entry completo con device squadra
bfc6789 T7: config flow completo (auto OAuth, manuale, reauth, opzioni)
d9e7657 T6: DataUpdateCoordinator con gestione auth/api error
dea2a72 T5 fix: parse_htt_datetime tollerante
f693913 T5: modello dati (models.py)
f35263d T4: client CHPP OAuth 1.0a in api.py
a7c3a6e T3: scheletro custom integration
fdb0b1c T2: CI hassfest + HACS
571cf9b T1: setup repo
```

## 2. Ambiente di test (da ricreare: `/tmp` viene pulito tra sessioni)

```bash
cd /Users/stefanocattonar/Repositories/ha-hattrick-integration
python3 -m venv /tmp/ht-venv
/tmp/ht-venv/bin/pip install -r requirements_test.txt homeassistant \
    pytest-homeassistant-custom-component requests-oauthlib pytest-cov pyyaml
```

Su Python 3.12 pip risolve **HA 2025.1.4** + **pytest-homeassistant-custom-component
0.13.205** (ultime compatibili con 3.12). In produzione l'integrazione gira su
HA 2025.1+ (vedi `hacs.json`); il target di pyproject è py313 (HA 2026).

## 3. Comandi rapidi

```bash
/tmp/ht-venv/bin/ruff check . && /tmp/ht-venv/bin/ruff format .
/tmp/ht-venv/bin/pytest -q                                        # 26 test
/tmp/ht-venv/bin/pytest -q --cov=custom_components/hattrick --cov-report=term-missing
```

Baseline attesa: **26 passed**, coverage ~90%.

## 4. Cosa è già implementato (mappa rápida)

- `api.py`: flusso OAuth 3-legged (`get_request_token_sync`, `get_authorize_url`,
  `get_access_token_sync`) + `get_file_sync`/`async_get_file` per i file XML CHPP;
  gestione 401/403 → `HattrickAuthError`, 429 → `HattrickApiError`, `<Error>` XML.
  Il modulo è indipendente da HA (eccezioni proprie).
- `models.py`: dataclass con `from_xml` tollerante; `parse_htt_datetime` (formato
  HTT `yyyy-MM-dd HH:mm:ss`, vuota → `datetime.min`).
- `coordinator.py`: scarica `teamdetails`, `team`, `economy` e assembla
  `HattrickData`; `HattrickAuthError` → `ConfigEntryAuthFailed`, altro → `UpdateFailed`.
- `config_flow.py`: step `user` (scelta auto/manuale), `manual` (4 credenziali),
  `auth` (mostra URL authorize + campo verifier), `reauth`/`reauth_confirm`,
  options flow (`scan_interval` 5–60 min, `enabled_files`). Validazione via
  `teamdetails.xml`, `unique_id = UserID`, abort su doppioni.
- `sensor.py`: 4 sensor con `unique_id = {team_id}_{key}`, device "squadra"
  (`identifiers={(DOMAIN, team_id)}`).
- Nota HA 2025.1: `OptionsFlowWithConfigEntry` va istanziato con
  `HattrickOptionsFlow(config_entry)` in `async_get_options_flow`.

## 5. Cosa resta da fare (prossimi passi, in ordine)

1. **T11 (M2)**: parsing esteso in `models.py`/`api.py` per `players`,
   `leaguedetails`, `matches`, `training`, `trainingsummary`, `arenadetails`,
   `club`, `world` + fixture XML in `tests/fixtures/` + test in `test_models.py`.
   Commit: `T11: ...`
2. **T12–T14 (M2)**: sensor rosa (giocatori/TSI/infortunati/squalificati),
   classifica e partite (posizione, prossima/ultima partita), allenamento e
   stadio. Aggiungere le chiavi in `SENSORS` + `strings.json`/`translations`.
3. **T15 (M2)**: options flow già partly fatto; manca la **modalità matchday**
   (polling 5 min nelle finestre partita HTT) nel coordinator.
4. **M3 (T16–T18)**: servizi `hattrick.get_match_details` / `get_player`
   (con `supports_response`), sensor diagnostici partita, matchday.
5. **M4 (T19–T20)**: servizio `hattrick.set_match_orders` (POST `matchorders.xml`,
   richiede permesso scrittura sull'app CHPP), `hattrick.refresh`,
   `services.yaml` + `icons.json`.
6. **M5–M8**: dashboard/esempi, test suite completa, release HACS v1.0.0,
   certificazione CHPP — vedi `docs/09-piano-di-lavoro.md`.

## 6. Attenzioni e note tecniche

- `FILE_VERSIONS` in `const.py` contiene versioni **stimate**: riconfermarle
  contro la wiki CHPP (wiki.hattrick.org, categoria "CHPP XML Pages") prima di
  affidarsi ai dati reali.
- Le date CHPP sono in HTT (Europe/Stockholm): convertire con `zoneinfo` prima
  di esporle nei sensor.
- Rispetto limiti CHPP: polling default 15 min, backoff su 429, niente scraping
  (solo `chppxml.ashx`), mai salvare password utente, mai loggare token/secret.
- I test patchano `HattrickCHPPClient` a livello di modulo
  (`custom_components.hattrick` per `__init__`, `...config_flow` per il flow) con
  client finti che leggono `tests/fixtures/*.xml`.
- `hassfest` gira solo in CI (action GitHub); in locale si valida con
  `ruff`, `pytest` e controllo manuale dell'ordinamento chiavi in `manifest.json`.

## 7. Regole di sessione attive

- **Un commit su `main` per ogni avanzamento** (task completato); push su
  `origin` autorizzato in questa sessione.
- Tag SemVer (`vX.Y.Z`) a ogni milestone; HACS installa le release, non main.
- Tutti i testi UI in `strings.json` + `translations/` (niente hardcoded).
- Lingua delle risposte e dei testi generati: **italiano**.

## 8. Come riprendere

Chiedere: *"procedi con T11"* (o l'ultimo task in sospeso). Ricostruire il venv
(sezione 2), lanciare `pytest -q` per confermare la baseline 26 passed, poi
lavorare al task e committare.
