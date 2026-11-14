# 02 — Guida alle API CHPP di Hattrick

Questa guida raccoglie tutto quello che serve sapere per dialogare con le API CHPP:
registrazione dell'applicazione, autenticazione OAuth 1.0a, endpoint, file XML
principali, regole e limiti. È la base su cui poggia il client API dell'integrazione
(descritto in `docs/03` e `docs/05`).

Fonti ufficiali di riferimento:

- Portale CHPP: <https://chpp.hattrick.org>
- Wiki di Hattrick (sezione CHPP): <https://wiki.hattrick.org/wiki/CHPP_Manual> e
  categoria "CHPP XML Pages" (<https://wiki.hattrick.org/wiki/Category:CHPP_XML_Pages>)
- Blog degli sviluppatori di Hattrick: <https://devblog.hattrick.org>

## 1. Registrazione dell'applicazione CHPP

1. Vai su <https://chpp.hattrick.org> e registra un nuovo "CHPP product".
2. Hattrick ti rilascia una coppia di credenziali dell'**applicazione**:
   - **Consumer Key**
   - **Consumer Secret**
3. Nella pagina dell'app imposti anche:
   - **Callback URL** (URL a cui Hattrick reindirizza l'utente dopo l'autorizzazione;
     per un'app desktop/HA si usa spesso il flusso con codice/verifier "out-of-band").
   - **Permessi (scope)** richiesti: es. lettura dati squadra, e in fase successiva
     scrittura ordini partita (`matchorders`).
4. Per essere **certificati CHPP** e comparire nella lista ufficiale dei prodotti serve
   una richiesta di approvazione separata (voir `docs/08`). In fase di sviluppo puoi già
   usare l'app sui tuoi dati personali.

> Importante: il Consumer Secret dell'applicazione non va mai distribuito lato client in
> chiaro in app pubbliche; in una custom integration HA gira solo dentro l'istanza
> dell'utente, quindi il rischio è contenuto, ma va comunque trattato come segreto.

## 2. Autenticazione: OAuth 1.0a a tre zampe (3-legged)

CHPP usa **OAuth 1.0a** con firma **HMAC-SHA1**. Il flusso completo:

```
App (HA)                    chpp.hattrick.org                    Utente (browser)
   |                                |                                  |
   |-- 1. POST /oauth/requesttoken.aspx (firmata con consumer key/secret)
   |<-- oauth_token + oauth_token_secret (request token)              |
   |                                |                                  |
   |-- 2. URL authorize: /oauth/authorize.aspx?oauth_token=...  ----->|
   |                                |<-- login + "Allow" -------------|
   |                                |-- redirect a callback con oauth_verifier
   |<-- 3. l'utente copia il verifier (o arriva via callback)         |
   |                                |                                  |
   |-- 4. POST /oauth/accesstoken.aspx (request token + verifier)     |
   |<-- oauth_token + oauth_token_secret (ACCESS token, long-lived)   |
   |                                |                                  |
   |-- 5. GET chppxml.ashx?file=... firmata con consumer + access token
   |<-- XML con i dati                                                |
```

### Endpoint OAuth

| Passo | Endpoint | Metodo |
|-------|----------|--------|
| Request token | `https://chpp.hattrick.org/oauth/requesttoken.aspx` | POST (OAuth1) |
| Autorizzazione utente | `https://chpp.hattrick.org/oauth/authorize.aspx?oauth_token=...` | GET (browser utente) |
| Access token | `https://chpp.hattrick.org/oauth/accesstoken.aspx` | POST (OAuth1 + verifier) |

### Dettaglio del passo 2 (autorizzazione)

- L'utente deve aprire l'URL `authorize.aspx` nel browser, fare login su Hattrick e
  cliccare **Allow**.
- Hattrick mostra poi un **verifier** (codice) da copiare, oppure reindirizza al callback
  registered con `oauth_verifier` nei query param.
- **Mai** chiedere all'utente username/password di Hattrick: il login avviene solo sul
  sito ufficiale `chpp.hattrick.org` (il regolamento CHPP lo vieta esplicitamente).

### Dettaglio del passo 5 (chiamate API)

Ogni richiesta ai dati è una GET firmata OAuth1:

```
GET https://chpp.hattrick.org/chppxml.ashx?file=teamdetails&version=3.6
Authorization: OAuth oauth_consumer_key="...", oauth_token="...",
  oauth_signature_method="HMAC-SHA1", oauth_timestamp="...", oauth_nonce="...",
  oauth_version="1.0", oauth_signature="..."
```

In Python la firma si genera comodamente con `requests-oauthlib` (`OAuth1Session`), che
è la libreria che useremo nel client API (vedi `docs/03` e `docs/05`).

## 3. Struttura della risposta XML

Ogni file XML risponde con un envelope comune:

```xml
<HattrickData>
  <FileName>teamdetails</FileName>
  <Version>3.6</Version>
  <UserID>1234567</UserID>
  <FetchedDate>2026-11-14 10:30:00</FetchedDate>
  <!-- contenuto specifico del file -->
  <Team> ... </Team>
  <User> ... </User>
</HattrickData>
```

- In caso di errore c'è un elemento `<Error>` (es. token non valido, file non
  autorizzato, limite superato).
- Le date sono in **HTT (Hattrick Time)**, fuso CET/CEST della Svezia, formato
  `yyyy-MM-dd HH:mm:ss`.
- Il server **cachea** i file: pollare lo stesso file a intervalli ravvicinati restituisce
  spesso gli stessi dati (`FetchedDate` identico). Da qui la scelta di un intervallo di
  polling conservativo (vedi `docs/05`).

## 4. File XML principali per l'integrazione

Tutti i file si richiedono a:

```
https://chpp.hattrick.org/chppxml.ashx?file=<nome>&version=<versione>&<parametri opzionali>
```

| File | Versione tipica | Contenuto | Uso nell'integrazione |
|------|----------------|-----------|------------------------|
| `teamdetails` | 3.x | Dati squadra e manager: TeamID, TeamName, arena, lega, regione, colore maglia, stile gioco, livello allenatore | Device info, sensor squadra |
| `team` | 1.x | Morale (`TeamSpirit`) e fiducia dei tifosi (`Confidence`) | Sensor morale/fiducia |
| `club` | 1.x | Fan club, settore giovanile, staff (preparatore atletico, medico, psicologo, portavoce) | Sensor club/staff |
| `economy` | 1.x | Cassa, entrées previste, sponsor, stipendi, interessi, Maintenance costi | Sensor economia |
| `players` | 3.x | Rosa completa: skill, forma, esperienza, TSI, stipendio, specialità, infortuni, squalifiche, capitano | Sensor rosa + attributi giocatori |
| `training` | 1.x | Allenamento corrente: tipo skill, intensità, livello allenatore | Sensor allenamento |
| `trainingsummary` | 1.x | Riepilogo allenamento della settimana, progressi skill | Sensor/weekly training |
| `leaguedetails` | 2.x | Classifica del girone: posizione, punti, gol fatti/subiti, serie | Sensor classifica |
| `matches` | 2.x/3.x | Partite recenti e future: data, avversario, casa/trasferta, gol, matchID | Sensor prossima/ultima partita |
| `matchesarchive` | 1.x | Archivio storico partite (parametri: season, teamID) | Storico (opzionale, pesante) |
| `matchdetails` | 3.x | Dettaglio partita: gol, possesso, tiri, rating per reparto, eventi | Attributi sensor partita |
| `matchlineup` | 2.x | Formación e tattica usata, rating squadra | Sensor tattica |
| `arenadetails` | 1.x | Stadio: capacità, naming rights, livello settori | Sensor stadio |
| `world` / `worldDetails` | 1.x | Dati globali: leghe, server time, prossima training/economy update | Sensor "prossimo update HT" |
| `cup`, `cups` | 1.x | Coppe a cui si partecipa | Sensor coppe |
| `alliances` | 1.x | Alleanze | Diagnostica |
| `matchorders` | 1.x | **Scrittura**: invio ordini di partita (formazione, tattica, sostituzioni, capitano, rigoristi) | Servizio `set_match_orders` |

Parametri utili (dipendono dal file):

- `matches`: `matchID`, `isYouth`, `order=asc|desc`, `lastMatchDate`, `firstMatchDate`
  (default: ultime 4 settimane + future).
- `matchdetails` / `matchlineup`: `matchID` (obbligatorio).
- `players`: `playerID`, `includeMatchInfo`, `includeValues`.
- `matchesarchive`: `season`, `teamID`, `matchType`.
- `leaguedetails`: `leagueID`, `season`.

> Le versioni esatte dei file cambiano nel tempo: nel codice terremo una mappa
> `FILE_VERSIONS` in `const.py` e la aggiorneremo quando Hattrick rilascia nuove versioni
> (annunciate sul devblog e sulla wiki).

## 5. Scrittura: ordini di partita (`matchorders`)

L'unica scrittura che prevediamo (almeno all'inizio) è l'invio degli **ordini di
partita** tramite `matchorders.xml`, che richiede che l'app CHPP abbia il permesso di
scrittura sugli ordini.

