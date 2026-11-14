# 04 — Catalogo di entità (sensor) e azioni (services)

Questo documento elenca tutte le entità e i servizi che l'integrazione esporrà, con il
file CHPP che le alimenta. È la specifica da cui nascerà `sensor.py` e `services.py`.

Convenzioni:

- Ogni entità ha `unique_id = "{team_id}_{chiave}"` e fa parte del device "squadra".
- Le entità puramente diagnostiche sono `entity_category="diagnostic"` e disabilitate di
  default.
- Gli attributi (`extra_state_attributes`) contengono i dettagli, lo stato è il valore
  principale (spesso il più utile in dashboard/automazioni).

## 1. Sensor "squadra" (da `teamdetails.xml`, `team.xml`, `club.xml`)

| Entità (chiave) | Stato | Attributi principali | Fonte CHPP |
|-----------------|-------|----------------------|------------|
| `team_name` | nome squadra | team_id, lega, regione, arena_id, stile gioco, colore maglia | teamdetails |
| `morale` | TeamSpirit (excellent…disastrous) | — | team |
| `fiducia_tifosi` | Confidence | — | team |
| `fanclub` | numero membri fan club | — | club |
| `settore_giovanile` | livello youth squad | — | club |
| `allenatore` | nome + livello coach | — | teamdetails |
| `staff` (diagnostic) | — | preparatore atletico, medico, psicologo, portavoce e loro livelli | club |

## 2. Sensor "economia" (da `economy.xml`)

| Entità | Stato | Unità | Attributi |
|--------|-------|-------|-----------|
| `cassa` | cash disponibile | valuta lega (device_class monetary) | expected_cash, sponsor, costi staff, interessi |
| `entrate_previste` | expected cash | valuta | dettaglio fonti |
| `stipendi` (diagnostic) | wage totale rosa | valuta | — |

## 3. Sensor "classifica" (da `leaguedetails.xml`)

| Entità | Stato | Attributi |
|--------|-------|-----------|
| `posizione` | numero posizione in classifica | punti, gol fatti/subiti, differenza reti, serie (V/P), partite giocate, nome lega, league_id, season |
| `prossima_partita` | data/ora HT della prossima partita | match_id, avversario, casa/trasferta, tipo partita (lega/coppa/amicizia), luogo |
| `ultima_partita` | risultato (es. "3-1") | match_id, avversario, casa/trasferta, data, link matchdetails |

## 4. Sensor "rosa" (da `players.xml`)

| Entità | Stato | Attributi |
|--------|-------|-----------|
| `giocatori` | numero giocatori in rosa | lista compatta per giocatore: id, nome, ruolo, età, forma, TSI, stipendio, infortunio, squalifica, specialità |
| `tsi_totale` | somma TSI rosa | media TSI, età media |
| `infortunati` | numero infortunati | lista id/nome/giorni |
| `squalificati` | numero squalificati | lista id/nome/partite di squalifica |
| `forma_squadra` (diagnostic) | — | forma media,skill media per reparto (POR/DIF/CC/ATT) |

> Nota: la lista completa dei giocatori come attributo del sensor `giocatori` è
> voluminosa (25+ giocatori). Va bene per dashboard e automazioni; in alternativa si
> può esporre un servizio `hattrick.get_player` con risposta per il singolo giocatore.

## 5. Sensor "partite" (da `matches.xml`, `matchdetails.xml`, `matchlineup.xml`)

| Entità | Stato | Attributi |
|--------|-------|-----------|
| `partite_programmate` | numero partite future | lista prossime 5: data, avversario, casa/trasferta, match_id |
| `dettaglio_ultima_partita` (diagnostic) | rating totale | possesso, tiri, gol, rating per reparto (POR/DIF/CC/ATT), meteo, arbitro |
| `tattica_ultima_partita` (diagnostic) | tattica usata | aggressività, pressing, formazione, capitano |

I dettagli di una partita specifica si possono ottenere on-demand con il servizio
`hattrick.get_match_details` (con risposta), evitando di tenere in memoria tutte le
partite.

## 6. Sensor "allenamento" (da `training.xml`, `trainingsummary.xml`)

| Entità | Stato | Attributi |
|--------|-------|-----------|
| `allenamento` | skill allenata (es. "Scoring") + intensità % | tipo allenamento, livello coach, morale/fiducia impattati |
| `progresso_allenamento` (diagnostic) | — | riepilogo settimanale, skill allenate, % reparto |

## 7. Sensor "stadio" (da `arenadetails.xml`)

| Entità | Stato | Attributi |
|--------|-------|-----------|
| `stadio` | capacità totale | settori (basic/covered/grandstand), naming rights, livello costruzione |

## 8. Sensor "mondo/HT" (da `world.xml`)

| Entità | Stato | Attributi |
|--------|-------|-----------|
| `server_time` | data/ora HT corrente | prossima training update, prossima economy update, stagione corrente |

## 9. Servizi (azioni) del dominio `hattrick`

| Servizio | Descrizione | Dati richiesti | Effetto |
|----------|-------------|----------------|---------|
| `hattrick.refresh` | forza un aggiornamento immediato dei dati CHPP | (opzionale) `config_entry` | chiama il coordinator fuori ciclo |
| `hattrick.set_match_orders` | invia gli ordini di partita a Hattrick (`matchorders.xml`) | `match_id`, tattica, aggressività, pressing, atteggiamento, formazione (11+7), capitano, rigoristi, sostituzioni | POST a CHPP, poi refresh; restituisce esito |
| `hattrick.get_match_details` | restituisce i dettagli di una partita (con risposta) | `match_id` | risposta JSON con gol, rating, eventi |
| `hattrick.get_player` | restituisce i dati di un giocatore (con risposta) | `player_id` | risposta JSON con skill, forma, TSI, ecc. |

Note sui servizi:

- `set_match_orders` richiede che l'app CHPP dell'utente abbia il permesso di scrittura
  sugli ordini partita; in config flow lo chiederemo come scope opzionale.
- I servizi con risposta (`get_match_details`, `get_player`) usano `supports_response`
  (HA 2024.11+) così da poter essere usati in automazioni con `response_variable`.
- Tutti i campi dei servizi sono descritti in `services.yaml` con selettori
  (`select`, `number`, `object`, `entity`) e tradotti in `strings.json`.

## 10. Esempi di automazioni abilitate

```yaml
# Notifica 30 minuti prima della partita
trigger:
  - platform: time_pattern
    minutes: "/5"
condition:
  - condition: template
    value_template: >
      {{ now() >= (states('sensor.prossima_partita') | as_datetime) - timedelta(minutes=30)
         and now() < (states('sensor.prossima_partita') | as_datetime) - timedelta(minutes=25) }}
action:
  - action: notify.mobile_app
    data:
      message: "Tra 30 minuti gioca {{ state_attr('sensor.prossima_partita','avversario') }}!"
```

```yaml
# Allarme cassa bassa
trigger:
  - platform: numeric_state
    entity_id: sensor.cassa
    below: 1000000
action:
  - action: notify.mobile_app
    data:
      message: "Cassa sotto 1M: {{ states('sensor.cassa') }}"
```

```yaml
# Invio ordini partita automatico (esempio con dati in input_text/input_select)
action:
  - action: hattrick.set_match_orders
    data:
      match_id: "{{ state_attr('sensor.prossima_partita', 'match_id') }}"
      tactic: "{{ states('input_select.tattica') }}"
      # ... formazione, capitano, ecc.
```
