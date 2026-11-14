# 10 — Handoff: stato attuale e come riprendere in una nuova sessione

Documento di passaggio: fotografa lo stato del repo al **2026-11-14** e dice
esattamente da dove ripartire. Aggiornarlo a ogni milestone.

## 1. Stato del repository

- Branch `main`, remote `origin` = `https://github.com/CesarStef/ha-hattrick-integration.git`
- Ultimo commit su main: `15cec8c` (pushato). Tag `v0.2.0` pushato.
- **Milestone M2 completata**: a M1 si aggiungono parsing esteso (8 file CHPP),
  coordinator multi-file, 17 sensor totali (rosa, club, classifica, partite,
  economia, allenamento, stadio, mondo), options flow con modalità matchday,
  47 test verdi, coverage 93%.

```
ha-hattrick-integration/
├── README.md
├── hacs.json
├── pyproject.toml                 # ruff (py313, line-length 100) + pytest
├── requirements_test.txt          # ruff, pytest, pytest-asyncio, pytest-cov,
│                                  #   pytest-homeassistant-custom-component, requests-oauthlib
├── .github/workflows/             # hassfest.yaml, hacs.yaml
├── custom_components/hattrick/
│   ├── manifest.json              # domain hattrick, config_flow, cloud_polling, version 0.2.0
│   ├── const.py                   # endpoint CHPP, CONF_*, FILE_VERSIONS, intervalli, matchday
│   ├── api.py                     # HattrickCHPPClient (OAuth 1.0a) + HattrickApiError/AuthError
│   ├── models.py                  # Team, TeamMood, Economy, Player(s), LeagueDetails,
│   │                              #   Match(es), Training, TrainingSummary, Arena, Club,
│   │                              #   World + parser XML tollerante (HTT -> aware)
│   ├── coordinator.py             # HattrickDataUpdateCoordinator: file base + abilitati,
│   │                              #   matchday (5 min in finestra partita)
│   ├── config_flow.py             # auto OAuth / manuale / reauth / options (interval,
│   │                              #   file abilitati, matchday)
│   ├── entity.py                  # HattrickEntity + device_info squadra
│   ├── sensor.py                  # 21 sensor (vedi docs/04 §1–§8)
│   ├── __init__.py                # setup/unload entry, client+coordinator, PLATFORMS=[SENSOR]
│   ├── strings.json
│   └── translations/{en,it}.json
├── docs/                          # 01-10 documentazione + piano + handoff
└── tests/
    ├── conftest.py                # sys.path + auto_enable_custom_integrations
    ├── fixtures/                  # 12 XML: teamdetails, team, economy, error_auth,
    │                              #   players, leaguedetails, matches, training,
    │                              #   trainingsummary, arenadetails, club, worlddetails
    ├── test_api.py                # 8 test client CHPP
    ├── test_models.py             # 14 test parsing
    ├── test_coordinator.py        # 6 test coordinator (incl. matchday)
    ├── test_config_flow.py        # 8 test config flow + options
    └── test_sensor.py             # 9 test sensor/device
```

Commit recenti:

```
15cec8c T15: opzioni scan_interval/file abilitati/modalità matchday + coordinator matchday
c737a18 T14: sensor allenamento, stadio, mondo e allenatore
27ba3a6 T13: sensor classifica, partite ed economia
67c98ca T12: sensor rosa e club
e1d70ed T11: parsing esteso (8 file CHPP) + coordinator multi-file
38f17e4 T9+T10: traduzioni verificate e coverage M1 (tag v0.1.0)
67a1933 T8: sensor base + setup entry completo con device squadra
bfc6789 T7: config flow completo (auto OAuth, manuale, reauth, opzioni)
d9e7657 T6: DataUpdateCoordinator con gestione auth/api error
571cf9b..dea2a72 T1-T5: setup, CI, scheletro, client CHPP, modello dati
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
/tmp/ht-venv/bin/pytest -q                                        # 47 test
/tmp/ht-venv/bin/pytest -q --cov=custom_components/hattrick --cov-report=term-missing
```

