
## Change Requests

### 5/10/26 — Automatismi sullo stato di qualifica (AIDEV-22)

- **Creazione**: un fornitore nuovo parte sempre *In attesa*, anche se da admin
  o API viene indicato un altro stato.
- **Upload dal portale**: se il fornitore è *In attesa* o *Respinto* e, caricando
  un documento/requisito obbligatorio, ha consegnato tutti gli obbligatori
  mancanti o scaduti, passa a *Da Revisionare*. I caricamenti facoltativi non
  cambiano lo stato.
- **Ricarico anticipato**: se un documento/requisito già approvato e ancora
  valido viene ricaricato, la nuova versione resta *in attesa di revisione*
  (una sola per record) e quella approvata, con la sua scadenza, resta in vigore:
  lo stato del fornitore non cambia. L'ufficio la approva o la rifiuta dalle
  code di revisione del back-office; se approvata, file e date dell'anagrafica
  vengono sostituiti. Vale anche per i facoltativi. Nuovi campi `pending_*` su
  documenti e requisiti (migrazioni `documents/0013` e `vendors/0050`).
- **Requisiti respinti**: ora distinti da quelli non ancora verificati (nuovo
  campo `rejected`, migrazione `vendors/0051`, esistenti non respinti). Il
  fornitore li vede "Respinto - da ricaricare", escono dalla coda di default del
  back-office e dai KPI "da revisionare", e non contano come consegnati.
- **Home del portale fornitore**: due avvisi separati, uno per i documenti e uno
  per i requisiti (da caricare, respinti da ricaricare, scaduti, in scadenza),
  ciascuno col proprio link; diventano rossi se c'è qualcosa di respinto. I
  riquadri KPI hanno una colonna "Respinti" per documenti e requisiti.
- La regola di AIDEV-100 per approvare il fornitore resta invariata: obbligatori
  caricati, approvati dall'ufficio e non scaduti. L'approvazione/rifiuto manuale
  del fornitore da parte dell'ufficio non cambia.

### 29/9/26 — Documenti e requisiti obbligatori e stato di qualifica (AIDEV-100)

L'obbligatorietà di documenti contrattuali e abilitazioni/requisiti professionali
si imposta a catalogo (nessun nuovo campo): **`DocumentCatalog.is_required`**,
ora etichettato "È obbligatorio", e **`Competence.is_mandatory`**.

- **Stato di qualifica**: un fornitore può risultare *Approvato* solo se tutti i
  documenti e requisiti **obbligatori** a lui assegnati sono caricati (file
  presente), verificati/approvati dal gestore e non scaduti. Altrimenti lo stato
  passa a *Da Revisionare*. I record facoltativi non bloccano. Il sistema non
  riapprova mai da solo.
- **Quando scatta il controllo**: al salvataggio del fornitore, a ogni modifica o
  cancellazione di un suo documento/requisito e a ogni salvataggio del catalogo
  (se un tipo diventa obbligatorio, i fornitori coinvolti vengono riesaminati).
  "Qualificato" (`is_qualified`) tiene conto anche della scadenza nel tempo.
- **Azione admin "Approva fornitori selezionati"**: approva solo i fornitori in
  regola e segnala cosa manca agli altri.
- **Revisione da admin**: approvare/respingere un documento o spuntare
  "Verificata" su un requisito compila in automatico revisore e data, come già
  fa il portale back-office. Lo "Stato validità" dei documenti è calcolato da
  stato e scadenza, quindi non richiede aggiornamenti manuali.
- **UI**: scrollbar verticale (intestazione fissa) nelle tabelle Servizi
  Erogati, Abilitazioni e Requisiti Assegnati e Registro Documenti Contrattuali
  del fornitore, e nelle liste admin di `documents/`, `services/` e
  `competences/`.
- ⚠️ **Dopo il deploy** lanciare `python manage.py sync_qualification_status
  --dry-run` e poi senza `--dry-run`: i fornitori oggi *Approvati* ma non in
  regola passano a *Da Revisionare* (in locale erano 30 su 49).

