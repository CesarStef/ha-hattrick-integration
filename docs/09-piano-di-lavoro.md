# 09 — Piano di lavoro

Piano operativo per lo sviluppo dell'integrazione, derivato dalla roadmap in
`docs/08`. Stato attuale: **documentazione di progettazione completata** (commit
`e1424d2`). Da qui in poi si passa al codice.

## Stato di avanzamento (aggiornato al 2026-11-14)

**M5 completata e rilasciata**: tag `v0.5.0`, pushato su `origin/main`.
Test: 73 passed. Coverage totale 94% (models 98%, sensor 98%, coordinator 91%,
entity 100%, config_flow 86%, `__init__` 97%, api 88%, services 93%).

| Task | Stato | Commit |
|------|-------|--------|
| T1 | fatto | `571cf9b` |
| T2 | fatto | `fdb0b1c` |
| T3 | fatto | `a7c3a6e` |
| T4 | fatto | `f35263d` |
| T5 | fatto | `f693913` + `dea2a72` (fix parsing tollerante) |
| T6 | fatto | `d9e7657` |
| T7 | fatto | `bfc6789` |
| T8 | fatto | `67a1933` |
| T9 | fatto | `38f17e4` (grep: nessun testo UI hardcoded) |
| T10 | fatto | `38f17e4` (coverage, tag `v0.1.0`) |
| T11 | fatto | `e1d70ed` (parsing esteso 8 file + coordinator multi-file) |
| T12 | fatto | `67c98ca` (sensor rosa + club) |
| T13 | fatto | `27ba3a6` (sensor classifica/partite/economia) |
| T14 | fatto | `c737a18` (sensor allenamento/stadio/mondo/allenatore) |
| T15 | fatto | `15cec8c` (opzioni + modalità matchday) |
| T16 | fatto | `783da55` (servizi get_match_details/get_player + services.yaml) |
| T17 | fatto | `15cec8c` (matchday già in T15: polling 5 min in finestra HTT) |
| T18 | fatto | `6c228e5` (sensor diagnostici dettaglio/tattica ultima partita) |
| T19 | fatto | `0cddaad` (set_match_orders: POST matchorders.xml + refresh post-invio) |
| T20 | fatto | `bd6478a` (servizio refresh + icons.json + servizi in services.yaml) |
| T21 | fatto | `e399964` (examples/dashboard.yaml + automations.yaml + test) |
| T22 | fatto | `bdb7561` (README utente: installazione, config, FAQ) |

**Prossimo task: T23 (inizio M6).** Per riprendere il lavoro in una nuova
sessione vedi `docs/10-handoff-nuova-sessione.md`.

## Convenzioni di lavoro

- **Un commit per ogni task completato** su `main`, con messaggio che indica il task
  (es. `T3: client CHPP OAuth in api.py`). Niente push senza richiesta esplicita.
- Ogni task ha un **criterio di accettazione** verificabile (test, comando, controllo
  manuale). Un task è "fatto" solo quando il criterio è soddisfatto e committato.
- Ordine: si segue la colonna "Dipende da"; i task senza dipendenze possono partire in
  parallelo.
- Stime indicative in ore/uomo (h), da ricalibrare dopo M1.

## Milestone M1 — Fondamenta (v0.1.0 funzionante end-to-end)

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T1 | Setup repo di sviluppo: `.gitignore`, `pyproject.toml` (ruff), `requirements_test.txt`, cartella `tests/` | file di config committati | `ruff check` pulito; `pytest` gira (anche se vuoto) | 2h | — |
| T2 | CI GitHub Actions: hassfest + HACS validation in `.github/workflows/` | workflow che passano su PR | badge/CI verdi su una PR di test | 2h | T1 |
| T3 | Scheletro integrazione: `custom_components/hattrick/` con `manifest.json`, `hacs.json`, `const.py`, `__init__.py` vuoto | HA riconosce l'integrazione (appare in "Aggiungi integrazione") | hassfest action verde; HA carica il dominio senza errori | 3h | T1 |
| T4 | Client CHPP in `api.py`: `OAuth1Session`, `get_file()`, gestione errori (`HattrickAuthError`, `HattrickApiError`), wrapper async in executor | client testabile con mock | test con fixture XML: parsing OK, errore auth → `HattrickAuthError` | 6h | T3 |
| T5 | `models.py`: dataclass + parser XML per teamdetails, team, economy | dataclass popolate da fixture | test parsing su `tests/fixtures/*.xml` | 4h | T4 |
| T6 | `coordinator.py`: `HattrickDataUpdateCoordinator`, refresh dei 3 file base, gestione `ConfigEntryAuthFailed`/`UpdateFailed` | coordinator funzionante | test: update OK; auth error → reauth; api error → UpdateFailed | 4h | T4, T5 |
| T7 | `config_flow.py`: modalità manuale (4 credenziali) + automatica (request token → authorize URL → verifier → access token), validazione con teamdetails, `unique_id=UserID`, reauth | config flow completo | test config flow con mock: happy path, verifier errato, reauth; entry creata con title=TeamName | 8h | T4, T6 |
| T8 | `sensor.py` base + `entity.py`: device_info squadra, sensor `team_name`, `morale`, `fiducia_tifosi`, `cassa` | 4 sensor visibili in HA | test sensor: stati corretti da fixture; device raggruppa le entità | 4h | T6 |
| T9 | Traduzioni: `strings.json`, `translations/en.json`, `translations/it.json`, `icons.json` | UI in it/en | nessun testo hardcoded nel codice (grep) | 2h | T7, T8 |
| T10 | Test suite M1 + primo giro manuale in HA Docker con account CHPP di test | `pytest` verde; demo manuale | coverage coordinator+config_flow > 70%; video/screenshot dashboard base | 4h | T7–T9 |

