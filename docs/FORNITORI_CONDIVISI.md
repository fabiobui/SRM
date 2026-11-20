# Fornitori condivisi tra società

Un fornitore che lavora con più società del gruppo (CMASRL, EMMETEK, EVIMED, GSPROTEC, IGEAM, SICURA) è **un solo
record** `Vendor`, identificato dal **codice SAGE** (codice Terzo Sage, univoco tra le società). Il record è diviso in
**sezioni**: una sezione **Comune** e una sezione per ogni società con cui il fornitore lavora.

## Modello dati

- `Company` (`vendors/models.py`): le società del gruppo più la riga sentinella `COMUNE` (`is_common=True`). Seminata
  dalla migrazione `vendors/0057` e, in modo idempotente, da `post_migrate` (`ensure_companies`), così esiste anche nei
  DB di test creati senza migrazioni. `ldap_aliases` elenca i valori dell'attributo AD `company` da riconoscere.
- `VendorCompany` (`Vendor.company_sections`): la sezione di una società. Porta **qualifica, date, audit e Valutazione
  Finale della società** e il flag *attivo in Embyon* della società.
- `VendorCompanyAccount` (`VendorCompany.accounts`): i conti Embyon della società (`F 6546`, spazi collassati); un
  fornitore può averne più di uno nella stessa società. Unicità `(società, conto)`.
- `Vendor.sage_code` (unico, nullable). `old_code`, `embyon_company` ed `embyon_active` restano come campi storici:
  `embyon_active`, stato e Valutazione Finale del `Vendor` diventano l'**aggregato** delle sezioni (stato "migliore",
  valutazione "migliore", attivo se attivo in almeno una società) così dashboard, API e filtri esistenti restano
  coerenti.
- `company` (FK a `Company`, default `"COMUNE"`) su `Document`, `VendorCompetence`, `VendorService`, `Contract` e
  `VendorEvaluation`: la sezione dell'elemento. I vincoli di unicità sono `(fornitore, sezione, tipo)`: lo stesso
  documento può esistere in sezioni diverse. Si usa la riga sentinella invece di un FK nullable perché MySQL non
  applica vincoli condizionali e Django salta la validazione `unique` quando un valore è NULL.
- `scope` (`COMMON`/`COMPANY`) su `DocumentCatalog` e `Competence`: tipi comuni a tutte le società (DURC, visura,
  certificazioni, assicurazioni, ...) o specifici della società (contratto e allegati `ACQ-*`, privacy, DUVRI, POS,
  ...). Serve da default per la sezione dei caricamenti dal portale e per l'avviso di duplicato. Il seed iniziale è in
  `vendors/migrations/0058_popola_sezioni.py` (`COMMON_DOCUMENT_CODES`); tutti i requisiti esistenti sono comuni.
- `section_confirmed` su `Document`/`VendorCompetence`: falso per i caricamenti dal portale di un fornitore con più
  società, la cui sezione la assegna il back office in revisione.
- `User.company`: società dell'utente interno.

La migrazione `0058_popola_sezioni` crea una sezione per ogni fornitore con "Società Embyon" (copiandoci la qualifica
attuale e il codice Embyon come conto) e sposta i suoi elementi in quella sezione. I fornitori senza società (es. i
codici provvisori `XLS…`) restano con tutto in Comune e con la qualifica sul `Vendor` (percorso storico).

## Qualifica per società

La qualifica di una sezione considera i documenti/requisiti obbligatori della **Comune più quelli della società**
(`Vendor._mandatory_gaps(check, company=...)`). Le regole sono le stesse di prima (mai riapprovazione automatica,
Approvato -> Da revisionare se un obbligatorio non è più in regola, upload completo -> Da revisionare), applicate a ogni
sezione: `Vendor.sync_qualification_status()` e `submit_for_review_if_complete()` delegano alle sezioni quando ci sono,
quindi signal, portale e job notturno (`qualification_sync.sync_all`, 6:30) non cambiano chiamante.

## Permessi

Regole in `vendors/sections.py`:

| Utente | Comune | Sezione della propria società | Sezioni di altre società |
|---|---|---|---|
| Superuser | modifica | modifica | modifica |
| Admin con società | modifica | modifica | sola lettura |
| Admin senza società | modifica | – | sola lettura |
| BO User (revisione portale) | rivede | rivede | non vede |

La società dell'utente arriva a ogni login dall'attributo AD `company` (`core/simple_ldap_backend.py`,
`Company.objects.match_ldap`: codice, nome o alias, anche come prefisso, es. "Sicura S.p.A."). Un valore non
riconosciuto lascia quella impostata a mano in admin e scrive un warning nel log.

## Interfaccia