- Si invia una richiesta **POST** a `chppxml.ashx?file=matchorders` con corpo XML
  contenente: `MatchID`, `TeamID`, tattica (`TacticType`, `TacticSkill`), aggressività,
  pressing, `Attitude`, formazione (`lineup` con 11 titolari + 7 panchina), ordini
  individuali, capitano, taker dei calci piazzati, rigoristi, sostituzioni condizionali.
- La risposta conferma l'esito; conviene sempre rileggere `matchlineup` dopo l'invio per
  verificare che Hattrick abbia applicato gli ordini.
- Da HA l'azione sarà un **servizio** (es. `hattrick.set_match_orders`) con selettori per
  i campi principali (vedi `docs/04`).

## 6. Regole e limiti CHPP da rispettare

Regole ufficiali (dal CHPP Manual e dal regolamento):

1. **Solo i file XML**: è vietato scaricare/scansionare qualsiasi altra parte del sito
   Hattrick dalle app CHPP.
2. **Mai credenziali di login**: non è consentito memorizzare username e password (o
   codici di sicurezza) degli utenti. Si usa solo OAuth. (Eccezione: manager assistant
   autorizzati, non il nostro caso.)
3. **Solo la propria squadra**: non è consentito memorizzare dati di altre squadre.
4. **Limiti di download**: Hattrick applica limiti anti-abuso (non sempre pubblici) e
   cache server-side. Best practice:
   - pollare al massimo ogni 5–15 minuti (default 15);
   - evitare file pesanti non necessari (`matchesarchive` solo on-demand);
   - usare i parametri dei file per filtrare (es. date delle partite) invece di
     scaricare tutto;
   - non ritentare in loop in caso di errore: usare backoff esponenziale.
