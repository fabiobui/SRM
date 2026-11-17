# Design: sezione Tecnici/mezzi per i Subappaltatori (AIDEV-187)

**Stato:** bozza in attesa di approvazione.
**Ticket:** AIDEV-187 — "Creazione tab tecnici/mezzi Subappaltatori".
**Fonte requisiti:** `Tab tecnici e mezzi.xlsx` (allegato al ticket, copia locale in Downloads).

## Intento e motivazione

Il Subappaltatore deve poter dichiarare i propri tecnici (con documentazione e
abilitazioni) e i propri mezzi/attrezzature, così che Fulgard tenga sotto
controllo le scadenze e la idoneità del personale e dei mezzi che opereranno.

## Obiettivi

- Due nuove sezioni, "Tecnici" e "Mezzi/dotazioni", visibili solo per i fornitori
  con `Vendor.is_subappaltatore` (stessa logica degli Attributi operativi).
- Il fornitore compila le sezioni nel portale; il back office le valida.
- Un admin può compilarle e modificarle dall'admin, come per gli Attributi operativi.
- Le scadenze di tecnici e mezzi entrano nei promemoria email giornalieri
  (`send_expiry_reminders`, AIDEV-18).

## Non obiettivi

- Nessuna modifica alla classificazione dei fornitori né al calcolo dello stato di qualifica.
- Nessuna integrazione con sistemi esterni (HR, anagrafiche del personale).
- Nessuna gestione dei turni o della disponibilità dei tecnici.

## Anti-obiettivi

- Mostrare dati interni o di sicurezza nella guida fornitori (vincolo di
  `tests/test_guide_operative.py`).
- Mostrare le sezioni a fornitori non Subappaltatori, anche via URL diretto.
- Perdere lo storico dei documenti di formazione all'aggiornamento.

## Vincoli

- Ogni email passa da `core/emails.py::send_templated_email`.
- Migrazioni generate e verificate con `makemigrations --check --dry-run`.
- Test pytest per ogni modifica; verifica Playwright in locale (Docker, `localhost:8000`).
- Documentazione e guide operative in italiano; guide aggiornate in
  `templates/guide/` (`admin_body.html`, `vendor_body.html`).

## Approcci considerati

1. **Modelli dedicati + flusso di validazione (scelto).** Nuovi modelli per
   tecnici e mezzi, con stato di validazione del back office. Riusa il pattern
   dei documenti e delle richieste di modifica del portale. Più lavoro, ma
   coerente con il requisito "il back office valida".
2. **Solo admin, nessuna validazione.** Più semplice, ma il fornitore non può
   aggiornare i dati. Scartato perché contrario alla scelta di avere il fornitore
   come compilatore principale.
3. **Riuso dei Documenti come tipi di documento.** Ogni tecnico/mezzo sarebbe
   un insieme di Document. Scartato: il modello Document non nasce per
   anagrafiche di persona/mezzo, e il catalogo dei documenti diventerebbe
   ingestibile.

## Design

### Modelli (app `vendors`, o nuova app `subcontractors` se preferite)

- **Tecnico** (`SubcontractorTechnician`): fornitore (FK), cognome, nome,
  mansione, badge, stato di validazione (`in attesa` / `validato` /
  `respinto`), note.
- **Documento del tecnico** (`TechnicianDocument`): tecnico (FK), tipo di
  documento (scelta fissa dalle righe dell'Excel: identità, patente, LUL, UNILAV,
  idoneità sanitaria, consegna DPI, attestati di formazione generale/specifica,
  preposti, DPI 3ª cat., PES/PAV, spazi confinati, PLE, primo soccorso,
  antincendio, altra documentazione), data di rilascio, data di scadenza
  (se prevista), file allegato, stato di validazione.
- **Mezzo/dotazione** (`SubcontractorEquipment`): fornitore (FK), tipo mezzo,
  targa o matricola/codice interno, strumento, stato di validazione, note.
- **Documento del mezzo** (`EquipmentDocument`): mezzo (FK), tipo di documento
  (libretto, contratto di leasing, assicurazione, certificato di taratura),
  data di scadenza, file allegato, stato di validazione.

### Storico (scelta mia, da confermare)

Ogni rinnovo di un attestato (formazione specifica, preposti, antincendio, ecc.)
crea un nuovo `TechnicianDocument` con le proprie date; i precedenti restano in
archivio. La scadenza che conta per il promemoria e per la visualizzazione è
quella del documento più recente validato per ciascun tipo.

### Visibilità

- Portale: le sezioni compaiono nella navigazione del fornitore solo se
  `is_subappaltatore` è vero. Le URL rispondono 404 agli altri fornitori.
- Admin: le sezioni sono inline sul fornitore, visibili solo se
  `is_subappaltatore` è vero, come per gli Attributi operativi. Chi ha ruolo admin
  può compilarle.

### Flusso di validazione

- Il fornitore inserisce o modifica una voce: stato `in attesa` finché il back
  office non valida. Nel frattempo la voce è visibile al back office, ma le
  scadenze restano nei promemoria solo quando la voce è `validata`.
- Il back office valida o respinge dall'admin (con nota per il respingimento).
- Le modifiche fatte da un admin sono validate direttamente, come per gli
  Attributi operativi.

### Promemoria

- Le date di scadenza di tecnici (documenti con scadenza) e mezzi (assicurazione,
  leasing, taratura) entrano in `send_expiry_reminders`, con le stesse soglie e lo
  stesso template dei documenti.
- Solo voci validate generano promemoria.

### Guide operative

- Aggiornare `admin_body.html`, `vendor_body.html` e le chip corrispondenti con le
  nuove sezioni e il flusso di validazione (regola del repo).

## Da verificare

- Quali documenti del tecnico e del mezzo richiedono davvero scadenza e obbligatorietà
  (la tabella dell'Excel è la fonte; eventuali dubbi vanno chiesti a Riccardo prima
  della implementazione).
- Formato del file allegato (PDF/immagine), con la stessa validazione dei documenti.

## Test previsti

- Visibilità: sezioni e URL accessibili solo ai Subappaltatori.
- Permessi: fornitore può creare/modificare le proprie voci; admin può tutto;
  altri fornitori no.
- Validazione: voci `in attesa` non generano promemoria; voci validate sì.
- Storico: il rinnovo crea un nuovo documento e la scadenza considerata è la più recente.
- Promemoria: scadenze di tecnici e mezzi incluse nel job.
- Guida fornitori: nessun dato interno (test `test_guide_operative.py`).
- Migrazioni: `makemigrations --check --dry-run`.
- Suite pytest completa e verifica Playwright in locale.

## Dimensione

Progetto: nuovi modelli, migrazioni, viste portale, inline admin, promemoria,
guide, test.
