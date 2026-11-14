# Release notes — v1.0.0

Prima release pubblica stabile di **Hattrick for Home Assistant**.
Testo pronto da incollare nella GitHub Release del tag `v1.0.0`
(il connettore GitHub disponibile non può creare release: crearla dall'interfaccia
web con "Draft a new release" → tag `v1.0.0` → incolla queste note).

---

## Hattrick for Home Assistant v1.0.0

Integrazione custom per Home Assistant che porta la tua squadra Hattrick in HA tramite
le API ufficiali CHPP (OAuth 1.0a). Open source, licenza Apache 2.0.

### Funzionalità

- **23 sensor** nel dispositivo "squadra": nome, morale, fiducia tifosi, cassa, rosa
  (giocatori, TSI, infortunati, squalificati, forma), fan club, settore giovanile, staff,
  posizione in classifica, prossima/ultima partita, partite programmate, entrate e
  stipendi, allenatore, allenamento, progresso allenamento, stadio, orario server HT,
  diagnostici ultima partita (rating e tattica).
- **4 servizi**: `hattrick.get_match_details` e `hattrick.get_player` (con risposta,
  usabili in automazioni con `response_variable`), `hattrick.set_match_orders` (invio
  ordini di partita via `matchorders.xml`, richiede permesso di scrittura sull'app
  CHPP), `hattrick.refresh`.
- **Config flow OAuth 1.0a** automatico (authorize URL + verifier) o manuale, con reauth
  e repair automatico in caso di token revocato.
- **Opzioni**: intervallo di polling 5–60 min, file CHPP abilitabili singolarmente,
  modalità matchday (polling 5 min dentro ±3h dalla partita).
- **Diagnostics redatta**: il dump di diagnostica non contiene mai token o secret.
- Interfaccia in italiano e inglese; esempi di dashboard e automazioni in `examples/`,
  mock visivi in `examples/mockups/`.

### Requisiti

- Home Assistant 2025.1+ (testata su 2026.11.1 con il Marketplace integrato).
- Un'app CHPP personale su chpp.hattrick.org. **Attenzione**: finché l'app non è
  certificata da Hattrick, solo il proprietario dell'app può autorizzarla
  ("only the app owner can authorize the app").

### Qualità

- 90 test automatici verdi, coverage 97% su `custom_components/hattrick`.
- CI GitHub Actions: hassfest + validazione HACS.
- Conforme al CHPP Manual: solo file XML `chppxml.ashx`, niente scraping, User-Agent
  con nome e versione, mai log di token/secret, solo dati della propria squadra.

### Nota

Questo progetto è vibe-codato (generato con un agente AI, vedi disclaimer nel README).

---

*This application uses information from the online game service Hattrick.org.*
