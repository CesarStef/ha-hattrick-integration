# 07 — Setup di sviluppo, test e debug

Come preparare l'ambiente per sviluppare l'integrazione, eseguirla in una HA di test,
lanciare i test automatici e validare il pacchetto prima di distribuirlo.

## 1. Ambiente di sviluppo

Opzioni consigliate, dalla più semplice alla più completa:

1. **HA in Docker + cartella custom_components montata**:
   ```bash
   docker run -d --name homeassistant --privileged \
     -v /percorso/config-ha:/config \
     -v /percorso/repo/ha-hattrick-integration/custom_components:/config/custom_components:ro \
     -p 8123:8123 ghcr.io/home-assistant/home-assistant:stable
   ```
2. **Dev container / VS Code** con l'estensione ufficiale "Home Assistant Config Helper",
   che dà linting e autocompletamento sulle API HA.
3. **Core checkout** (per chi vuole contribuire a HA stesso, non necessario qui):
   clone di `home-assistant/core` con symlink di `custom_components/hattrick`.

Requisiti locali: Python 3.12+ (quello richiesto dalle HA recenti), `git`, `pip`.

## 2. Setup del progetto

```bash
git clone <repo> ha-hattrick-integration
cd ha-hattrick-integration
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt   # pytest, pytest-homeassistant-custom-component, ecc.
```

`requirements_test.txt` conterrà (da creare):

```
pytest
pytest-asyncio
pytest-homeassistant-custom-component
requests-oauthlib
voluptuous
```

## 3. Esecuzione in HA di test

- Dopo aver copiato/smontato `custom_components/hattrick`, riavvia HA.
- Aggiungi l'integrazione da UI. Per i test di sviluppo senza un account CHPP reale:
  - usa la **modalità manuale** con credenziali di un'app CHPP di test registrata su
    chpp.hattrick.org, autorizzata sul proprio account;
  - oppure intercetta le chiamate in `api.py` con un mock (vedi test).
- Per ricaricare senza riavviare: **Strumenti per sviluppatori → YAML → "Ricarica
  integrazioni personalizzate"** (o il servizio `homeassistant.reload_config_entry`).

## 4. Test automatici (`tests/`)

Framework: `pytest-homeassistant-custom-component` (replica l'ambiente HA in-process).

Struttura:

```
tests/
├── conftest.py            # fixture hass, mock del client CHPP, config entry di test
├── fixtures/              # XML CHPP reali (copiati/sanificati) per ogni file
│   ├── teamdetails.xml
│   ├── players.xml
│   ├── matches.xml
│   └── ...
├── test_config_flow.py    # flusso UI: happy path, verifier errato, reauth
├── test_coordinator.py    # update OK, errore auth → ConfigEntryAuthFailed, UpdateFailed
├── test_sensor.py         # stati e attributi dei sensor principali
└── test_services.py       # set_match_orders, refresh, get_match_details
```

Pattern: il client `HattrickCHPPClient` viene patchato con un `MockCHPPClient` che legge
i fixture XML, così i test non fanno rete.

Comandi:

```bash
pytest                          # tutti i test
pytest tests/test_sensor.py -v  # un file
pytest --cov=custom_components/hattrick  # copertura
```

## 5. Lint e formattazione

```bash
pip install ruff black isort
ruff check custom_components/ tests/
ruff format custom_components/ tests/
```

Config in `pyproject.toml` (da creare): regole ruff standard + `flake8-pytest-style`,
line-length 100, target py312.

## 6. Validazione del pacchetto (CI)

Due workflow GitHub Actions in `.github/workflows/`:

- **hassfest** (action ufficiale `home-assistant/actions/hassfest@master`): valida
  `manifest.json` (chiavi ordinate, versioni pinnate, ecc.).
- **HACS validation** (action `hacs/action@main`): valida `hacs.json` e la struttura del
  repo per la distribuzione via HACS.

Entrambi girano a ogni push/PR. Inoltre `hassfest` controlla che `services.yaml` sia
coerente con i servizi registrati nel codice.

## 7. Debug

- Log dell'integrazione: `logger: custom_components.hattrick: debug` in
  `configuration.yaml` (temporaneo, in test):
  ```yaml
  logger:
    default: info
    logs:
      custom_components.hattrick: debug
  ```
- I log **non devono mai** contenere token o secret: in `api.py` il logging dei
  parametri OAuth è disabilitato/mascherato.
- Ispezione stato: Strumenti per sviluppatori → Stati (entità `sensor.*`), e
  "Attributi" per vedere i dizionari completi.
- Test manuale di una singola chiamata CHPP: script in `scripts/chpp_probe.py` (da
  creare) che, con le credenziali da env var, chiama un file XML e stampa il risultato —
  utile per verificare versioni e parametri senza passare da HA.
- Errori comuni:
  - `ConfigEntryAuthFailed` → token revocato: rifare reauth;
  - `UpdateFailed` con messaggio CHPP → leggere `<Error>` restituito da Hattrick;
  - entità mancanti dopo l'aggiunta → controllare che il file CHPP sia abilitato nelle
    opzioni e che l'app CHPP abbia i permessi necessari.

## 8. Release e distribuzione

1. Bump di `version` in `manifest.json` (SemVer: `MAJOR.MINOR.PATCH`).
2. Commit + tag `vX.Y.Z` su GitHub: HACS installa le **release**, non il branch main.
3. Verifica che le action hassfest/HACS passino sulla PR.
4. README con istruzioni di installazione HACS e screenshot della dashboard di esempio.
5. (Futuro) richiesta di certificazione CHPP a Hattrick per comparire nella lista
   ufficiale — vedi `docs/08`.
