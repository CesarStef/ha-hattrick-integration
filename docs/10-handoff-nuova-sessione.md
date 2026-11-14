# 10 — Handoff: stato attuale e come riprendere in una nuova sessione

Documento di passaggio: fotografa lo stato del repo al **2026-11-14** e dice
esattamente da dove ripartire. Aggiornarlo a ogni milestone.

## 1. Stato del repository

- Branch `main`, remote `origin` = `https://github.com/CesarStef/ha-hattrick-integration.git`
- Ultimo commit su main: `d22159f`. Tag `v1.0.0` pushato (tutti i tag v0.1.0–v1.0.0 su origin).
- **M7 rilasciata (v1.0.0)** e **M8 in preparazione**: 4 servizi, 23 sensor, esempi +
  mock HTML, diagnostics redatta, repair token revocato, 90 test verdi, coverage 97%.
- Attenzione: i **tag** sono su origin ma le **GitHub Release** no (il connettore
  disponibile non le crea): crearle dall'UI GitHub dai tag, altrimenti
  Marketplace/HACS installano il branch main invece della release.

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
│   ├── manifest.json              # domain hattrick, config_flow, cloud_polling, version 1.0.0
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
│   ├── services.py                # 4 servizi: get_match_details/get_player/set_match_orders
│   │                              #   (supports_response ONLY) + refresh
│   ├── services.yaml              # schema di tutti i servizi con selettori
│   ├── icons.json                 # icone dei 4 servizi
│   ├── diagnostics.py             # dump diagnostico con credenziali redatte (***)
│   ├── repairs.py                 # fix flow: token revocato -> reauth
│   ├── __init__.py                # setup/unload entry + registrazione/rimozione servizi
│   ├── strings.json
│   └── translations/{en,it}.json
├── docs/                          # 01-11 documentazione + piano + handoff + richiesta CHPP
├── examples/                      # dashboard.yaml + automations.yaml + mockups/index.html (M5)
├── docs/12-release-notes-v1.0.0.md  # note release v1.0.0 (da incollare nella GitHub Release)
├── docs/13-privacy-policy.md      # privacy policy per la certificazione CHPP
└── tests/
    ├── conftest.py                # sys.path + auto_enable_custom_integrations
    ├── fixtures/                  # 14 XML (aggiunti matchdetails.xml, matchlineup.xml)
    ├── test_api.py                # 8 test client CHPP
    ├── test_models.py             # 17 test parsing (incl. MatchDetails/MatchLineup)
    ├── test_coordinator.py        # 6 test coordinator (incl. matchday)
    ├── test_config_flow.py        # 8 test config flow + options
    ├── test_sensor.py             # 11 test sensor/device (incl. diagnostici partita)
    ├── test_services.py           # 10 test servizi (on-demand, set_match_orders, refresh)
    ├── test_examples.py           # 4 test struttura esempi examples/
    ├── test_diagnostics.py        # 3 test diagnostics redatta + repair token revocato
    └── test_api.py                # 12 test client CHPP (incl. POST matchorders)
```

Commit recenti:

```
53e0433 T24: diagnostics.py redatta + repair fixable token revocato
941480d T23: test suite completa (86 test, coverage 97%)
78ef989 Mock HTML dashboard (3 varianti) in examples/mockups/
bdb7561 T22: README utente completo (installazione, config, FAQ, servizi)
e399964 T21: esempi dashboard Lovelace e automazioni in examples/ + test
bd6478a T20: servizio refresh + icons.json + servizi in services.yaml/traduzioni
0cddaad T19: set_match_orders (POST matchorders.xml) + refresh post-invio + test
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
/tmp/ht-venv/bin/pytest -q                                        # 89 test
/tmp/ht-venv/bin/pytest -q --cov=custom_components/hattrick --cov-report=term-missing
```

Baseline attesa: **89 passed**, coverage ~97%.

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
- `services.py`: 4 servizi registrati una sola volta in
  `hass.data[DOMAIN]["services_registered"]` e rimossi quando non restano entry:
  `get_match_details`/`get_player`/`set_match_orders` con
  `supports_response=SupportsResponse.ONLY`, e `refresh` (senza risposta).
  `set_match_orders` costruisce il corpo XML di `matchorders.xml`
  (`_build_match_orders_xml`), lo posta con `async_post_file` e poi chiama
  `coordinator.async_request_refresh()`; i nomi campo XML sono quelli della
  wiki CHPP, **da riconfermare** contro dati reali.
- `api.py`: `post_file_sync`/`async_post_file` per POST XML su `chppxml.ashx`;
  `_parse_response` condiviso GET/POST (401/403 → AuthError, 429/altro →
  ApiError, `<Error>` XML).
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

1. **Creare le GitHub Release dai tag** (UI GitHub → Releases → "Draft a new release"):
   senza l'oggetto Release, Marketplace/HACS installano main invece della versione
   fissata. Note pronte in `docs/12-release-notes-v1.0.0.md` per v1.0.0.
2. **T26 (M8)**: inviare la domanda di certificazione CHPP con il testo di `docs/11`
   (privacy policy in `docs/13`). **Bloccante**: chiedere prima agli admin CHPP se il
   codice generato da AI (senza feature AI a runtime) è ammissibile — a maggio 2026
   Hattrick ha rifiutato un'app con uso AI. Poi aggiornare `docs/11` con la risposta.
3. Collaudo reale su HA 2026.11.1 con account CHPP: riconfermare `FILE_VERSIONS` e i
   nomi campi XML di `matchorders.xml` contro le risposte reali.

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

Chiedere: *"procedi con T26"* (o l'ultimo task in sospeso). Ricostruire il venv
(sezione 2), lanciare `pytest -q` per confermare la baseline 90 passed, poi
lavorare al task e committare. Push solo a fine milestone (tag SemVer).