### 24/9/26 — Zone di competenza territoriali

Le "zone di competenza" del fornitore non sono più un catalogo di zone nominate
da pre-creare a mano (`CompetenceZone` + regole INCLUDE/EXCLUDE): il fornitore
si collega direttamente ai territori.

- **Admin** (`admin/vendors`): nel tab Informazioni Base un selettore ad albero
  Nazione → Regione → Provincia, con stato tri-stato derivato sulle regioni,
  comandi *Seleziona tutto* / *Deseleziona tutto* per ogni livello e ricerca.
  In cima alla lista, tre filtri a cascata Nazione → Regione → Provincia.
- **Portale fornitori** (`portale/anagrafica/`): il fornitore propone le proprie
  zone con lo stesso selettore; la modifica passa dall'approvazione del back
  office come ogni altro campo anagrafico.
- **Dashboard** (`vendors/dashboard/`): i grafici contano ora le zone di
  competenza e non più la sede. *"Fornitori per Regione"* è stato rinominato
  **"Regioni"**; le province sono finalmente aggregate lato server. Un fornitore
  attivo in più regioni è conteggiato in ognuna, quindi la somma delle barre
  supera il numero di fornitori (indicato in pagina).
- **Export Excel**: due colonne nuove (Zone di Competenza, Province Competenza).
  ⚠️ I parametri `regions`/`provinces` (nomi, sede) sono sostituiti da
  `comp_regions`/`comp_provinces`/`comp_countries` (codici, competenza): vecchi
  bookmark dell'export smettono di filtrare.
- **Geografia**: il catalogo Nazioni/Regioni/Province è ora seminato
  automaticamente ad ogni deploy (`seed_geography`); `import_geography.py` è
  deprecato.
- **Rimossi**: `CompetenceZone`, `CompetenceZoneRule`, `Vendor.competence_zones`,
  `Vendor.competences_zone` e i relativi admin, endpoint DRF e serializer. I
  serializer Vendor espongono ora `competence_provinces`/`competence_countries`
  per codice.

⚠️ **Prima del deploy** leggere la sezione dedicata in
[DEPLOY.md](DEPLOY.md): la migrazione `0044` cancella in modo irreversibile i
dati legacy, e va preceduta dal report di travaso.

### 19/5/26

Ecco l'elenco delle modifiche richieste.

#### Scheda Fornitore (VendorAdmin)

**TAB Informazioni di base**

- Label `Vecchio codice fornitore` -> `Codice Embyon`
- Aggiungere un campo `Utente gestione fornitore`che è una lookup sugli users che fanno parte dei gruppi 'BO User' o 'Admin'

**TAB Stato Contrattuale**

-> Rimuovere

**TAB Contratti**

Aggiungere in ogni `Contract`:
- il campo `Tipo contratto`con queste opzioni: 1) Accordo quadro, 2) Ordine, 3) Ordine ricorrente, 4) Fornitura occasionale
- il campo `Persona di riferimento`

Cambiare la label `Note`in `Note/Ulterioni condizioni contrattuali`

**TAB Gestione/Altro**

- Rinominare il TAB in Zone
- Togliere il campo `Descrizione Attività Fornitore`
- Togliere il campo `Gestione aggiornamenti`

#### Lista Fornitori

Nella lista/vista dei fornitori queste modifiche:
- Al posto di `Codice fornitore`-> `Codice Embyon`(ex Vecchio codice fornitore)
- Al posto di `Stato di qualifica` -> `Valutazione finale`
- Rimuovere i campi `Livello di affidabilità`e `Qualificato`

#### Varie

Nella lista degli 'Stati di qualifica' aggiungere 'Da Revisionare'

#### PORTALE FORNITORI

Togliamo il menù 'Stato Qualifica' e mettiamo nella 'Home' **solo** lo 'stato qualifica' come era nel menù 'Stato qualifica ': ![[Pasted image 20260519155016.png]]
