# 08 — Sicurezza, regole CHPP e roadmap

## 1. Sicurezza e privacy

- **Credenziali OAuth**: consumer key/secret e access token/secret dell'utente sono salvati
  nella config entry di HA (in `.storage/core.config_entries`, protetto dai permessi del
  file system di HA). Non vengono mai inviati a server terzi, non vengono mai loggati,
  non finiscono in diagnostica/support dump (da escludere esplicitamente in
  `async_get_diagnostics` se implementata).
- **Solo HTTPS**: tutte le chiamate vanno su `https://chpp.hattrick.org`.
- **Verifica del dominio di autorización**: nel config flow mostriamo all'utente l'URL
  completo `chpp.hattrick.org/oauth/authorize.aspx` e gli chiediamo di verificare il
  lucchetto nel browser prima di fare login (anti-phishing, come richiesto da CHPP).
- **Nessuna password**: l'integrazione non chiede né memorizza la password Hattrick
  (vietato dal regolamento CHPP).
- **Dati di altri utenti**: l'integrazione legge solo i file relativi all'utente
  autorizzato (la propria squadra). È vietato memorizzare dati di altre squadre.
- **Diagnostica**: se implementiamo `diagnostics`, redigere token, consumer secret e
  qualsiasi dato personale; includere solo ID squadra, versioni file e statistiche di
  polling.
- **Aggiornamenti**: le dipendenze (`requirements` nel manifest) sono pinnate a versione
  esatta; HACS/HA le installa solo da PyPI.

## 2. Regole CHPP da rispettare (riepilogo operativo)

1. Usare **solo** i file XML di `chppxml.ashx`: niente scraping di pagine HTML di
   Hattrick.
2. Non memorizzare **mai** login/password/codici di sicurezza degli utenti.
3. Non memorizzare dati di squadre diverse dalla propria.
4. Rispettare i **limiti di download** (cache server-side + limiti anti-abuso): polling
   conservativo (default 15 min), backoff sugli errori, niente retry forsennati.
5. L'app è gratuita: se in futuro diventasse a pagamento, va dichiarato chiaramente che
   Hattrick/Extralives non sono responsabili dei pagamenti.
6. Per la **certificazione CHPP** (lista ufficiale dei prodotti): richiesta a Hattrick
   dopo aver raggiunto una certa maturità; durante lo sviluppo si può usare l'API con il
   proprio account.

## 3. Roadmap

| Milestone | Contenuto | Dipende da |
|-----------|-----------|------------|
| **M1 — Fondamenta** | Struttura repo, manifest, hacs.json, config flow (manuale + automatico), client OAuth, coordinator, sensor base (team, morale, fiducia, cassa) | docs 02, 03, 06 |
| **M2 — Squadra completa** | Sensor rosa (giocatori, TSI, infortuni, squalifiche), classifica, prossima/ultima partita, allenamento, stadio | M1 |
| **M3 — Partite in dettaglio** | Servizi `get_match_details` / `get_player` con risposta, sensor dettaglio partita, modalità matchday | M2 |
| **M4 — Azioni** | Servizio `set_match_orders` (ordini partita a CHPP), `refresh`; gestione permessi scrittura | M1 + permesso CHPP |
| **M5 — UX e dashboard** | Traduzioni it/en complete, icone, dashboard Lovelace di esempio in `docs/` o `examples/`, automazioni di esempio | M2 |
| **M6 — Test e CI** | Suite pytest completa (config flow, coordinator, sensor, servizi), workflow hassfest + HACS, copertura > 80% | M1–M4 |
| **M7 — Prima release HACS** | Tag `v0.1.0`, README con installazione, release notes | M6 |
| **M8 — Certificazione CHPP** | Documentazione pubblica, richiesta di approvazione a Hattrick, adegamento a eventuali richieste | M7 |

## 4. Rischi e mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Cambio di versione dei file CHPP da parte di Hattrick | `FILE_VERSIONS` centralizzato in `const.py`; test con fixture aggiornati; monitorare devblog/wiki |
| Limite download superato (429) | backoff esponenziale, riduzione frequenza, file disabilitabili dalle opzioni |
| Token revocato dall'utente | reauth flow automatico (`ConfigEntryAuthFailed`) |
| XML malformato o campi nuovi | parser tollerante (valori mancanti → None), log di warning, test con fixture reali |
| Fuso orario HTT vs locale | conversione con `zoneinfo("Europe/Stockholm")`, test su date |
| Perdita di dati al riavvio | recorder HA sugli sensor; primo refresh alla partenza |

## 5. Risorse utili

- Portale CHPP: <https://chpp.hattrick.org>
- Wiki CHPP: <https://wiki.hattrick.org/wiki/CHPP_Manual> (e categoria CHPP XML Pages)
- Devblog Hattrick: <https://devblog.hattrick.org>
- Developer docs Home Assistant: <https://developers.home-assistant.io>
- Blueprint custom integration: <https://github.com/jpawlowski/ha-integration-blueprint>
- HACS: <https://hacs.xyz>
- Librerie CHPP di riferimento (per confrontare approcci): `pychpp` (PyPI),
  `github.com/lucianoq/hattrick` (Go), FoxTrick (browser extension)
