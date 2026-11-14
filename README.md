# ha-hattrick-integration

Custom integration di **Home Assistant** per monitorare e gestire la propria squadra di
[Hattrick](https://www.hattrick.org) tramite le API ufficiali **CHPP** (Certified Hattrick
Product Provider).

L'integrazione porta in Home Assistant i dati della squadra (economia, rosa, partite,
classifica, allenamento, stadio) come entità `sensor`, ed espone azioni (es. invio degli
ordini di partita) come servizi di HA, così da poterli usare in dashboard Lovelace e
automazioni.

## Documentazione

| Documento | Contenuto |
|-----------|-----------|
| [docs/01-obiettivi-e-panoramica.md](docs/01-obiettivi-e-panoramica.md) | Obiettivi del progetto, casi d'uso, funzionalità previste |
| [docs/02-chpp-api.md](docs/02-chpp-api.md) | Guida completa alle API CHPP: registrazione app, OAuth 1.0a, endpoint, file XML, regole e limiti |
| [docs/03-architettura-integrazione.md](docs/03-architettura-integrazione.md) | Architettura della custom integration: struttura cartelle, manifest, config flow, coordinator, piattaforme |
| [docs/04-entita-e-azioni.md](docs/04-entita-e-azioni.md) | Catalogo delle entità (sensor) e delle azioni (services) pianificate, mappate ai file CHPP |
| [docs/05-modello-dati-e-polling.md](docs/05-modello-dati-e-polling.md) | Modello dati (dataclass), parsing XML, DataUpdateCoordinator e strategia di polling |
| [docs/06-configurazione-utente.md](docs/06-configurazione-utente.md) | Flusso di configurazione per l'utente finale: credenziali CHPP, autorizzazione OAuth, opzioni |
| [docs/07-sviluppo-test-debug.md](docs/07-sviluppo-test-debug.md) | Ambiente di sviluppo, comandi utili, test automatici, hassfest/HACS, debug |
| [docs/08-sicurezza-regole-roadmap.md](docs/08-sicurezza-regole-roadmap.md) | Sicurezza e privacy, regole CHPP da rispettare, roadmap di sviluppo |
| [docs/09-piano-di-lavoro.md](docs/09-piano-di-lavoro.md) | Piano operativo: task T1–T26, dipendenze, criteri di accettazione, milestone M1–M8 |
| [docs/10-handoff-nuova-sessione.md](docs/10-handoff-nuova-sessione.md) | Stato attuale del repo, ambiente di test, comandi rapidi e da dove ripartire (handoff) |

## Stato del progetto

Fase di documentazione e progettazione. Il codice dell'integrazione verrà sviluppato in
`custom_components/hattrick/` seguendo l'architettura descritta in
[docs/03-architettura-integrazione.md](docs/03-architettura-integrazione.md).

## Licenza

Da definire (suggerita: MIT).
