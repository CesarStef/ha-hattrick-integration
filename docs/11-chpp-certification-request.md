# 11 — CHPP certification request (English text)

Testo pronto da incollare nella domanda di certificazione dell'app su
[chpp.hattrick.org](https://chpp.hattrick.org) (milestone M8 / task T26).
La descrizione dell'app è volutamente in inglese: è la lingua del team CHPP.

---

## App name

Hattrick for Home Assistant

## Short description (app listing)

A Home Assistant custom integration that brings your Hattrick team into your smart home:
live sensors for economy, squad, league standings, matches, training and arena, plus
optional match-day orders, all in Lovelace dashboards and automations.

## Full description (certification request)

**What it is.** "Hattrick for Home Assistant" is an open-source (Apache 2.0) custom
integration for Home Assistant, a popular open-source home automation platform. It connects
to the CHPP XML API (`chppxml.ashx`) with OAuth 1.0a three-legged authentication and exposes
the user's own team data as Home Assistant entities (sensors) and services.

**What it does (read-only, default).** After the user authorizes the app on Hattrick, the
integration polls the standard CHPP files on a configurable interval (default 15 minutes)
and shows them in Home Assistant:

- team info, morale and fan confidence (`teamdetails`, `team`)
- economy: cash, expected cash, wages, sponsors (`economy`)
- squad: player list with skills, form, TSI, injuries, suspensions (`players`)
- league standings and recent/upcoming matches (`leaguedetails`, `matches`)
- current training and weekly training summary (`training`, `trainingsummary`)
- arena capacity and sectors (`arenadetails`)
- club staff, fan club, youth squad (`club`)
- world/server time and next HT update dates (`worlddetails`)

Users can build dashboards and automations on top of these sensors, for example: a
notification 30 minutes before a match, an alert when cash drops below a threshold, or a
weekly training summary card.

**Optional write scope.** A separate service lets the user submit match orders
(`matchorders.xml`, POST) for the next match — formation, tactics, captain, set-piece
takers and substitutions — followed by an immediate refresh. This is only used when the
user explicitly calls the service, and only if the app is granted write permission.

**Matchday mode.** An optional "matchday" setting temporarily reduces the polling interval
to 5 minutes, but only inside a ±3 hour window around the team's next match (Hattrick Time),
to catch results almost in real time. Outside match windows the interval returns to the
user-configured value.

**Compliance with the CHPP rules.**

- Authentication is OAuth 1.0a three-legged: the user authorizes the app on hattrick.org and
  the integration stores only the resulting access token/secret, inside the Home Assistant
  config entry (encrypted at rest by Home Assistant). **No Hattrick login name, password or
  security code is ever requested, stored or logged.** Tokens and secrets are never written
  to logs or diagnostics.
- Only the official XML interface (`chppxml.ashx`) is used. No scraping of the website, no
  use of live or other non-CHPP endpoints.
- Download limits are respected: default polling is 15 minutes per file set, individual files
  can be disabled in the options, heavy files (`matchesarchive`, alliances, etc.) are never
  polled automatically and only on explicit user request, and on HTTP 429 the integration
  backs off instead of retrying aggressively.
- Data is used only for the authorizing user, only inside their own Home Assistant instance.
  Nothing is shared with third parties, sold, or used for profiling. The source code is
  public on GitHub for review.
- The integration is clearly labeled as unofficial and not affiliated with Hattrick.

**Why certify it.** Home Assistant has a large user base and many Hattrick managers use it.
Without certification only the app owner can authorize the app, so the integration cannot
reach other managers. Certification would let any Hattrick user connect their team safely,
with the guarantees above.

**Repository:** https://github.com/CesarStef/ha-hattrick-integration (Apache 2.0, tests
included).

---

## Note per l'uso (italiano)

1. Registrare l'app su chpp.hattrick.org con nome e short description sopra.
2. Incollare la "Full description" nel campo descrizione della domanda di certificazione.
3. Se viene chiesta una demo: puntare alla propria istanza HA (web) con i sensor già
   popolati, oppure a una registrazione dello schermo (i mock in `examples/mockups/`
   mostrano il layout previsto).
4. Se CHPP chiede il permesso di scrittura sugli ordini di partita (`matchorders`), è la
   milestone M4: va richiesto come scope separato e difeso con il paragrafo "Optional
   write scope".
5. Aggiornare questo documento con la risposta di Hattrick e gli eventuali adeguamenti
   richiesti (criterio di accettazione di T26).

---

## Stato della policy AI di Hattrick (aggiornato al 2026-11, da ricontrollare prima dell'invio)

**Rilevante per questo progetto, che è vibe-codato.**

- A maggio 2026 un admin CHPP ha chiarito pubblicamente (caso `rmagasi/hattrick-team-assistant`,
  app rifiutata il 2026-05-17) che **l'uso di AI nelle applicazioni CHPP non è attualmente
  consentito** — il progetto è stato "parked" con la nota che non c'è percorso di
  approvazione sotto la policy corrente.
- La formulazione riguarda le app che "fanno lavoro AI per gli utenti" (LLM al runtime).
  **Non è chiaro se includa anche il codice generato da AI senza feature AI a runtime** —
  la nostra integrazione non usa alcun modello AI a runtime, ma il codice è stato generato
  con un agente AI (dichiarato nel README).
- **Prima di inviare la domanda, chiedere esplicitamente agli admin CHPP** (forum CHPP o
  campo note della domanda) se il codice generato da AI, senza feature AI a runtime, è
  ammissibile. Se la risposta è no, la certificazione è bloccata finché Hattrick non
  aggiorna la policy: documentare la risposta in questo file.

## Checklist pre-invio (requisiti CHPP Manual, verificati nel repo)

- [x] Solo file XML ufficiali (`chppxml.ashx`), niente scraping — `api.py` usa solo CHPP_XML_URL.
- [x] User-Agent con nome programma e versione in ogni richiesta — `USER_AGENT` in
  `const.py` (da manifest), impostato su tutte le sessioni OAuth in `api.py`.
- [x] OAuth 1.0a 3-legged; mai password/codice di sicurezza; token mai nei log;
  diagnostics redatta (`diagnostics.py`, test automatico in `tests/test_diagnostics.py`).
- [x] Solo dati della propria squadra; niente tracciamento di altre squadre.
- [x] Limiti di download: polling default 15 min, backoff su 429, file pesanti solo
  on-demand, matchday 5 min solo dentro ±3h dalla partita.
- [x] Copyright notice "This application uses information from the online game service
  Hattrick.org" nel README (richiesto dal CHPP Manual).
- [x] App gratuita: nessun pagamento richiesto agli utenti.
- [x] Privacy policy pubblica: `docs/13-privacy-policy.md` (renderizzata da GitHub).
- [x] Codice sorgente pubblico su GitHub con test (90 test, coverage 97%).
- [ ] Demo: istanza HA reale con dati CHPP o registrazione (da preparare al momento dell'invio).
- [ ] Risposta esplicita sulla policy AI (vedi sezione sopra) — **bloccante**.
- [ ] La domanda va inviata **prima** di pubblicizzare l'app: "Apply for CHPP before you
  start developing" (wiki CHPP). L'app resta "personal" finché non certificata, quindi
  solo il proprietario può autorizzarla.
