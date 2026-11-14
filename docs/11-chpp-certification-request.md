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
   popolati, oppure a una registrazione dello schermo.
4. Se CHPP chiede il permesso di scrittura sugli ordini di partita (`matchorders`), è la
   milestone M4: va richiesto come scope separato e difeso con il paragrafo "Optional
   write scope".
5. Aggiornare questo documento con la risposta di Hattrick e gli eventuali adeguamenti
   richiesti (criterio di accettazione di T26).