5. **App a pagamento**: se un prodotto CHPP fa pagare, deve informare gli utenti che
   Hattrick/Extralives non sono responsabili dei pagamenti. (La nostra sarà gratuita.)
6. **Certificazione**: per essere elencati come prodotto CHPP ufficiale serve
   l'approvazione di Hattrick; durante lo sviluppo si può usare l'API con il proprio
   account.
7. **Sicurezza del dominio**: l'autorizzazione OAuth deve avvenire solo su
   `chpp.hattrick.org` (l'utente deve verificare l'URL nel browser).

## 7. Esempio pratico di chiamata (Python, con requests-oauthlib)

```python
from requests_oauthlib import OAuth1Session

CHPP_BASE = "https://chpp.hattrick.org"

client = OAuth1Session(
    consumer_key,            # consumer key dell'app
    client_secret=consumer_secret,
    resource_owner_key=access_token,       # access token dell'utente
    resource_owner_secret=access_token_secret,
)

r = client.get(
    f"{CHPP_BASE}/chppxml.ashx",
    params={"file": "teamdetails", "version": "3.6"},
    timeout=30,
)
r.raise_for_status()
import xml.etree.ElementTree as ET
root = ET.fromstring(r.text)
team_name = root.findtext("./Team/TeamName")
```

Nel client reale dell'integrazione (`api.py`) questa logica sarà wrappata in una classe
`HattrickCHPPClient` con metodi tipizzati per ogni file e parsing in dataclass (vedi
`docs/05`), eseguita in executor perché `requests` è bloccante.

## 8. Gestione errori comuni

| Situazione | Segnale | Gestione in HA |
|------------|---------|----------------|
| Access token revocato/scaduto | `<Error>` con codice auth / HTTP 401 | `ConfigEntryAuthFailed` → reauth flow (vedi `docs/06`) |
| File non autorizzato per l'app | `<Error>` "not authorized" | log + disabilitare quel file nelle opzioni |
| Limite download superato | `<Error>` / HTTP 429 | backoff esponenziale, ridurre frequenza polling |
| File non valido / parametri errati | `<Error>` con messaggio | log dell'errore, non bloccare gli altri file |
| Timeout di rete | eccezione `requests` | `UpdateFailed` nel coordinator, retry al prossimo ciclo |
