# ha-hattrick-integration

Custom integration di **Home Assistant** per monitorare e gestire la propria squadra di
[Hattrick](https://www.hattrick.org) tramite le API ufficiali **CHPP** (Certified Hattrick
Product Provider, OAuth 1.0a).

L'integrazione porta in Home Assistant i dati della squadra (economia, rosa, partite,
classifica, allenamento, stadio) come entità `sensor`, ed espone azioni (dettaglio
partita/giocatore on-demand, invio ordini di partita, refresh manuale) come servizi di HA,
usabili in dashboard Lovelace e automazioni.

## Funzionalità

- **23 sensor** raggruppati nel dispositivo "squadra": nome squadra, morale, fiducia
  tifosi, cassa, rosa (giocatori, TSI, infortunati, squalificati, forma), fan club,
  settore giovanile, staff, posizione in classifica, prossima/ultima partita, partite
  programmate, entrate/stipendi, allenatore, allenamento, progresso allenamento, stadio,
  orario server HT, più due diagnostici sull'ultima partita (rating e tattica).
- **4 servizi**:

  | Servizio | Cosa fa | Risposta |
  |----------|---------|----------|
  | `hattrick.get_match_details` | dettagli di una partita (gol, tiri, rating, meteo) | sì |
  | `hattrick.get_player` | scheda di un giocatore (skill, forma, TSI, stipendio) | sì |
  | `hattrick.set_match_orders` | invia gli ordini di partita (`matchorders.xml`) | sì (esito) |
  | `hattrick.refresh` | forza l'aggiornamento immediato dei dati | no |

- **Polling configurabile** (5–60 min, default 15) con modalità **matchday**: dentro ±3h
  dalla partita il polling scende a 5 min.
- **File CHPP abilitabili** singolarmente dalle opzioni, inclusi `matchdetails`/`matchlineup`
  on-demand sull'ultima partita.
- Interfaccia in **italiano e inglese**.

## Installazione

### Con il Marketplace di Home Assistant (HA 2026.11+)

1. Vai su **Impostazioni → Marketplace → ⋮ → Repository personalizzati** (o
   "Custom repositories").
2. Aggiungi `https://github.com/CesarStef/ha-hattrick-integration` come repository di
   tipo **Integrazione**.
3. Cerca "Hattrick" nel Marketplace e installalo. Il Marketplace installa le **release**
   (tag `vX.Y.Z`); senza release installa il branch `main`.

### Con HACS (HA ≤ 2026.10)

1. Aggiungi questo repository in HACS come **custom repository** (categoria: Integration).
2. Installa "Hattrick" da HACS e **riavvia Home Assistant**.

### Manuale

Copia `custom_components/hattrick/` in `<config>/custom_components/hattrick/` e riavvia.

## Configurazione