Baseline attesa: **47 passed**, coverage ~93%.

## 4. Cosa è già implementato (mappa rápida)

- `api.py`: flusso OAuth 3-legged (`get_request_token_sync`, `get_authorize_url`,
  `get_access_token_sync`) + `get_file_sync`/`async_get_file` per i file XML CHPP;
  gestione 401/403 → `HattrickAuthError`, 429 → `HattrickApiError`, `<Error>` XML.
  Il modulo è indipendente da HA (eccezioni proprie).
- `models.py`: dataclass con `from_xml` tollerante per tutti i file del ciclo
  standard; `parse_htt_datetime` (formato HTT `yyyy-MM-dd HH:mm:ss`, vuota →
  `datetime.min`) e `htt_to_aware` (naive HTT → aware Europe/Stockholm).
  Enum CHPP come dizionari: `SPECIALTIES`, `TRAINING_TYPES`, `MATCH_TYPES`,
  `STAFF_TYPES` (etichette da riconfermare contro la wiki).
- `coordinator.py`: scarica in parallelo i file base (`teamdetails`, `team`,
  `economy`) + quelli abilitati in options e assembla `HattrickData`;
  `HattrickAuthError` → `ConfigEntryAuthFailed`, altro → `UpdateFailed`.
  Modalità matchday: se attiva e la prossima partita è entro ±3h (HTT),
  `update_interval` scende a 5 min (`MATCHDAY_INTERVAL`).
- `config_flow.py`: step `user` (scelta auto/manuale), `manual` (4 credenziali),
  `auth` (mostra URL authorize + campo verifier), `reauth`/`reauth_confirm`,
  options flow (`scan_interval` 5–60 min, `enabled_files`, `matchday`).
  Validazione via `teamdetails.xml`, `unique_id = UserID`, abort su doppioni.
- `sensor.py`: 21 sensor con `unique_id = {team_id}_{key}`, device "squadra"
  (`identifiers={(DOMAIN, str(team_id))}`); i diagnostici hanno
  `entity_category=DIAGNOSTIC`. I timestamp (`prossima_partita`, `server_time`)
  usano `device_class=TIMESTAMP` e datetime aware HTT.
- Nota HA 2025.1: `OptionsFlowWithConfigEntry` va istanziato con
  `HattrickOptionsFlow(config_entry)` in `async_get_options_flow`.
- Nota test: su Python 3.12 il venv risolve HA 2025.1.4 + PHACC 0.13.205
  (pin espliciti, vedi sezione 2); `requirements_test.txt` resta per py313.

## 5. Cosa resta da fare (prossimi passi, in ordine)

1. **T16 (M3)**: servizi `hattrick.get_match_details` e `hattrick.get_player`
   con `supports_response=SupportsResponse.ONLY` (HA 2024.11+): nuovo
   `services.py` + registrazione in `__init__.py`, `services.yaml`,
   fixture `matchdetails.xml`/`players.xml` (già c'è) + test con mock client.
2. **T17 (M3)**: la modalità matchday è già nel coordinator (T15); resta il
   test con ora HTT simulata dentro/fuori finestra (già coperto da
   `test_coordinator_matchday_*`) — eventualmente rifinire la finestra.
3. **T18 (M3)**: sensor diagnostici `dettaglio_ultima_partita` e
   `tattica_ultima_partita` da `matchdetails.xml`/`matchlineup.xml`
   (on-demand, non nel ciclo standard) + fixture + test.
4. **M4 (T19–T20)**: servizio `hattrick.set_match_orders` (POST `matchorders.xml`,
   richiede permesso scrittura sull'app CHPP), `hattrick.refresh`,
   `services.yaml` + `icons.json` + traduzioni servizi.
5. **M5–M8**: dashboard/esempi, test suite completa, release HACS v1.0.0,
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

Chiedere: *"procedi con T16"* (o l'ultimo task in sospeso). Ricostruire il venv
(sezione 2), lanciare `pytest -q` per confermare la baseline 47 passed, poi
lavorare al task e committare.
