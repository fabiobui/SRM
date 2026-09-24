
## Change Requests

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