1. Crea un'app CHPP su Hattrick: vai su
   [chpp.hattrick.org](https://chpp.hattrick.org) → "My CHPP apps" → nuova app.
   Imposta un **callback URL** (può essere `oob` per il flusso manuale) e annota
   **Consumer Key** e **Consumer Secret**. Se vuoi inviare ordini di partita, spunta il
   permesso di **scrittura su matchorders**.
2. In Home Assistant: **Impostazioni → Dispositivi e servizi → Aggiungi integrazione →
   "Hattrick"**.
3. Inserisci Consumer Key e Consumer Secret dell'app CHPP.
4. Scegli la modalità:
   - **Automatica (consigliata)**: HA mostra un URL su `chpp.hattrick.org`; aprilo,
     fai login su Hattrick e autorizza l'app, poi incolla il **verifier** mostrato.
   - **Manuale**: incolla direttamente Access Token e Access Token Secret (se li hai già
     ottenuti altrove).
5. Fatto: l'integrazione valida i dati con `teamdetails.xml` e crea le entità.

### Opzioni (per squadra)

Da **Impostazioni → Dispositivi e servizi → Hattrick → Configura** puoi cambiare:

- **intervallo di aggiornamento** (5–60 minuti);
- **file CHPP abilitati** (puoi disattivare quelli che non ti servono per ridurre i
  download, o attivare `matchdetails`/`matchlineup` per i sensor diagnostici);
- **modalità matchday** (polling a 5 min dentro la finestra partita).

## Uso

- **Dashboard**: vedi `examples/dashboard.yaml` — una dashboard pronta con panoramica,
  rosa, partite, allenamento/stadio, club e diagnostici. Importala in una dashboard in
  modalità YAML e adatta gli `entity_id` ai tuoi.
- **Automazioni**: vedi `examples/automations.yaml` — notifica 30 min prima della
  partita, allarme cassa bassa, promemoria infortunati, salvataggio rating ultima
  partita, esempio di invio ordini.
- **Servizi**: da **Strumenti sviluppatore → Azioni** (es. `hattrick.get_match_details`
  con `match_id` preso dall'attributo del sensor `prossima_partita`).

## FAQ

**"Only the app owner can authorize the app" — perché?**
Finché un'app CHPP **non è certificata** da Hattrick, solo il proprietario dell'app può
autorizzarla via OAuth. Quando l'app sarà certificata (milestone M8 del progetto, vedi
`docs/11-chpp-certification-request.md`) qualsiasi manager potrà autorizzarla. Nel
frattempo puoi usare solo la tua app CHPP personale.

**"Credenziali CHPP non valide" nel config flow**
Consumer Key/Secret errati o app CHPP non attiva: ricontrolli su chpp.hattrick.org.

**"Unknown error occurred"**
Di solito è un errore di rete o un refusal di CHPP non tradotto: controlla i log di Home
Assistant (`homeassistant.log`) e riprova.

**Il token è stato revocato**
HA mostra un avviso di **ri-autenticazione**: segui il flusso e ri-autorizza l'app.

**Gli ordini di partita non vengono inviati**
`hattrick.set_match_orders` richiede il permesso di **scrittura su matchorders** sull'app
CHPP: abilitalo nelle impostazioni dell'app su chpp.hattrick.org.

**Quanto pesa sui limiti CHPP?**
Default 15 min di polling, solo file XML ufficiali (`chppxml.ashx`), niente scraping.
Con la modalità matchday il polling scende a 5 min solo dentro ±3h dalla partita.

## Documentazione tecnica

| Documento | Contenuto |
|-----------|-----------|
| [docs/01-obiettivi-e-panoramica.md](docs/01-obiettivi-e-panoramica.md) | Obiettivi del progetto, casi d'uso, funzionalità previste |
| [docs/02-chpp-api.md](docs/02-chpp-api.md) | Guida completa alle API CHPP: registrazione app, OAuth 1.0a, endpoint, file XML, regole e limiti |
| [docs/03-architettura-integrazione.md](docs/03-architettura-integrazione.md) | Architettura della custom integration: struttura cartelle, manifest, config flow, coordinator, piattaforme |
| [docs/04-entita-e-azioni.md](docs/04-entita-e-azioni.md) | Catalogo delle entità (sensor) e delle azioni (services), mappate ai file CHPP |
| [docs/05-modello-dati-e-polling.md](docs/05-modello-dati-e-polling.md) | Modello dati (dataclass), parsing XML, DataUpdateCoordinator e strategia di polling |
| [docs/06-configurazione-utente.md](docs/06-configurazione-utente.md) | Flusso di configurazione per l'utente finale: credenziali CHPP, autorizzazione OAuth, opzioni |
| [docs/07-sviluppo-test-debug.md](docs/07-sviluppo-test-debug.md) | Ambiente di sviluppo, comandi utili, test automatici, hassfest/HACS, debug |
| [docs/08-sicurezza-regole-roadmap.md](docs/08-sicurezza-regole-roadmap.md) | Sicurezza e privacy, regole CHPP da rispettare, roadmap di sviluppo |
| [docs/09-piano-di-lavoro.md](docs/09-piano-di-lavoro.md) | Piano operativo: task T1–T26, dipendenze, criteri di accettazione, milestone M1–M8 |
| [docs/10-handoff-nuova-sessione.md](docs/10-handoff-nuova-sessione.md) | Stato attuale del repo, ambiente di test, comandi rapidi e da dove ripartire (handoff) |
| [docs/11-chpp-certification-request.md](docs/11-chpp-certification-request.md) | Bozza (in inglese) della richiesta di certificazione CHPP a Hattrick |

## Stato del progetto

Milestone M1–M4 completate (release `v0.4.0`): config flow OAuth, coordinator multi-file,
23 sensor, 4 servizi, 73 test verdi, coverage ~94%. Prossime milestone: esempi/README
(M5, in corso), qualità e diagnostics (M6), release pubblica v1.0.0 (M7), certificazione
CHPP (M8). Vedi [docs/09-piano-di-lavoro.md](docs/09-piano-di-lavoro.md).

## Disclaimer

Questo progetto è **vibe-codato**: è stato generato e mantenuto con un agente di coding AI
([Mistral Vibe](https://mistral.ai)), non è stato revisionato riga per riga da un essere
umano. Il codice è coperto da test automatici (73 test) e segue le linee guida di HA, ma
**usalo a tuo rischio**: prima di affidargli automazioni importanti (es. ordini di partita
in matchday) verifica i dati reali nella tua istanza.

In particolare:

- l'app CHPP di riferimento **non è ancora certificata** da Hattrick (milestone M8), quindi
  solo il proprietario dell'app può autorizzarla;
- i nomi dei campi XML delle API CHPP sono basati sulla documentazione pubblica e possono
  differire dalle risposte reali: il primo avvio con un account reale è il collaudo vero;
- la logica di sicurezza (mai loggare token, mai salvare password, rispetto dei limiti di
  download CHPP) è implementata ma va ricontrollata prima di un uso in produzione.

## Licenza

[Apache License 2.0](LICENSE) — Copyright 2026 Stefano Cattonar.