**M1 done quando**: T1–T10 committati, CI verde, HA di test mostra i 4 sensor con dati
reali CHPP, tag `v0.1.0`.

## Milestone M2 — Squadra completa (v0.2.0)

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T11 | Parsing esteso in `models.py`/`api.py`: players, leaguedetails, matches, training, trainingsummary, arenadetails, club, world | fixture per ogni file | test parsing di tutti i file | 6h | T5 |
| T12 | Sensor rosa: `giocatori` (attributi lista), `tsi_totale`, `infortunati`, `squalificati`, `forma_squadra` | 5 sensor | test stati/attributi; attributi leggibili in UI | 5h | T11 |
| T13 | Sensor classifica e partite: `posizione`, `prossima_partita`, `ultima_partita`, `partite_programmate` | 4 sensor | test con fixture matches/leaguedetails | 4h | T11 |
| T14 | Sensor allenamento e stadio: `allenamento`, `progresso_allenamento`, `stadio`, `server_time` | 4 sensor | test con fixture training/arenadetails/world | 3h | T11 |
| T15 | Options flow: scan_interval (5–60 min), file abilitabili, modalità matchday | opzioni funzionanti | test options flow; coordinator usa l'intervallo scelto | 3h | T6, T7 |

**M2 done quando**: tutti i sensor di `docs/04` §1–§8 presenti e testati, tag `v0.2.0`.

## Milestone M3 — Dettaglio partite on-demand (v0.3.0)

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T16 | Servizi `hattrick.get_match_details` e `hattrick.get_player` con `supports_response` | 2 servizi con risposta | test servizi: risposta JSON corretta da fixture matchdetails/players | 5h | T11, T3 |
| T17 | Modalità matchday nel coordinator (polling 5 min nelle finestre partita HTT) | opzione funzionante | test con ora HTT simulata dentro/fuori finestra | 3h | T15 |
| T18 | Sensor diagnostici: `dettaglio_ultima_partita`, `tattica_ultima_partita` (matchlineup) | 2 sensor diagnostic | test con fixture matchdetails/matchlineup | 3h | T16 |

## Milestone M4 — Azioni (v0.4.0)

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T19 | Servizio `hattrick.set_match_orders`: schema voluptuous + selettori, POST `matchorders.xml`, refresh post-invio, risposta con esito | servizio funzionante | test con mock POST: payload XML corretto, esito restituito; docs/04 §9 rispettata | 8h | T3, T7 (permesso scrittura) |
| T20 | Servizio `hattrick.refresh` + `services.yaml` + icone + traduzioni servizi | 3 servizi in UI | hassfest valida services.yaml; servizi visibili in Strumenti sviluppatori → Azioni | 3h | T16, T19 |

## Milestone M5 — UX e dashboard (v0.5.0)

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T21 | Dashboard Lovelace di esempio (`examples/dashboard.yaml`) + automazioni di esempio (`examples/automations.yaml`) | file di esempio | importati in HA di test senza errori; screenshot in README | 4h | M2 |
| T22 | README utente: installazione HACS, configurazione, FAQ | README completo | link check; istruzioni seguibili da un utente nuovo | 3h | M2 |

## Milestone M6 — Qualità (v0.6.0)

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T23 | Test suite completa: config flow, coordinator, sensor, servizi, options, reauth | `pytest` completo | coverage > 80% su `custom_components/hattrick` | 8h | M2–M4 |
| T24 | Diagnostics redatta (senza token) + repair per token revocato | `diagnostics.py` | dump di test non contiene credenziali (test automatico) | 2h | T7 |

## Milestone M7 — Release pubblica HACS

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T25 | Release `v1.0.0`: tag, release notes, verifica HACS action | release su GitHub | HACS installa la release in HA di test pulita | 2h | M6 |

## Milestone M8 — Certificazione CHPP

| ID | Task | Deliverable | Criterio di accettazione | Stima | Dipende da |
|----|------|-------------|--------------------------|-------|------------|
| T26 | Preparazione richiesta certificazione a Hattrick (docs, privacy policy, demo) | domanda inviata | risposta di Hattrick; adegamenti documentati | 4h | M7 |

## Grafo delle dipendenze (sintesi)

```
T1 → T2, T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 ─┐
                          T4 → T11 → T12/T13/T14 → T15 ─┤
                          T11 → T16 → T17, T18 ──────────┼→ T23 → T25 → T26
                          T3+T7 → T19 → T20 ──────────────┤
                          M2 → T21, T22 ──────────────────┘
```

## Prossimi passi immediati

1. T1 (setup repo) — poi commit.
2. T3 (scheletro integrazione) — poi commit.
3. T4 (client CHPP) — poi commit.

Ogni task completato viene committato singolarmente su `main`.
