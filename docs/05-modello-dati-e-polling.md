# 05 — Modello dati, coordinator e strategia di polling

Come i dati CHPP vengono trasformati in oggetti Python, chi li tiene in memoria e con
quale frequenza vengono aggiornati.

## 1. Modello dati (`models.py`)

Dataclass pure con parser `from_xml`. Schema semplificato:

```python
@dataclass
class Player:
    player_id: int
    name: str
    role: str            # portiere/difensore/centrocampista/attaccante
    age: int
    form: int            # forma (1-8+)
    tsi: int
    wage: int
    injury_weeks: int
    cards: int           # squalifica in partite
    specialty: str
    experience: int
    # ... altre skill (keeper, defending, passing, ...)

@dataclass
class Match:
    match_id: int
    date: datetime       # in HTT
    home_team: str
    away_team: str
    home_goals: int | None
    away_goals: int | None
    is_finished: bool
    match_type: str      # league/cup/friendly/...

@dataclass
class Team:        # da teamdetails
    team_id: int
    team_name: str
    league_id: int
    league_name: str
    arena_id: int
    region: str
    coach_level: int
    # ...

@dataclass
class Economy:
    cash: int
    expected_cash: int
    sponsors: int
    wages: int
    # ...

@dataclass
class Training:
    training_type: str
    intensity: int
    stamina_share: int
    coach_level: int

@dataclass
class LeagueStanding:
    position: int
    points: int
    goals_for: int
    goals_against: int
    matches_played: int

@dataclass
class HattrickData:
    team: Team
    morale: str
    confidence: str
    economy: Economy
    players: list[Player]
    training: Training
    standing: LeagueStanding
    next_match: Match | None
    last_match: Match | None
    arena_capacity: int
    fetched_date: datetime   # FetchedDate di Hattrick
```

Regole di parsing:

- `xml.etree.ElementTree` per leggere l'XML (niente dipendenze esterne).
- Conversione tipizzata: interi, float, date (`datetime.strptime` con formato
  `"%Y-%m-%d %H:%M:%S"`, timezone HTT = Europe/Stockholm).
- Valori mancanti → `None` o default, mai eccezioni: un file parziale non deve rompere
  tutto l'aggiornamento.
- Il file `<Error>` nell'envelope → `HattrickApiError` con il messaggio di Hattrick.

## 2. Coordinator (`coordinator.py`)

```python
class HattrickDataUpdateCoordinator(DataUpdateCoordinator[HattrickData]):
    def __init__(self, hass, entry, client): ...

    async def _async_update_data(self) -> HattrickData:
        try:
            return await self.client.async_refresh_all(
                hass=self.hass,
                files=self._enabled_files,   # dalle opzioni dell'entry
            )
        except HattrickAuthError as err:
            raise ConfigEntryAuthFailed(...) from err   # → reauth flow
        except HattrickApiError as err:
            raise UpdateFailed(str(err)) from err
```

- `config_entry` passata al costruttore (pattern moderno HA: `config_entry=entry`).
- `update_interval` = `scan_interval` dalle opzioni (default 15 min, min 5).
- `always_update = True` non serve: le entità leggono `coordinator.data`.

## 3. Strategia di polling

Principi (derivati dalle regole CHPP, vedi `docs/02` §6):

- **Default 15 minuti**: i file CHPP sono cachati server-side, pollare più spesso è
  inutile e rischioso.
- **File abilitabili singolarmente** (opzioni): l'utente può disattivare file pesanti o
  inutili (es. `matchesarchive`, `alliances`) per ridurre il numero di download.
- **Modalità "matchday"** (opzione): nelle finestre di partita (es.weekday e ora delle
  partite di lega, tipicamente sabato pomeriggio e mercoledì sera in HTT) il polling
  scende a 5 minuti per intercettare risultati e matchdetails in tempo quasi reale.
  Implementazione: il coordinator confronta l'ora HT corrente con le finestre configurate
  e usa un intervallo ridotto; fuori finestra torna a quello standard.
- **Backoff su errore**: se una chiamata fallisce con 429/5xx, il ciclo successivo
  raddoppia l'intervallo (max 60 min) fino al successo.
- **Download on-demand**: `matchdetails`, `matchlineup`, `matchesarchive` e i servizi
  `get_match_details`/`get_player` non fanno parte del ciclo standard: vengono chiamati
  solo quando servono (servizio o attributo richiesto), così da non sprecare download.

### Quali file nel ciclo standard

| File | Nel ciclo standard? | Motivo |
|------|---------------------|--------|
| teamdetails, team, club | sì | dati base squadra, leggeri |
| economy | sì | cassa (cambia a ogni update economico settimanale) |
| players | sì | rosa (cambia lentamente; cache server-side) |
| training, trainingsummary | sì | allenamento settimanale |
| leaguedetails | sì | classifica (aggiornata dopo le partite) |
| matches | sì | prossime/ultime partite |
| arenadetails | sì (o on-change) | cambia raramente |
| worlddetails | sì | server time e prossimi update HT |
| matchdetails / matchlineup | on-demand | solo per match_id specifico |
| matchesarchive | no (opzionale) | pesante, solo su richiesta |
| cup, alliances | opzionale | diagnostica |

## 4. Caching e persistenza

- Lo stato corrente vive solo in `coordinator.data` (memoria).
- Lo storico (andamento cassa, punti, risultati) lo fornisce il **recorder** di HA sugli
  sensor con `state_class`: basta che l'utente tenga la recorder attiva (default).
- Nessuna scrittura su disco propria: niente file, niente database.
- `restore_state` non serve: al riavvio il primo refresh ripopola tutto.

## 5. Gestione dei fusi orari

- Tutte le date CHPP sono in **HTT (Europe/Stockholm)**.
- Nei sensor le mostriamo convertite nel fuso dell'istanza HA (`dt_util.as_local`),
  mantenendo l'originale HTT negli attributi quando serve (es. per confrontare con il
  calendario di lega).

## 6. Esempio di update completo

1. Il coordinator scade (ogni `scan_interval`).
2. `client.async_refresh_all()` esegue in executor le GET ai file abilitati (in
   parallelo con `asyncio.gather` dove possibile, rispettando un piccolo rate limit
   client-side: max ~1 richiesta ogni 2 secondi).
3. Ogni risposta XML → dataclass; si assembla `HattrickData`.
4. Se `teamdetails` dà `UserID` diverso da quello atteso → `ConfigEntryAuthFailed`
   (token riutilizzato su altro account).
5. `coordinator.async_set_updated_data(data)` → tutte le entità si aggiornano.
6. I sensor calcolano derivati (es. `tsi_totale = sum(p.tsi for p in players)`).
