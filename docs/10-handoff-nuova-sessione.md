# 10 — Handoff: stato attuale e come riprendere in una nuova sessione

Documento di passaggio: fotografa lo stato del repo al **2026-11-14** e dice
esattamente da dove ripartire. Aggiornarlo a ogni milestone.

## 1. Stato del repository

- Branch `main`, remote `origin` = `https://github.com/CesarStef/ha-hattrick-integration.git`
- Ultimo commit su main: `6c228e5` (pushato). Tag `v0.3.0` pushato.
- **Milestone M3 completata**: servizi on-demand `get_match_details`/`get_player`
  con risposta, sensor diagnostici ultima partita (matchdetails/matchlineup),
  23 sensor totali, 59 test verdi, coverage 94%.

```
ha-hattrick-integration/
├── README.md                      # include disclaimer "progetto vibe-codato"
├── LICENSE                        # Apache License 2.0
├── hacs.json
├── pyproject.toml                 # ruff (py313, line-length 100) + pytest, license Apache-2.0
├── requirements_test.txt          # ruff, pytest, pytest-asyncio, pytest-cov,
│                                  #   pytest-homeassistant-custom-component, requests-oauthlib
├── .github/workflows/             # hassfest.yaml, hacs.yaml
├── custom_components/hattrick/
│   ├── manifest.json              # domain hattrick, config_flow, cloud_polling, version 0.3.0
│   ├── const.py                   # endpoint CHPP, CONF_*, FILE_VERSIONS, ON_DEMAND_FILES,
│   │                              #   SELECTABLE_FILES, intervalli, matchday
│   ├── api.py                     # HattrickCHPPClient (OAuth 1.0a) + HattrickApiError/AuthError
│   │                              #   (wrap anche di TokenRequestDenied/ValueError)
│   ├── models.py                  # Team, TeamMood, Economy, Player(s), LeagueDetails,
│   │                              #   Match(es), Training, TrainingSummary, Arena, Club,
│   │                              #   World, MatchDetails, MatchLineup + parser XML tollerante
│   ├── coordinator.py             # file base + abilitati in parallelo, on-demand
│   │                              #   (matchdetails/matchlineup ultima partita se abilitati),
│   │                              #   matchday (5 min in finestra partita ±3h HTT)
│   ├── config_flow.py             # step app (consumer key/secret) + auto OAuth / manuale /
│   │                              #   reauth / options (interval, file abilitati incl. on-demand,
│   │                              #   matchday)
│   ├── entity.py                  # HattrickEntity + device_info squadra
│   ├── sensor.py                  # 23 sensor (vedi docs/04 §1–§8 + diagnostici M3)
│   ├── services.py                # servizi get_match_details / get_player (supports_response ONLY)
│   ├── services.yaml              # schema servizi (match_id/player_id/config_entry)
│   ├── __init__.py                # setup/unload entry + registrazione/rimozione servizi
│   ├── strings.json
│   └── translations/{en,it}.json
├── docs/                          # 01-11 documentazione + piano + handoff + richiesta CHPP
└── tests/
    ├── conftest.py                # sys.path + auto_enable_custom_integrations
    ├── fixtures/                  # 14 XML (aggiunti matchdetails.xml, matchlineup.xml)
    ├── test_api.py                # 8 test client CHPP
    ├── test_models.py             # 17 test parsing (incl. MatchDetails/MatchLineup)
    ├── test_coordinator.py        # 6 test coordinator (incl. matchday)
    ├── test_config_flow.py        # 8 test config flow + options
    ├── test_sensor.py             # 11 test sensor/device (incl. diagnostici partita)
    └── test_services.py           # 4 test servizi on-demand
```

Commit recenti:

```
6c228e5 T18: sensor diagnostici dettaglio/tattica ultima partita (matchdetails/matchlineup)
783da55 T16: servizi get_match_details/get_player con supports_response + services.yaml
e0db589 Fix config flow: step app consumer key/secret + wrap TokenRequestDenied in HattrickAuthError
a1b80dc docs/11: testo inglese per richiesta certificazione CHPP (M8/T26)
e4f7b4c Disclaimer README "progetto vibe-codato"
fcf4dfc Compatibilita HA 2026.11: OptionsFlow semplice (no OptionsFlowWithConfigEntry)
37834f0 Licenza Apache 2.0
15cec8c T15: opzioni scan_interval/file abilitati/modalità matchday + coordinator matchday
c737a18 T14: sensor allenamento, stadio, mondo e allenatore
27ba3a6 T13: sensor classifica, partite ed economia
67c98ca T12: sensor rosa e club
e1d70ed T11: parsing esteso (8 file CHPP) + coordinator multi-file
```

## 2. Ambiente di test (da ricreare: `/tmp` viene pulito tra sessioni)

