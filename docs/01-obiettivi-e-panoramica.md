# 01 — Obiettivi e panoramica del progetto

## Cos'è

`ha-hattrick-integration` è una **custom integration** di Home Assistant che si collega alle
API ufficiali **CHPP** di Hattrick e porta i dati della propria squadra dentro Home
Assistant, dove è possibile visualizzarli in dashboard e usarli in automazioni.

Hattrick è un manageriale calcistico online: ogni utente gestisce una squadra (rosa,
economia, tattiche, allenamento, stadio, partite). CHPP è il programma di Hattrick che
permette a prodotti di terze parti certificati di accedere ai dati dell'utente tramite API.

## Obiettivi

1. **Monitoraggio centralizzato**: portare in HA i principali indicatori della squadra
   (cassa, tifosi, morale, fiducia, classifica, prossima partita, allenamento, stadio).
2. **Dettaglio rosa**: esporre i dati dei giocatori (skill, forma, TSI, stipendio,
   infortuni, squalifiche) come entità o attributi di entità.
3. **Partite**: tracciare calendario, risultati, formazioni e statistiche delle partite.
4. **Azioni**: permettere di inviare comandi a Hattrick da HA, in primo luogo gli
   **ordini di partita** (formazione, tattica, capitano, rigoristi, sostituzioni) tramite
   il file CHPP `matchorders.xml`.
5. **Automazioni**: abilitare notifiche e automazioni HA basate sugli eventi di Hattrick
   (es. "notifica 30 minuti prima della partita", "avvisa se la cassa scende sotto X",
   "notifica se un giocatore è infortunato").

## Casi d'uso tipici

- Dashboard Lovelace "Hattrick" con panoramica squadra, prossima partita e ultimi
  risultati.
- Notifica push quando inizia una partita della propria squadra.
- Automazione che invia gli ordini di partita preparati in anticipo (es. la sera prima
  del match).
- Allerte se morale/fiducia crollano, se ci sono troppi infortunati, se la squadra è in
  zona retrocessione.
- Storico partite e andamento economico su recorder/InfluxDB tramite i sensor HA.

## Principi di progetto

- **Solo API ufficiali CHPP**: niente scraping delle pagine web di Hattrick (vietato dal
  regolamento CHPP). Tutti i dati passano da `chpp.hattrick.org/chppxml.ashx`.
- **Rispetto dei limiti**: Hattrick impone limiti anti-abuso sui download dei file XML e
  cachea lato server le risposte. L'integrazione deve pollare in modo conservativo
  (default: ogni 15 minuti) e mai in modo aggressivo.
- **Privacy**: le credenziali OAuth dell'utente restano nell'istanza HA dell'utente
  (config entry), non vengono mai inviate a server terzi né loggate.
- **UX nativa HA**: configurazione tramite UI (config flow), entità con `device_info`
  raggruppate per squadra, nomi tradotti (italiano e inglese), servizi con selettori.
- **Distribuzione via HACS**: l'integrazione è pensata per essere installabile tramite
  HACS (Home Assistant Community Store), quindi richiede `hacs.json` e `version` nel
  manifest.

## Utenti target

- Manager di Hattrick che usano già Home Assistant e vogliono integrare i dati della
  squadra nel proprio ecosistema domotico.
- Utenti che vogliono automazioni "manageriali" (promemoria partite, allerte stato
  squadra) senza aprire il sito di Hattrick.

## Non-obiettivi (per ora)

- Gestire più squadre per lo stesso account Hattrick (un account Hattrick ha una sola
  squadra attiva; in futuro si valuterà il supporto multi-account come config entry
  separati).
- Sostituire strumenti CHPP completi come Hattrick Organizer (HO!): qui ci concentriamo
  su monitoraggio e poche azioni mirate, non su gestione avanzata del calciomercato.
- Non memorizzare dati di altri utenti: il regolamento CHPP vieta di conservare
  informazioni su squadre diverse dalla propria.

## Glossario rapido

| Termine | Significato |
|---------|-------------|
| CHPP | Certified Hattrick Product Provider: programma di accesso API ufficiale di Hattrick |
| OAuth 1.0a | protocollo di autenticazione usato da CHPP (firma HMAC-SHA1 delle richieste) |
| File XML CHPP | endpoint dati di Hattrick (es. `teamdetails.xml`, `players.xml`, `matches.xml`) |
| Config entry | istanza configurata dell'integrazione in HA (qui: un account/squadra Hattrick) |
| Coordinator | `DataUpdateCoordinator` di HA, interroga le API a intervalli e distribuisce i dati alle entità |
| HACS | Home Assistant Community Store, il marketplace non ufficiale per le custom integration |
| TSI | Total Skill Index, indice di forza complessivo di un giocatore |
| HTT | Hattrick Time: fuso orario ufficiale di Hattrick (CET/CEST, Svezia) |
