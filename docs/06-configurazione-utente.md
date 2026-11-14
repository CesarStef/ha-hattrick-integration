# 06 — Flusso di configurazione per l'utente finale

Come l'utente aggiunge la propria squadra di Hattrick in Home Assistant. Tutta la
configurazione avviene dalla UI (config flow), senza toccare YAML.

## 1. Aggiunta dell'integrazione

1. L'utente installa l'integrazione via **HACS** (Repository → cerca "Hattrick" →
   Download) oppure, da **HA 2026.11** con il **Marketplace** integrato, aggiungendo il
   repository custom (Marketplace → ⋮ → "Custom repositories" → URL
   `https://github.com/CesarStef/ha-hattrick-integration`, categoria *Integration*),
   poi Marketplace → Hattrick → installa. In alternativa copia
   `custom_components/hattrick/` in `<config>/custom_components/`.
2. Riavvia HA (solo la prima volta, dopo l'installazione).
3. Va in **Impostazioni → Dispositivi e servizi → Aggiungi integrazione** e cerca
   **"Hattrick"**.

## 2. Scelta della modalità di autenticazione

Al primo passo (`async_step_user`) l'utente sceglie come collegare l'account:

| Modalità | Come funziona | Quando usarla |
|----------|---------------|---------------|
| **Automatica (consigliata)** | HA genera il request token, mostra un link a `chpp.hattrick.org/oauth/authorize.aspx?oauth_token=...`; l'utente apre il link, fa login su Hattrick, clicca **Allow** e incolla il **verifier** mostrato. HA scambia il verifier con l'access token. | Sempre, se possibile |
| **Manuale** | L'utente ha già una coppia Consumer Key/Secret (registrata su chpp.hattrick.org) e una coppia Access Token/Secret (ottenuta autorizzando la propria app), e le incolla direttamente. | Utenti avanzati, o se il flusso automatico dà problemi |

> In nessuna modalità l'utente inserisce la password di Hattrick: il login avviene solo
> sul sito ufficiale CHPP (regola CHPP, vedi `docs/02` §6).

## 3. Passi del flusso automatico (config flow)

1. **user**: scelta "automatica".
2. **auth**: HA chiama `requesttoken.aspx`, poi mostra:
   - il link di autorizzazione (con `oauth_token`);
   - un campo di testo per il **verifier** (codice che Hattrick mostra dopo il consenso,
     oppure `oauth_verifier` nel callback se configurato).
3. **token**: HA chiama `accesstoken.aspx` con il verifier e ottiene access token +
   secret. Se fallisce → errore "invalid_verifier" con possibilità di riprovare.
4. **validate**: HA chiama `teamdetails.xml` per verificare che il token funzioni e
   leggere `UserID`/`TeamID`. Se il token è revocato → errore "auth".
5. Creazione della **config entry** con:
   - `unique_id = UserID` (un account Hattrick = una entry; niente doppioni);
   - `title = TeamName` (nome della squadra, preso da teamdetails);
   - dati sensibili (consumer key/secret, access token/secret) salvati nella entry
     (non in `options`, che è visibile in chiaro nelle esportazioni).

## 4. Opzioni dell'integrazione (OptionsFlow)

Modificabili da **Impostazioni → Dispositivi e servizi → Hattrick → Configura**:

- **Intervallo di aggiornamento** (minuti): default 15, minimo 5.
- **File CHPP da scaricare**: checkbox per abilitare/disabilitare i singoli file
  (es. disattivare `matchesarchive`).
- **Modalità matchday**: polling a 5 minuti nelle finestre partita (sabato pomeriggio,
  mercoledì sera HTT, configurabili).
- **Lingua dei nomi entità**: it/en (default: lingua di HA).

## 5. Reauth (token revocato)

Se Hattrick revoca l'access token (l'utente revoca i permessi da Hattrick, o scade),
la prossima chiamata dà errore di autenticazione:

1. il coordinator solleva `ConfigEntryAuthFailed`;
2. HA apre automaticamente il flusso di **reauth** (`async_step_reauth`);
3. l'utente ripete solo il passo "Allow" su chpp.hattrick.org e incolla il nuovo
   verifier;
4. la entry viene aggiornata con il nuovo token, senza perdere entità e automazioni.

## 6. Aggiunta di un secondo account (futuro)

Un account Hattrick ha una sola squadra attiva, ma l'utente può avere più account.
Il flusso permette già di aggiungere più config entry (una per account, `unique_id`
diverso). Ogni entry crea il proprio device "squadra" in HA.

## 7. Cosa vede l'utente dopo la configurazione

- Un **dispositivo** "NomeSquadra" (manufacturer Hattrick) con tutte le entità
  (cassa, morale, classifica, prossima partita, rosa, allenamento, stadio...).
- I **servizi** `hattrick.*` in Strumenti per sviluppatori → Azioni.
- Eventuali **repair**/avvisi se il token è revocato o mancano permessi (es. scrittura
  ordini partita non autorizzata).