```bash
cd /Users/stefanocattonar/Repositories/ha-hattrick-integration
python3 -m venv /tmp/ht-venv
/tmp/ht-venv/bin/pip install homeassistant==2025.1.4 \
    pytest-homeassistant-custom-component==0.13.205 requests-oauthlib \
    pytest-cov pyyaml ruff pytest pytest-asyncio voluptuous
```

Su Python 3.12 usare i **pin espliciti** sopra (NON `requirements_test.txt`,
che punta a PHACC>=0.13.230 in conflitto): pip risolve **HA 2025.1.4** +
**PHACC 0.13.205** (ultime compatibili con 3.12). In produzione l'integrazione
gira su HA 2025.1+ (vedi `hacs.json`); il target di pyproject è py313 (HA 2026).

## 3. Comandi rapidi

```bash
/tmp/ht-venv/bin/ruff check . && /tmp/ht-venv/bin/ruff format .
/tmp/ht-venv/bin/pytest -q                                        # 59 test
/tmp/ht-venv/bin/pytest -q --cov=custom_components/hattrick --cov-report=term-missing
```

Baseline attesa: **59 passed**, coverage ~94%.

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
  poi, se `matchdetails`/`matchlineup` sono abilitati, scarica on-demand i
  dettagli dell'ultima partita (`matchID=last.match_id`).
  `HattrickAuthError` → `ConfigEntryAuthFailed`, altro → `UpdateFailed`.
  Modalità matchday: se attiva e la prossima partita è entro ±3h (HTT),
  `update_interval` scende a 5 min (`MATCHDAY_INTERVAL`).
- `config_flow.py`: step `app` (consumer key/secret CHPP), `user` (scelta
  auto/manuale), `manual` (4 credenziali), `auth` (URL authorize + verifier),
  `reauth`/`reauth_confirm`, options flow (`scan_interval` 5–60 min,
  `enabled_files` incl. on-demand, `matchday`). Validazione via
  `teamdetails.xml`, `unique_id = UserID`, abort su doppioni.
- `sensor.py`: 23 sensor con `unique_id = {team_id}_{key}`, device "squadra"
  (`identifiers={(DOMAIN, str(team_id))}`); i diagnostici hanno
  `entity_category=DIAGNOSTIC`. I timestamp (`prossima_partita`, `server_time`)
  usano `device_class=TIMESTAMP` e datetime aware HTT.
- `services.py`: `hattrick.get_match_details` e `hattrick.get_player` con
  `supports_response=SupportsResponse.ONLY`, registrados una sola volta in
  `hass.data[DOMAIN]["services_registered"]` e rimossi quando non restano entry.
- Compatibilità HA: l'options flow usa `OptionsFlow` semplice con `config_entry`
  auto-assegnato da HA (2024.11+): funziona su 2025.1 e su 2026.11 (dove
  `OptionsFlowWithConfigEntry` è in phase-out e il setter rimosso dal 2025.12).
  Il coordinator passa `config_entry=` esplicito al `DataUpdateCoordinator`
  (raccomandato, ok sia su 2025.1 sia su 2026.x).
  Attenzione futura: da HA **2026.12** la combinazione `add_update_listener` +
  `async_update_reload_and_abort` (usata in reauth) solleverà un'eccezione:
  a quel punto migrare a `OptionsFlowWithReload`.
- Su HA 2026.11 il Marketplace è integrato (HACS si ferma a 2026.11): per testare
  il repo basta aggiungerlo come "Custom repository" nel Marketplace.
- Nota test: su Python 3.12 il venv risolve HA 2025.1.4 + PHACC 0.13.205
  (pin espliciti, vedi sezione 2); `requirements_test.txt` resta per py313.

## 5. Cosa resta da fare (prossimi passi, in ordine)

1. **T19 (M4)**: servizio `hattrick.set_match_orders` (POST `matchorders.xml`,
   richiede permesso scrittura sull'app CHPP): schema voluptuous + selettori in
   `services.yaml`, client `async_post_file` in `api.py`, refresh post-invio,
   risposta con esito; test con mock POST (payload XML corretto).
2. **T20 (M4)**: servizio `hattrick.refresh` + icone servizi (`icons.json`) +
   traduzioni servizi in strings/it/en; verifica hassfest su `services.yaml`.
3. **M5 (T21–T22)**: dashboard Lovelace di esempio + automazioni + README utente.
4. **M6–M8**: test suite completa (coverage > 80%), diagnostics redatta,
   release v1.0.0, certificazione CHPP (testo pronto in `docs/11`, ma
   **ricontrollare la policy CHPP sull'AI**: a maggio 2026 Hattrick ha rifiutato
   un'app generata da AI) — vedi `docs/09-piano-di-lavoro.md`.

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

Chiedere: *"procedi con T19"* (o l'ultimo task in sospeso). Ricostruire il venv
(sezione 2), lanciare `pytest -q` per confermare la baseline 59 passed, poi
lavorare al task e committare.
