# Privacy policy — Hattrick for Home Assistant

*Ultimo aggiornamento: 2026-11-14. This application uses information from the online game
service Hattrick.org.*

## Chi siamo

"Hattrick for Home Assistant" è un'integrazione custom open source (Apache 2.0) per
Home Assistant, sviluppata da Stefano Cattonar. Non è affiliata a Hattrick.org né da
Extralives. Repository: <https://github.com/CesarStef/ha-hattrick-integration>.

## Quali dati trattiamo

L'integrazione gira **solo dentro la tua istanza Home Assistant** e tratta esclusivamente:

- le **credenziali OAuth 1.0a** della tua app CHPP (consumer key/secret e access
  token/secret), salvate nella config entry di Home Assistant (cifrate at rest da HA);
- i **dati della tua squadra** scaricati via CHPP (`chppxml.ashx`): economy, rosa,
  partite, classifica, allenamento, stadio, ecc.

## Cosa NON facciamo

- Non chiediamo, salviamo o logghiamo **mai** username, password o codice di sicurezza
  Hattrick.
- Non salviamo né logghiamo **mai** token o secret (la diagnostica di HA li redacta
  automaticamente — test automatico in `tests/test_diagnostics.py`).
- Non accediamo a dati di **altre squadre**.
- Non facciamo **scraping** del sito Hattrick: solo i file XML ufficiali CHPP.
- Non inviamo dati a **terzi**: nessuna telemetria, nessun server esterno, nessun
  tracciamento. Tutto resta sul tuo dispositivo.
- Non vendiamo dati né facciamo profiling.

## Base legale e conservazione

Il trattamento avviene sul tuo dispositivo per permetterti di usare il servizio
(esecuzione del contratto / interesse legittimo). I dati restano nella tua istanza HA
finché non rimuovi l'integrazione; la rimozione della config entry cancella le
credenziali.

## Contatti

Per domande su questa policy: apri una issue su
<https://github.com/CesarStef/ha-hattrick-integration/issues>.
