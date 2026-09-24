# Script di import e manutenzione dati

Raccolta di tutti gli script da riga di comando del progetto SRM: cosa fanno, che
file leggono, quali opzioni accettano e in che ordine vanno lanciati.

Tutti gli script configurano Django da soli (`django.setup()` con
`config.settings`): si lanciano come normali script Python, **non** servono
`manage.py` né `manage.py shell`. `import_geography.py` faceva eccezione, ma è **deprecato**: la geografia si semina con `python manage.py seed_geography` (vedi sotto).

---

## Prima di iniziare

### Ambiente

```bash
cd /percorso/SRM
.venv/bin/python vendor_management_system/import_vendors.py --dry-run
```

Dipendenze richieste dagli script Excel: `pandas`, `openpyxl>=3.1.5`, `termcolor`
(tutte in `requirements.txt`). Con `openpyxl` più vecchio di 3.1.5 pandas 3.x si
rifiuta di aprire gli `.xlsx`:

```
ImportError: Pandas requires version '3.1.5' or newer of 'openpyxl'
```

### Su quale database scrivono

Gli script scrivono sul DB configurato in `.env` (`DB_NAME`, `DB_HOST`, ...).
**Controlla sempre di puntare al database giusto prima di un'esecuzione reale**:
non c'è nessuna conferma interattiva, a parte in `data_migration_scripts/delete_vendors.py`.

### Dry run

Quasi tutti accettano `--dry-run`: eseguono l'intera elaborazione dentro una
transazione e poi fanno rollback, stampando esattamente quello che avrebbero
fatto. È il modo corretto di provare un file nuovo.

### Dove vengono cercati i file

Gli script di import risolvono un percorso relativo in quest'ordine:

1. percorso assoluto, se lo è
2. cartella corrente (da dove lanci il comando)
3. `vendor_management_system/`
4. root del progetto

I file `.xlsx` **non sono versionati**: vanno passati con `-f /percorso/file.xlsx`.
`sync_sets.py` fa eccezione: non legge file, copia i dati da un altro database.

### Ordine consigliato

Gli import di dettaglio agganciano il fornitore tramite il **Codice Embyon**
(`old_code`), quindi vanno dopo l'anagrafica; le tabelle di lookup vanno prima di
chi le referenzia.

```
import_geography.py  ──┐
import_titoli.py       ├─→ import_vendors.py ─→ import_competenze.py
import_documenttypes.py┘                        import_servizi.py
                                                import_documenti.py
                                                import_valutazioni.py
                                                import_embyon_codes.py
```

---

## Anagrafica fornitori

### `import_vendors.py`

Crea e aggiorna i fornitori (`Vendor`) con il relativo indirizzo (`Address`).

```bash
.venv/bin/python vendor_management_system/import_vendors.py -f Import.xlsx --dry-run
.venv/bin/python vendor_management_system/import_vendors.py -f Import.xlsx
```

| Opzione | Default | Significato |
|---|---|---|
| `-f`, `--file` | `Import.xlsx` | file `.xlsx` o `.csv` |
| `-s`, `--sheet` | `0` | indice o nome del foglio |
| `--dry-run` | off | esegue e annulla tutto |

**Chiave**: la colonna `old_code`. Lo script fa `update_or_create(old_code=...)`,
quindi le righe senza `old_code` vengono saltate e quelle già presenti vengono
**sovrascritte** — una colonna vuota nel file svuota il campo a database.