- **Admin**: il click sul fornitore apre `/admin/vendors/vendor/<id>/sezioni/` (scelta della sezione); la scheda si apre
  sempre con `?sezione=CODICE` (una GET senza parametro torna alla scelta). Gli inline mostrano solo gli elementi della
  sezione e ci assegnano quelli nuovi; una sezione non modificabile è tutta in sola lettura. Endpoint
  `<id>/duplicati-sezione/` + `static/admin/js/section_duplicate_warning.js`: modale di avviso quando si sceglie un tipo
  già presente in un'altra sezione (non blocca).
- **Lente** (`embyon_search.js`, `fabric_hub.search_shared_suppliers`): cerca nelle viste per ragione sociale, codice
  Embyon, codice SAGE, P.IVA o C.F. Un fornitore già censito (per SAGE o per conto) non viene duplicato: `link-sage/`
  collega il codice e aggiunge solo la sezione della società. Un fornitore nuovo nasce con Comune + sezione della
  società scelta (per chi ha una società è sempre la sua).
- **Subappaltatori**: le tab Attributi operativi, Tecnici e Mezzi/dotazioni compaiono solo se il fornitore
  ha la classificazione Subappaltatore e solo nella sezione **Sicura** (`sections.SUBCONTRACTOR_SECTION`; nella
  Comune per i fornitori senza sezioni società). Le modifica chi può modificare quella sezione; il back office
  valida tecnici, mezzi e documenti dalla pagina *Tecnici e mezzi* (`/portale/backoffice/tecnici-mezzi/`).
- **Codice SAGE in Comune**: la sezione Comune mostra solo il codice SAGE (con la lente accanto); i conti Embyon
  sono nella tab Qualifica e Audit di ogni società.
- **Dashboard**: badge di Valutazione Finale per società, filtro *Società*, ricerca anche per SAGE e conti; la scheda in
  sola lettura chiede prima la sezione (`?sezione=`).
- **Portale fornitore**: vista unica con l'etichetta della società (o Comune) su ogni elemento e lo stato di qualifica
  per società. Il back office assegna/corregge la sezione in revisione.
- **API**: `sections` (sola lettura) in `VendorSerializer`/`VendorQualificationSerializer`; il `PATCH` di
  `/qualification/` su un fornitore con sezioni richiede `company`.

## Viste FABRIC_HUB e comandi

Entità DAB `v_suppliers` e `v_supplier_companies` (configurabili con `FABRICHUB_SHARED_SUPPLIERS_ENTITY` e
`FABRICHUB_SUPPLIER_COMPANIES_ENTITY`). Le viste servono solo a collegare i fornitori **già censiti**: nessun fornitore
viene importato in automatico.

- `python manage.py sync_fabric_suppliers [--dry-run]` (anche job Celery alle 6:00): assegna il codice SAGE ai
  fornitori agganciati univocamente dai loro conti, aggiorna stato e flag dei conti, aggiunge gli altri conti della
  stessa società e ricalcola *attivo in Embyon* delle sezioni. Non crea fornitori né sezioni; segnala i candidati
  all'accorpamento.
- `python manage.py merge_shared_suppliers [--apply] [--sage-code X] [--survivor-map file.csv]`: accorpa per codice
  SAGE i fornitori censiti per società diverse. Senza `--apply` è una simulazione. Il superstite è il record con la
  modifica più recente (storico admin, richieste dal portale, aggiornamenti di documenti/requisiti/servizi/contratti);
  i campi vuoti si completano dagli altri record senza sovrascrivere nulla; ogni elemento resta nella sezione della
  società d'origine; utenti portale, richieste, tecnici/mezzi, promemoria, ordini passano al superstite. I gruppi con
  due record della stessa società vengono saltati. Backup JSON dei record accorpati in
  `data_migration_scripts/reports/merge_backup/`.
- Report (fuori da git, contengono dati fornitore) in `data_migration_scripts/reports/`: `merge_report.csv`,
  `merge_skipped.csv` e `embyon_codes_not_in_views.csv` (fornitori con codice Embyon non agganciati alle viste, con il
  motivo: `non_trovato`, `societa_diversa`, `senza_societa`, `placeholder_xls`, `senza_codice`, `link_conflict`,
  `sage_ambiguo`).

## Ordine di esecuzione su una VM

1. Deploy e `migrate` (lo fa lo start del container/servizio).
2. `python manage.py sync_fabric_suppliers --dry-run`, poi senza `--dry-run`.
3. `python manage.py merge_shared_suppliers`, controllo dei CSV, poi `--apply`.
4. `python manage.py sync_qualification_status`.
5. Verificare che gli utenti interni abbiano la società (login LDAP o scheda utente) e, se serve, completare gli alias
   LDAP delle società.