**Riga excel Albo Fornitore.** Ogni fornitore importato porta con sé il numero di
riga del foglio da cui arriva, nel campo `albo_excel_row` (etichetta *Riga excel
Albo Fornitore*, visibile nel tab "Informazioni Base" dell'Admin Fornitore). Serve
a ritrovare l'originale nell'Albo anche dopo che `old_code` è stato sostituito dal
codice Embyon. Il numero è quello vero del foglio Excel — intestazione riga 1,
primo fornitore riga 2 — oppure, se il file porta già una colonna `albo_excel_row`
o `riga`, il valore di quella colonna. Il campo richiede la migrazione
`vendors.0036`; senza, l'import si ferma con
`Unknown column 'vendors_vendor.albo_excel_row' in 'field list'`.

**Colonne attese** (nomi tecnici dei campi `Vendor`):

> La colonna `competences_zone` non viene più letta: il campo è stato
> rimosso. Le zone di competenza si assegnano dall'admin o
> dal portale fornitori; se il file la contiene viene semplicemente
> ignorata.

```
old_code, name, vat_number, email, phone, vendor_type,
vendor_management_update, qualification_type, is_ico_consultant, albo_zucchetti,
vendor_task_description, vendor_medical_service, mobile_device, ambulatory_service,
laboratory_service, laboratory_independent, year_of_establishment,
licensed_physician_year, other_medical_service, doctor_registration,
doctor_cv, doctor_cv2, contractual_status, contractual_start_date,
contractual_end_date, contractual_terms, reference_contact / reference_person,
vendor_final_evaluation, review_notes,
address.street_address, address.city, address.state_province,
address.region, address.country
```

Note sulle colonne:

- `reference_contact / reference_person` va scritta **esattamente così**, spazi compresi.
- `year_of_establishment` finisce in `date_of_establishment`.
- I booleani accettano `SI`, `YES`, `TRUE`, `1`, `X`, `Y`.
- I valori devono rispettare le *choices* del modello: `contractual_status` sono i
  codici `00`, `02`, `03`, `04`, `05`, `06`, `99`; `vendor_final_evaluation` è
  `DA VALUTARE` / `NEGATIVO` / `POSITIVO` / `MOLTO POSITIVO`.

**Attenzione**: l'import è in un'unica `transaction.atomic()` con `raise` sugli
errori — se una riga fallisce, viene annullato **tutto**.

---

## Codice Embyon

### `import_embyon_codes.py`

Cerca i fornitori nell'anagrafica Embyon e scrive il `CODCONTO` trovato nel campo
**Codice Embyon** (`old_code`), sostituendo il codice provvisorio assegnato
dall'import Excel (`XLS0001`, `XLS0002`, ...).

```bash
.venv/bin/python vendor_management_system/import_embyon_codes.py --dry-run
.venv/bin/python vendor_management_system/import_embyon_codes.py
```

| Opzione | Default | Significato |
|---|---|---|
| `-p`, `--prefix` | `XLS` | prefisso degli `old_code` da elaborare |
| `--dry-run` | off | esegue e annulla tutto |
| `--report` | `data_migration_scripts/reports/embyon_match_report.csv` | CSV con l'esito riga per riga (cartella non servita da Django, a differenza di `static/`) |
| `--prefer-ditta` | — | Società da preferire quando il fornitore esiste su più DITTA |
| `--max-omocodie` | `3` | oltre questo numero di codici distinti non sceglie da solo |
| `--fuzzy` | off | ripiego sulla ragione sociale per chi non aggancia su C.F./P.IVA |
| `--fuzzy-threshold` | `0.90` | similarità minima (0..1) del match fuzzy |
| `--fuzzy-province-required` | off | accetta il fuzzy solo con provincia nota e uguale sui due lati |
| `--set-active` | off | aggiorna anche il flag "Attivo su Embyon" |
| `--limit` | — | elabora solo i primi N fornitori (per prove) |

**Società Embyon.** Insieme al codice viene salvata la Società (`embyon_company`,
etichetta *Società Embyon*): lo stesso fornitore ha un `CODCONTO` diverso per
ogni Società, quindi il codice da solo non lo identifica. I valori ammessi sono
le `DITTA` presenti in `Embyon_Fornitori_T` — **CmaSrl, Evimed, GsProtec,
Sicura** — elencati in `Vendor.EMBYON_COMPANY_CHOICES`. Se Embyon introduce una
Società nuova lo script lo segnala in testa all'esecuzione: va aggiunta alle
choices del modello, altrimenti il form dell'Admin rifiuta il valore. Il campo
richiede la migrazione `vendors.0037`.

**Sorgente**: `redmine_test.Embyon_Fornitori_T` filtrata per `TIPOCONTO='F'`, la
stessa usata dal modal 🔍 del VendorAdmin; si cambia con
`settings.EMBYON_FORNITORI_TABLE`. La provincia non esiste in quella tabella e
viene recuperata in `LEFT JOIN` da `redmine_test.Account_Embyon_T`
(`settings.EMBYON_ACCOUNT_TABLE`), che però copre solo ~3% delle righe.

Il match è fatto in Python e non con una `JOIN` cross-schema perché `vms_db` e
`redmine_test` hanno collation diverse e il confronto SQL diretto fallisce con
`Illegal mix of collations`.

**Ordine dei criteri** — il fuzzy è un ripiego, non un criterio parallelo:

1. Codice Fiscale **e** Partita IVA
2. Codice Fiscale
3. Partita IVA
4. *solo se i precedenti non trovano nulla e c'è `--fuzzy`*: somiglianza della
   ragione sociale, con la provincia come vincolo quando è nota da entrambe le parti

**Scelta del codice**: se il fornitore esiste su più Società con `CODCONTO`
diversi (omocodie), viene preso quello con il **numero più alto dopo la F**, ma
solo fino a `--max-omocodie` codici distinti; oltre quella soglia il fornitore
resta `AMBIGUO` e va deciso a mano (è il caso dei gruppi con una P.IVA su decine
di sedi). `old_code` è UNIQUE: se il codice è già su un altro fornitore l'esito è
`COLLISIONE` e la riga viene saltata.

**Esiti nel report**: `AGGIORNATO`, `AGGIORNATO_AMBIGUO` (più codici, preso il
maggiore), `AGGIORNATO_FUZZY`, `AMBIGUO`, `COLLISIONE`, `NESSUN_MATCH`. Il CSV
contiene il codice precedente accanto al nuovo, quindi funziona anche da
tracciato per tornare indietro.

Lo script **non tocca** `albo_excel_row`: il campo resta il riferimento al file di
origine dopo la sostituzione di `old_code`, e viene riportato nella colonna
`riga_albo` del CSV e a video sulle righe rimaste da sistemare
(`AMBIGUO`, `COLLISIONE`, `NESSUN_MATCH`), così sono ricercabili nell'Albo.

**Sul fuzzy**: a soglia 0.90 sui nomi di persona corti produce falsi positivi
(`MARZI LUCA` → `MAGRI LUCA`, `LAV SERVICES` → `LDA SERVICE`). A soglia `1.0` i
match sono affidabili, perché il lavoro utile lo fa la normalizzazione del nome
(toglie `SRL`/`SPA`/`DOTT.`/punteggiatura) e non la tolleranza sulla distanza.
Verifica sempre le colonne `nome_embyon` e `similarita` del report.

---

## Competenze e servizi

### `import_competenze.py` / `import_servizi.py`

Assegnano ai fornitori i requisiti professionali (`VendorCompetence`) e i servizi
(`VendorService`) a partire da un file **a matrice**: un fornitore per riga, un
requisito/servizio per colonna, con una `X` nelle celle da assegnare.

```bash
.venv/bin/python vendor_management_system/import_competenze.py -f ImportCompetenzaAssegnate.xlsx --dry-run
.venv/bin/python vendor_management_system/import_servizi.py   -f import_servizi_assegnati.xlsx   --dry-run
```

| Opzione | Default | Significato |
|---|---|---|
| `-f`, `--file` | `import_competenze_assegnate.xlsx` / `import_servizi_assegnati.xlsx` | file `.xlsx` o `.csv` |
| `-s`, `--sheet` | `0` | indice o nome del foglio |
| `--dry-run` | off | esegue e annulla tutto |
| `--alias COL=CATALOGO` | — | *(solo competenze)* aggancia una colonna a un requisito a catalogo; ripetibile |
| `--create-missing` | off | *(solo competenze)* crea a catalogo i requisiti non riconosciuti |
| `--reset-except-company X` | — | *(solo competenze)* cancella le assegnazioni dei fornitori con Società Embyon diversa da X, prima dell'import |
| `--key` | `auto` | come agganciare il fornitore: `auto`, `albo_row`, `old_code` |

**Formato a doppia intestazione** — le prime due righe hanno ruoli diversi:

| | codice | QUAL-001 | COMP-001 |
|---|---|---|---|
| **riga 1** (descrizioni) | | Qualifica RSPP | Qualifica RSPP |
| **riga 2** (header vero) | codice | QUAL-001 | COMP-001 |
| riga 3 (dati) | XLS0004 | X | |

- La prima colonna si chiama **`codice`** e contiene il codice provvisorio
  dell'Albo (`XLS0001`, `XLS0002`, …).
- Celle valide per l'assegnazione: `SI`, `YES`, `TRUE`, `1`, `X`, `Y`.
- I fornitori non trovati vengono contati come "Vendor non trovati" e saltati.

**Come viene trovato il fornitore.** Il codice della prima colonna finisce in
`old_code`, che però `import_embyon_codes.py` **sostituisce** con il codice
Embyon (`XLS0001` → `F 7238`): da quel momento un aggancio per `old_code` non
troverebbe più nulla. Lo script usa quindi la *Riga excel Albo Fornitore*, che
non cambia mai, sfruttando il fatto che i codici XLS sono progressivi sulle righe
del file:

```
XLS0001 → riga 2      XLS0002 → riga 3      XLSnnnn → riga nnnn + 1
```

(verificato su tutti i 1135 fornitori dell'Albo, nessuna eccezione). Con `--key`:

| Valore | Comportamento |
|---|---|
| `auto` *(default)* | per i codici `XLS*` usa la riga Albo, altrimenti il Codice Embyon |
| `albo_row` | solo riga Albo |
| `old_code` | solo Codice Embyon (comportamento precedente) |

Se la prima colonna contiene un numero, viene interpretato direttamente come
riga. **La stessa logica e la stessa opzione `--key` valgono per
`import_servizi.py`, `import_documenti.py` e `import_valutazioni.py`.** In
esecuzione ogni script dichiara il criterio usato riga per riga:

```
➡️ 1. Vendor: 21 MANAGEMENT DI BARONCINI DAVIDE [XLS0001 → riga Albo 2]
```

**Il prefisso della colonna è il tipo, non il requisito.** Nel file lo stesso
requisito compare sotto più codici: `QUAL-001` e `COMP-001` sono entrambi
"Qualifica RSPP". Il prefisso dice con quale ruolo il requisito viene assegnato
al fornitore, e finisce nei flag di `VendorCompetence`:

| Prefisso | Flag |
|---|---|
| `QUAL-` | `is_qualifica` |
| `COMP-` | `is_competenza` |
| `ISCR-` | `is_iscrizione_albo` |

Su quei flag filtrano le dashboard e il portale fornitore: un'assegnazione senza
tipo esiste a database ma non compare da nessuna parte. Se lo stesso fornitore
arriva sia da `QUAL-001` sia da `COMP-001`, la riga resta **una sola** con
entrambi i flag.

**L'aggancio al catalogo avviene per nome**, con il codice come conferma. Serve
perché i codici del file sono storici (`QUAL-*`, `COMP-*`) mentre a catalogo i
requisiti hanno codici diversi (`REQ-*`, `MDL-*`, `ISCR-*`, `SOA`, `F-GAS`, …).
Un requisito non riconosciuto viene **segnalato e la colonna ignorata**: crearlo
al volo produrrebbe doppioni del catalogo (è quello che faceva la versione
precedente dello script). Quando la descrizione nel file non coincide con il nome
a catalogo si usa `--alias`:

```bash
--alias QUAL-003=REQ-003    # Qualifica Coord. Sicurezza Cantieri -> Coordinatore Sicurezza Cantieri (CSP-CSE)
--alias QUAL-004=REQ-004    # Consul. Merci Pericolose            -> Consul. ADR
```

Gli alias ricorrenti si possono fissare nel dizionario `ALIASES` in testa allo
script. In avvio lo script stampa quante colonne ha riconosciuto
(`Requisiti riconosciuti a catalogo: 19/19`): **controlla quel numero prima di
lanciare senza `--dry-run`.**

**Ricaricare le assegnazioni.** `--reset-except-company` cancella le assegnazioni
esistenti prima di importare, tenendo solo quelle dei fornitori di una Società:

```bash
.venv/bin/python vendor_management_system/import_competenze.py \
    -f ImportCompetenzaAssegnate.xlsx --reset-except-company Sicura --dry-run
```

I fornitori **senza** Società Embyon rientrano nella cancellazione. La
cancellazione sta nella stessa transazione dell'import, quindi con `--dry-run`
viene annullata insieme al resto.

`import_servizi.py` mantiene invece il comportamento originale: aggancia il
`ServiceType` per codice di colonna e lo **crea se manca**.

---

## Documenti e valutazioni

### `import_documenti.py`

Crea/aggiorna i documenti (`Document`) dei fornitori. Anche qui il formato è a
matrice: un fornitore per riga, un tipo documento per colonna.

```bash
.venv/bin/python vendor_management_system/import_documenti.py -f import_sa8000.xlsx --dry-run
```

| Opzione | Default | Significato |
|---|---|---|
| `-f`, `--file` | `import_sa8000.xlsx` | file `.xlsx` o `.csv` |
| `-s`, `--sheet` | `0` | indice o nome del foglio |
| `--dry-run` | off | esegue e annulla tutto |
| `--key` | `auto` | come agganciare il fornitore: `auto`, `albo_row`, `old_code` |

- Prima colonna: **`old_code`**, con lo stesso aggancio degli altri import — vedi
  [Come viene trovato il fornitore](#competenze-e-servizi): i codici `XLS*`
  passano per la Riga excel Albo, che sopravvive a `import_embyon_codes.py`.
- Le altre colonne devono chiamarsi come il **`code` di un `DocumentType`**
  esistente (confronto case-insensitive); i tipi sconosciuti vengono segnalati e
  saltati, **non** creati. Per questo `data_migration_scripts/import_documenttypes.py` va lanciato prima.
- Il contenuto della cella decide lo stato: una data (`2026-05-31`, `31/05/2026`,
  `31-05-2026`) diventa `expiry_date` con stato `APPROVED`; un booleano
  (`SI`/`X`/...) dà `APPROVED` senza scadenza; qualsiasi altro testo dà
  `SUBMITTED` e finisce nelle note. Le celle vuote vengono ignorate.

### `import_valutazioni.py`

Crea/aggiorna le valutazioni (`VendorEvaluation`), sempre a matrice.

```bash
.venv/bin/python vendor_management_system/import_valutazioni.py -f import_valutazioni.xlsx --dry-run
```

Stesse opzioni (`-f`, `-s`, `--dry-run`, `--key`; default `import_valutazioni.xlsx`).

- Prima colonna: **`old_code`**, agganciata come sopra (Riga excel Albo per i
  codici `XLS*`).
- Le altre colonne devono corrispondere al **`code` di un `EvaluationCriterion`**
  esistente (confrontato in maiuscolo); i criteri non trovati vengono saltati.
- La cella contiene il punteggio; le celle non numeriche vengono ignorate.

---

## Tabelle di base (lookup)

Vanno popolate **prima** degli import che le referenziano.

### `import_titoli.py`

Titoli di studio (`QualificationType`), referenziati da `Vendor.qualification_type`.

```bash
.venv/bin/python vendor_management_system/import_titoli.py -f titoli.xlsx --dry-run
```

Opzioni: `-f` (default `titoli.xlsx`), `-s`, `--dry-run`.
Colonne: `code` (chiave), `name`, `description`, `level`, `sort_order`,
`is_active`, `parent_code` (per la gerarchia).

### `data_migration_scripts/import_documenttypes.py`

Tipi documento (`DocumentType`), referenziati dalle colonne di `import_documenti.py`.

```bash
.venv/bin/python data_migration_scripts/import_documenttypes.py
```

Unico script **senza opzioni**: legge un percorso fisso,
`vendor_management_system/documenttype.csv`, CSV con separatore `;` e queste
colonne: `code`, `name`, `description`, `document_category`, `is_mandatory`,
`requires_renewal`, `default_validity_days`, `alert_days_before_expiry`,
`is_active`, `sort_order`, `updated_at`, `instructions`. Aggiorna per `code` se
esiste, altrimenti crea.

### `import_geography.py` — DEPRECATO

Nazioni, regioni e province. **Non usarlo più**: al suo posto c'è il management
command `seed_geography`, che legge le stesse informazioni dalle fixture
`vendors/fixtures/geography_italy.json` e `geography_countries.json`, è
idempotente, non sovrascrive `is_active`/`sort_order` personalizzati da admin, e
gira automaticamente ad ogni deploy da `compose/django/start`. La geografia è
inoltre seminata dalla data migration `vendors/0041_seed_geography`, perché è il
prerequisito delle zone di competenza dei fornitori e `migrate` viene
eseguito prima dei comandi di seed.

```bash
python manage.py seed_geography              # riallinea nomi e ordinamento
python manage.py seed_geography --create-only  # crea solo ciò che manca
```

Lo script originale resta nel repo come riferimento storico dei dati di
partenza.

---

## Allineamento fra database

### `sync_sets.py`

Copia i Set delle **Abilitazioni e Requisiti Professionali** (`vendors.CompetenceSet`) e dei
**Servizi Erogati** (`vendors.ServiceSet`), con le relative voci, da un database SRM a un
altro — tipicamente da quello di sviluppo, dove i set vengono preparati, a una
copia del database di produzione.

```bash
.venv/bin/python vendor_management_system/sync_sets.py --source vms_db --target vms_db_PROD --dry-run
.venv/bin/python vendor_management_system/sync_sets.py --source vms_db --target vms_db_PROD --copy-missing-refs
```

| Opzione | Default | Significato |
|---|---|---|
| `--source` | *obbligatoria* | database sorgente (es. `vms_db`) |
| `--target` | *obbligatoria* | database destinazione (es. `vms_db_PROD`) |
| `--dry-run` | off | esegue e annulla tutto |
| `--copy-missing-refs` | off | copia anche le competenze/servizi di anagrafica assenti sul destinazione |

I due database devono stare **sulla stessa istanza MySQL**: lo script lavora con
query cross-schema usando la connessione configurata in `.env`.

Lo script non tocca `vendors_vendor`: i campi del fornitore, `albo_excel_row`
compreso, non lo riguardano.

**Controlli automatici prima di scrivere.** Lo script confronta le tabelle
coinvolte (set, tabelle M2M, `vendors_category`, `vendors_competence`,
`vendors_servicetype`) fra i due database e si ferma se una manca o se le colonne
differiscono. Esempio di stop corretto:

```
❌ vms_db_PROD.vendors_competenceset: tabella assente — applica prima
   `DB_NAME=vms_db_PROD python manage.py migrate vendors`
Struttura non allineata: interrotto.
```

**Comportamento.** È idempotente: un set già presente sul destinazione (stesso
nome e stessa Classificazione) viene aggiornato, non duplicato, e le sue voci
vengono riallineate a quelle del sorgente. Le anagrafiche non vengono toccate: se
una voce punta a una competenza o a un servizio che sul destinazione non esiste,
la voce viene saltata e segnalata, a meno di `--copy-missing-refs`.

Il travaso funziona senza rimappature solo perché le anagrafiche condividono gli
stessi id fra i due database. Vale la pena verificarlo prima:

```sql
SELECT COUNT(*) FROM vms_db.vendors_category d
  JOIN vms_db_PROD.vendors_category p ON d.id = p.id;   -- deve dare 30 su 30
```

### Puntare uno script a un altro database

`config/settings.py` legge la configurazione dalle variabili d'ambiente e
`load_dotenv()` **non** sovrascrive quelle già impostate: basta anteporre
`DB_NAME` al comando.

```bash
DB_NAME=vms_db_PROD .venv/bin/python manage.py showmigrations vendors
DB_NAME=vms_db_PROD .venv/bin/python manage.py migrate vendors
```

Vale per qualunque script del progetto. Verifica sempre dove sei finito:

```bash
DB_NAME=vms_db_PROD .venv/bin/python -c "
import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup()
from django.db import connection; print(connection.settings_dict['NAME'])"
```

### Collation: `utf8mb4_unicode_ci` ovunque

**Regola di progetto: un database SRM e tutte le sue tabelle usano
`utf8mb4_unicode_ci`.** Dentro un singolo database la collation deve essere
uniforme, altrimenti qualsiasi JOIN fra due tabelle con collation diverse
fallisce:

```
(1267, "Illegal mix of collations (utf8mb4_0900_ai_ci,IMPLICIT) and
        (utf8mb4_unicode_ci,IMPLICIT) for operation '='")
```

Il caso tipico: un dump caricato in un database con default diverso da quello in
cui era stato prodotto. Le tabelle del dump conservano la loro collation e
convivono con quelle create dopo (dalle migrazioni), che ereditano il default del
database. L'esito è un database misto, e si manifesta in due modi:

- `migrate` fallisce creando una tabella con una FK verso una tabella di
  collation diversa: `(3780, "Referencing column ... are incompatible")`;
- oppure la migrazione passa e l'errore arriva a runtime, leggendo i dati:
  `(1267, "Illegal mix of collations")`.

**Come preparare un dump perché sia neutro.** Togli dal file le clausole di
charset e collation in coda a ogni `CREATE TABLE`, così le tabelle ereditano
quelle del database di destinazione:

```bash
cp dump.sql dump.sql.bak
sed -i '' 's/ DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;/;/g' dump.sql
```

```sql
-- prima
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
-- dopo
) ENGINE=InnoDB AUTO_INCREMENT=9;
```

Non basta togliere il solo `COLLATE=`: se resta `DEFAULT CHARSET=utf8mb4`, MySQL
applica la collation di default **del charset** (in MySQL 8 è
`utf8mb4_0900_ai_ci`), non quella del database. Va rimossa l'intera clausola.

**Ordine di ripristino:**

```bash
mysql -u root -p -e "CREATE DATABASE vms_db_PROD CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p vms_db_PROD < dump.sql     # tabelle tutte utf8mb4_unicode_ci
DB_NAME=vms_db_PROD .venv/bin/python manage.py migrate
```

**Verifica** — la seconda query deve restituire una riga sola:

```sql
SELECT SCHEMA_NAME, DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA
 WHERE SCHEMA_NAME IN ('vms_db','vms_db_PROD');

SELECT TABLE_COLLATION, COUNT(*) FROM information_schema.TABLES
 WHERE TABLE_SCHEMA = 'vms_db_PROD' GROUP BY TABLE_COLLATION;
```

**Fra database diversi** la collation può invece differire (`vms_db` di sviluppo
è ancora `utf8mb4_0900_ai_ci`): `sync_sets.py` forza i confronti cross-schema a
`utf8mb4_unicode_ci` — vedi `JOIN_COLLATE` — e in avvio segnala sia la differenza
fra i due DB sia, come avviso, un database internamente non uniforme.

**Se una migrazione è già fallita a metà**, le tabelle risultano create ma la
migrazione non è registrata in `django_migrations`: al rilancio Django ritenta e
si ferma con `(1050, "Table ... already exists")`. Se quelle tabelle sono **vuote**
vanno rimosse e si rilancia `migrate`; se contengono già dati, conviene
ricostruire il database dal dump neutro invece di rattopparle, perché restano
senza foreign key e con la collation sbagliata.

---

## Manutenzione

### `data_migration_scripts/delete_vendors.py`

Cancella fornitori e tutte le righe collegate (CASCADE su documenti, competenze,
servizi, valutazioni, contratti; SET_NULL dove previsto). Mostra l'anteprima e
chiede conferma.

```bash
python data_migration_scripts/delete_vendors.py --ids 1024                      # un fornitore
python data_migration_scripts/delete_vendors.py --ids 1024,1030,1055            # più id
python data_migration_scripts/delete_vendors.py --from 1000 --to 1050           # range inclusivo
python data_migration_scripts/delete_vendors.py --from 1000 --to 1050 --dry-run # solo anteprima
python data_migration_scripts/delete_vendors.py --field vendor_code --ids A1B2C3D4E5
```

| Opzione | Default | Significato |
|---|---|---|
| `--field` | `old_code` | campo di selezione: `old_code` o `vendor_code` |
| `--ids` | — | valori esatti separati da virgola |
| `--from` / `--to` | — | estremi del range, inclusi |
| `--dry-run` | off | mostra solo l'anteprima |
| `--yes` | off | non chiede conferma |

`old_code` è il Codice Embyon, l'unico numerato in modo ordinato; `vendor_code` è
casuale e utile solo per valori esatti.

### `migrate_existing_services.py`

Una tantum: migra i servizi dal vecchio `Vendor.service_type` (ForeignKey) alla
relazione `VendorService`. Nessuna opzione.

```bash
.venv/bin/python vendor_management_system/migrate_existing_services.py
```

### `data_migration_scripts/fix_documentset_migration.py`

Riallinea la migrazione `documents.0006_documentset` quando la tabella esiste già
a database ma la migrazione non risulta applicata (`migrate` fallisce con
*Table 'documents_documentset' already exists*). È idempotente e decide da solo
tra `--fake`, drop della tabella vuota o stop per intervento manuale.

```bash
python data_migration_scripts/fix_documentset_migration.py --dry-run   # solo diagnosi
python data_migration_scripts/fix_documentset_migration.py             # esegue
```

---

## Problemi frequenti

| Sintomo | Causa e rimedio |
|---|---|
| `ImportError: Pandas requires version '3.1.5' or newer of 'openpyxl'` | `pip install --upgrade "openpyxl>=3.1.5"` |
| `❌ File non trovato. Percorso fornito: Import.xlsx` | il file non è in nessuna delle cartelle cercate: passa `-f /percorso/assoluto` |
| `Vendor() got unexpected keyword arguments: 'xxx'` | lo script scrive un campo rimosso dal modello: confronta con `Vendor._meta.get_fields()` e togli la riga |
| `❌ Vendor non trovato: <codice>` | l'anagrafica non è stata importata, oppure stai usando `--key old_code` dopo che `import_embyon_codes.py` ha sostituito i codici: lascia `--key auto`, che aggancia per Riga excel Albo |
| `⚠️ Tipo documento XXX non trovato` | manca il `DocumentType`: lancia prima `data_migration_scripts/import_documenttypes.py` |
| `import_competenze` dice `non è a catalogo` e salta la colonna | la descrizione nel file non coincide con nessun nome a catalogo: aggancia con `--alias COL=CODICE_CATALOGO` |
| Le competenze importate non si vedono nelle dashboard | assegnazioni senza tipo (`is_competenza`/`is_qualifica`/`is_iscrizione_albo` tutti `False`): reimporta con la versione aggiornata dello script, che ricava il tipo dal prefisso della colonna |
| `Illegal mix of collations` | confronto SQL diretto fra `vms_db` e `redmine_test`: vanno confrontati in Python, come fa `import_embyon_codes.py` |
| L'import si annulla tutto per una riga sbagliata | è voluto: `import_vendors.py` usa una transazione unica. Correggi la riga e rilancia |
| `(3780, "Referencing column ... are incompatible")` durante `migrate` | database con collation non uniformi: vedi [Collation](#collation-utf8mb4_unicode_ci-ovunque) |
| `(1267, "Illegal mix of collations")` leggendo i dati | due tabelle dello stesso DB con collation diverse: vedi [Collation](#collation-utf8mb4_unicode_ci-ovunque) |
| `(1050, "Table '...' already exists")` al rilancio di `migrate` | una migrazione precedente è fallita a metà: rimuovi le tabelle residue (vuote) e rilancia |
| `Unknown column 'vendors_vendor.albo_excel_row'` | manca la migrazione del campo *Riga excel Albo Fornitore*: `python manage.py migrate vendors` |
| `Unknown column 'vendors_vendor.embyon_company'` | manca la migrazione del campo *Società Embyon*: `python manage.py migrate vendors` |
| Nel modal di ricerca la Società non finisce nel form | il campo `embyon_company` non è nel fieldset dell'Admin, oppure il valore trovato non è fra le `EMBYON_COMPANY_CHOICES` (il JS imposta una `<select>` solo se l'opzione esiste) |
| `Struttura non allineata: interrotto.` da `sync_sets.py` | al database destinazione mancano tabelle o colonne: applica le migrazioni con `DB_NAME=<target> manage.py migrate` |
