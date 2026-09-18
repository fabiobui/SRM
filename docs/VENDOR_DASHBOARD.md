# Dashboard di Analisi Fornitori (`/vendors/dashboard/`)

> Riferimento consolidato per la funzionalità della dashboard di analisi fornitori (grafici, filtro lato client,
> export Excel). Sostituisce 9 file di note di sessione sovrapposti che si trovavano precedentemente sotto
> `vendor_management_system/vendors/`
> (`DASHBOARD_IMPLEMENTATION_SUMMARY.md`, `README_DASHBOARD.md`, `README_FILTRI_AVANZATI.md`,
> `ESEMPI_FILTRI_AVANZATI.md`, `IMPLEMENTAZIONE_FILTRI_COMPLETA.md`, `VISUAL_GUIDE_FILTRI.md`,
> `TESTING_GUIDE_FILTRI.md`, `START_HERE.md`, `README_VIEWS.md`) più il file `INSTALLATION_INSTRUCTIONS.md`
> presente nella root. Questo file è stato scritto leggendo quei documenti **e** l'implementazione attuale
> (`dashboard_views.py`, `urls.py`, `dashboard.js`, `vendor_dashboard.html`, `test_dashboard.py`) alla data del
> branch `feature/AIDEV-14-portale-fornitori`, 2026-09-15 — dove erano in disaccordo, prevale il codice. La
> configurazione locale generale (venv, `pip install`, `migrate`, `createsuperuser`) **non** è ripetuta qui —
> vedi `docs/PROJECT_OVERVIEW_AND_LOCAL_SETUP.md`.

## 1. Cos'è e dove si trova

La dashboard è una vista interna di analisi/consultazione sul registro `Vendor`: statistiche riassuntive, un
insieme di grafici cliccabili, un generatore di filtri avanzati in stile Redmine, una casella di ricerca a testo
libero e un export Excel filtrato. È raggiungibile da qualsiasi sessione autenticata (pensata per BO/Admin, ma
viene applicato solo `@login_required` — nessun controllo di ruolo).

| Piece | Location |
|---|---|
| URL | `/vendors/dashboard/` (nome `vendors:vendor-dashboard`) |
| App | `vendor_management_system/vendors/` |
| Views | `vendor_management_system/vendors/dashboard_views.py` (tenuto separato dal `views.py` DRF — vedi §7) |
| URLs | `vendor_management_system/vendors/urls.py` |
| Template | `vendor_management_system/vendors/templates/vendors/vendor_dashboard.html` |
| CSS | `vendor_management_system/vendors/static/vendors/css/dashboard.css` |
| JS | `vendor_management_system/vendors/static/vendors/js/dashboard.js` (~2200 righe) |
| Tests | `vendor_management_system/vendors/tests/test_dashboard.py` |
| Librerie frontend (CDN) | Bootstrap 5.3.0, Font Awesome 6.0.0, Chart.js 4.4.0 |
| Dipendenza Excel | `openpyxl==3.1.2` — già fissata nel `requirements.txt` di root, non serve alcun passaggio di installazione aggiuntivo |

## 2. Come funziona realmente la pagina (leggi questo prima di modificare filtri/grafici)

`vendor_dashboard_view` (la view di `GET /vendors/dashboard/`) esegue **tutto** il lavoro sui dati lato server in
un'unica richiesta: interroga `Vendor` con `select_related`/`prefetch_related`/`Prefetch`, costruisce le
aggregazioni per i grafici, serializza l'*intera* lista fornitori in JSON e incorpora entrambi i blob
direttamente nell'HTML renderizzato come `chart_data_json` e `vendors_data_json`
(`json.dumps(..., cls=DjangoJSONEncoder)`).

Tutto ciò che avviene dopo — il rendering dei grafici, il filtro tramite click sui grafici, il generatore di
filtri avanzati, la casella di ricerca, le stat card "Selezionati"/"Positivi" e la tabella fornitori a pagina —
viene eseguito **interamente lato client** in `dashboard.js` contro l'array `allVendors` incorporato. Non c'è
alcun round-trip AJAX mentre si interagisce con la dashboard. Esistono due endpoint di tipo REST
(`dashboard-stats/`, `dashboard-vendors/`) ma **l'attuale UI della dashboard non chiama nessuno dei due** — vedi
§6. Solo il pulsante di export Excel effettua una vera richiesta al server (una navigazione a pagina intera verso
`/vendors/export-excel/?...`, non una fetch/AJAX).

Implicazione pratica: questo rende l'interazione con la dashboard ragionevolmente veloce, ma significa che
l'intera tabella fornitori viene scaricata a ogni caricamento della pagina — utile saperlo prima di escludere che
un "caricamento iniziale lento" sia legato alla dimensione del dataset (vedi §9).

## 3. Stat card e grafici

Quattro card nella parte superiore della pagina (`vendor_dashboard_view` le calcola una volta; tre delle quattro
vengono poi ricalcolate in tempo reale lato client al variare dei filtri):

| Card | Field | Behavior |
|---|---|---|
| Fornitori Totali | `total_vendors` | Conteggio statico di tutti i fornitori; il click chiama `clearAllFilters()` |
| Attivi | `active_vendors` | Fornitori con `is_active=True` |
| Selezionati | `total_vendors` inizialmente, poi in tempo reale | Conteggio dei fornitori che attualmente corrispondono a tutti i filtri attivi |
| Positivi | `positive_vendors` | Fornitori (all'interno dell'insieme filtrato corrente) con `vendor_final_evaluation` pari a `Positivo`/`Molto Positivo` |

Nove grafici cliccabili (canvas `chart-clickable`), ciascuno costruito a partire da `chart_data_json` e ciascuno
che, al click, attiva/disattiva una voce nell'oggetto `activeFilters` descritto in §4:

| Chart (canvas id) | Dimension | `activeFilters` key |
|---|---|---|
| `vendorTypeChart` | `vendor_type` | `vendor_types` (array) |
| `serviceTypeChart` (etichettato "Consulenti ICO") | `is_ico_consultant` | `ico_consultant` (tri-stato: `null`/`true`/`false`) |
| `regionChart` | `address.region` | `regions` (array) |
| `provinceChart` | `address.state_province` (solo all'interno delle regioni selezionate) | `provinces` (array) |
| `qualificheChart` | `Competence` dove `VendorCompetence.is_qualifica=True` | `qualifiche` (array) |
| `competenzeChart` | `Competence` dove `VendorCompetence.is_competenza=True` | `competenze_req` (array) |
| `serviceCategoriesChart` | `ServiceType` di primo livello (`parent__isnull=True`) | `service_categories` (array) |
| `servicesChart` | `ServiceType` foglia (`parent` impostato) | `services` (array) |
| `certificationsChart` | `Competence` dove `VendorCompetence.has_certification=True` | `certifications` (array) |

Nel template attuale **non** esiste alcun grafico per categoria / stato qualifica / livello di rischio / paese,
nonostante questo fosse l'insieme di dimensioni descritto nei vecchi documenti sostituiti da questo file — quella
descrizione riguarda una versione precedente della dashboard. Le distribuzioni di valutazione qualità e tasso di
adempimento vengono calcolate lato server in `chart_data['by_quality']` / `chart_data['by_fulfillment']`
(suddivise in bucket 0-1/1-2/.../4-5 e 0-20%/.../80-100%) ma attualmente non vengono renderizzate come grafici nel
template — l'aggregazione esiste già in `dashboard_views.py` nel caso si voglia collegarci un grafico.

Tutte le voci di `activeFilters` con valore array sono a selezione multipla (OR all'interno della stessa
dimensione, ad es. cliccando due regioni si mostrano i fornitori dell'una o dell'altra) e tutte le dimensioni si
combinano in **AND** (un filtro per regione + un filtro per tipo fornitore restringe il risultato a entrambi).

## 4. Casella di ricerca

Il campo di testo (`#search-input`) esegue una corrispondenza per sottostringa case-insensitive su un insieme
fisso di campi concatenati: `vendor_code`, `name`, `email`, `vendor_type`, `service_type.parent`, `category.name`
(o `category` se non annidato), `address.region`, `address.city`, `address.state_province`, `vat_number`,
`fiscal_code`, e la lista concatenata delle `competences`. Si combina in AND con i filtri da click sui grafici e
con i filtri avanzati.

## 5. Filtri avanzati (generatore di filtri in stile Redmine)

Il pannello "Filtri Avanzati" permette di costruire righe arbitrarie `campo / operatore / valore`, tutte
combinate in **AND** (non c'è OR tra le righe, né OR all'interno di un singolo campo — ad es. non è possibile
esprimere "regione = Lazio OR regione = Lombardia" con una sola riga; aggiungere due dashboard separate oppure
ottenere lo stesso risultato con una selezione multipla da click sui grafici su `regions`, dato che quella
dimensione *è* combinata in OR).

### 5.1 Campi disponibili

Questo è l'elenco autorevole dei campi tratto da `filterFields` in `dashboard.js` (verificato rispetto al file
attuale — alcuni dei documenti sostituiti elencavano un numero/set di campi leggermente diverso; questa tabella è
aggiornata):

| Field (internal key) | Label | Type | Notes / options |
|---|---|---|---|
| `name` | Nome | text | |
| `vendor_code` | Codice Fornitore | text | |
| `vendor_type` | Tipo Fornitore | select | Società, Professionista, Dipendente, Dipendente + Libero professionista, Disoccupato, Libero Professionista, Presso Studio, Prestazione Occasionale, Società/professionista, Internazionale |
| `email` | Email | text | |
| `phone` | Telefono | text | |
| `vat_number` | Partita IVA | text | |
| `fiscal_code` | Codice Fiscale | text | |
| `qualification_status` | Stato Qualifica | select | PENDING, APPROVED, REJECTED |
| `vendor_final_evaluation` | Valutazione Finale | select | DA VALUTARE, NEGATIVO, POSITIVO, MOLTO POSITIVO |
| `quality_rating_avg` | Valutazione Qualità | number | 0–5 |
| `fulfillment_rate` | Tasso Adempimento | number | 0–100 (percentuale) |
| `is_active` | Attivo | boolean | |
| `is_ico_consultant` | Consulente ICO | boolean | |
| `contractual_status` | Stato Contrattuale | select | `00` Da verificare, `02` Fare RAI, `03` RAI Effettuata, `04` Contrattualizzato, `05` Da contrattualizzare ad esigenza, `06` Contratto Scaduto, `99` Non Usare |
| `address.city` | Città | text | annidato — i fornitori senza indirizzo non corrispondono mai |
| `address.region` | Regione | text | annidato |
| `address.state_province` | Provincia | text | annidato |
| `address.country` | Paese | text | annidato |
| `category.name` | Categoria | text | annidato |
| `service_type.name` | Tipo Servizio | text | annidato — corrisponde solo al servizio *primario* del fornitore |

Da notare che il modello ha anche un campo `risk_level` (LOW/MEDIUM/HIGH) e `Vendor.contact_details`/`website`/
ecc., ma `risk_level` **non** è esposto come campo filtro né come dimensione dei grafici nella dashboard attuale
— nonostante fosse prominente nei vecchi documenti (faceva parte di un'iterazione precedente). Se oggi serve
filtrare per livello di rischio, bisogna usare il Django Admin oppure reintrodurlo in `filterFields`/`chart_data`.

### 5.2 Operatori per tipo di campo

| Type | Operators |
|---|---|
| text | contiene, non contiene, è uguale a, è diverso da, inizia con, finisce con, è vuoto, non è vuoto |
| number | è uguale a, è diverso da, è maggiore di, è minore di, è maggiore o uguale a, è minore o uguale a, è vuoto, non è vuoto |
| select | è uguale a, è diverso da, è vuoto, non è vuoto |
| boolean | è vero, è falso |

`è vuoto` / `non è vuoto` / `è vero` / `è falso` nascondono il campo valore (non è necessario né viene inviato
alcun valore).

### 5.3 Esempi pratici

Le chiavi di campo riportate qui sotto sono quelle effettivamente selezionate nel menu a tendina "Campo" (il menu
mostra l'etichetta in italiano; la chiave sottostante è indicata qui per chiarezza quando si legge/scrive
`dashboard.js`).

```
Fornitori attivi di Milano
  address.city        è uguale a       Milano
  is_active            è vero

Società senza Partita IVA
  vendor_type          è uguale a       Società
  vat_number            è vuoto

Fornitori con valutazione ottima e alto adempimento
  vendor_final_evaluation   è uguale a         MOLTO POSITIVO
  fulfillment_rate           è maggiore o uguale a   90

Contratti scaduti tra i fornitori attivi
  contractual_status    è uguale a   06     (06 = Contratto Scaduto)
  is_active               è vero

Fornitori esteri
  address.country       è diverso da   Italia
  address.country       non è vuoto

Email con dominio Gmail (proxy per "email non aziendale")
  email                 finisce con    @gmail.com
```

### 5.4 Limitazioni note

- Nessun OR tra le righe di filtro né all'interno del valore di una singola riga.
- Nessun filtro per data/intervallo (nel modello non è esposto nulla per le date di contratto/qualifica).
- I campi `address.*` escludono i fornitori senza un `Address` collegato — non esiste un filtro dedicato "nessun
  indirizzo" al di là dell'uso di `address.city` + `è vuoto`, che comunque richiede che il fornitore abbia una
  riga `Address` con città vuota.
- **I filtri avanzati e i filtri da click sui grafici influenzano entrambi la tabella, le statistiche e i
  grafici a pagina, ma solo i filtri da click sui grafici (più la casella di ricerca) vengono inviati all'export
  Excel** — vedi §6. Questo è un divario reale e attuale, non un errore di documentazione: `exportToExcel()` in
  `dashboard.js` serializza nell'URL di export solo `activeFilters` + il termine di ricerca; `advancedFilters`
  non esce mai dal browser.

## 6. Export Excel

Pulsante: "Esporta Excel" verde (in basso a destra, posizione fissa) → `GET /vendors/export-excel/`
(`vendors:export-vendors-excel`), gestito da `export_vendors_excel` in `dashboard_views.py`.

- **Autenticazione**: `@login_required` (autenticazione basata su sessione) — *non* token auth, nonostante quanto
  affermato dai vecchi documenti.
- **Filtri rispettati**: solo i filtri da click sui grafici e la casella di ricerca (vedi l'avvertenza in §5.4).
  Parametri query accettati, separati da virgola per quelli multi-valore:

| Param | Maps to |
|---|---|
| `regions` | `address__region__in` |
| `provinces` | `address__state_province__in` |
| `vendor_types` | `vendor_type__in` |
| `ico_consultant` | `true`/`false` → `is_ico_consultant` |
| `competencies` | `competences__name__in` |
| `certifications` | fornitori con `vendor_competences.has_certification=True` e nome competenza corrispondente |
| `qualifiche` | fornitori con `vendor_competences.is_qualifica=True, has_competence=True` e nome corrispondente |
| `competenze_req` | fornitori con `vendor_competences.is_competenza=True, has_competence=True` e nome corrispondente |
| `service_categories` | `vendor_services__service_type__parent__name__in` |
| `services` | `vendor_services__service_type__name__in` |
| `search` | stessa logica di corrispondenza per sottostringa del §4, applicata lato server (`vendor_code`, `name`, `email`) |

Esistono anche parametri "legacy" ancora gestiti per retrocompatibilità, provenienti da una versione precedente
della dashboard: `category`, `qualification_status`, `risk_level`, `service_type` — nessuno di questi viene mai
inviato dal template/JS attuale, ma l'endpoint continua ad accettarli se si costruisce l'URL a mano.

- **Colonne esportate** (codice attuale — molto più ridotto delle "22 colonne" pubblicizzate dai vecchi
  documenti, che descrivevano una versione precedente di questo endpoint): **Nome, Tipo, Email, Telefono,
  Regione, Provincia, Valutazione Complessiva**. Nessun codice fornitore, nessuna Partita IVA/Codice Fiscale,
  nessun indirizzo (via/CAP), nessuna metrica di performance oltre alla valutazione finale. Se serve un export
  più completo, `export_vendors_excel` è il punto in cui estenderlo.
- **File**: foglio singolo "Fornitori", riga di intestazione in grassetto bianco su sfondo blu, colonne a
  larghezza automatica, nome file sempre `fornitori_export.xlsx` (nessun timestamp nell'implementazione attuale,
  nonostante i vecchi documenti ne descrivessero uno).

## 7. Endpoint API ausiliari (esistono, ma non usati dalla UI attuale)

Due endpoint aggiuntivi sono collegati in `urls.py` e definiti in `dashboard_views.py`. Nessuno dei due viene
chiamato oggi da `dashboard.js` — utile saperlo se si sta facendo debug del tipo "perché la scheda network non
mostra una fetch verso questo endpoint" oppure se si sta integrando qualcosa di esterno contro di essi.

**`GET /vendors/dashboard-stats/`** (`dashboard_stats_api`, `@csrf_exempt`, nessun decoratore di autenticazione —
nonostante i vecchi documenti affermassero che fosse richiesta l'autenticazione a token):
```json
{"total": 1247, "active": 1180, "pending_qualification": 62, "high_risk": 0}
```
`pending_qualification` conta i casi con `qualification_status in [PENDING, IN_PROGRESS, NOT_STARTED]`;
`high_risk` conta i casi con `risk_level in [HIGH, CRITICAL]`. Si tratta di un payload molto più ridotto rispetto
alla struttura `by_category`/`by_qualification`/`by_risk`/`by_country`/`by_quality`/`by_fulfillment` descritta
dai vecchi documenti (e da `test_dashboard.py`, vedi §9) — quella struttura più ricca non esiste nell'endpoint
attuale.

**`GET /vendors/dashboard-vendors/`** (`dashboard_vendors_list_api`, `@csrf_exempt`, nessuna autenticazione):
restituisce `{"vendors": [...]}` filtrato dai parametri query `category`, `qualification_status`, `risk_level`,
`service_type`, `search` — la struttura di filtro "legacy", con la stessa logica dei parametri legacy
dell'endpoint di export.

## 8. Creare dati fornitore di esempio/test in locale

Per avere qualcosa da guardare/filtrare, apri una shell (`python manage.py shell` oppure `docker compose exec
django python manage.py shell`) ed esegui qualcosa del genere. Questo corregge lo snippet che si trovava
precedentemente nel file `INSTALLATION_INSTRUCTIONS.md` di root, che chiamava
`Vendor.objects.create(..., country=...)` — `Vendor` non ha un proprio campo `country` (solo `Address.country`
ce l'ha), quindi quello snippet solleva un `TypeError` contro il modello attuale. `vendor_code` è la chiave
primaria del modello e viene generato automaticamente in `save()` se omesso — non passarlo.

```python
from vendor_management_system.vendors.models import Vendor, Category, Address

cat1 = Category.objects.create(code="SERV", name="Servizi", is_active=True)
cat2 = Category.objects.create(code="PROD", name="Prodotti", is_active=True)

addr = Address.objects.create(
    street_address="Via Roma 123",
    city="Milano",
    state_province="Milano",
    region="Lombardia",
    postal_code="20100",
    country="Italia",
)

vendor_types = ["Società", "Professionista", "Internazionale"]
evaluations = ["DA VALUTARE", "POSITIVO", "MOLTO POSITIVO", "NEGATIVO"]

for i in range(20):
    Vendor.objects.create(
        name=f"Fornitore Test {i}",
        email=f"fornitore{i}@test.com",
        phone=f"+39 02 1234567{i}",
        category=cat1 if i % 2 == 0 else cat2,
        address=addr,
        vendor_type=vendor_types[i % len(vendor_types)],
        qualification_status="APPROVED" if i % 3 == 0 else "PENDING",
        vendor_final_evaluation=evaluations[i % len(evaluations)],
        risk_level=["LOW", "MEDIUM", "HIGH"][i % 3],
        quality_rating_avg=round(3.0 + (i % 5) * 0.4, 1),
        fulfillment_rate=round(60 + (i % 5) * 8, 1),
        is_active=True,
        is_ico_consultant=(i % 4 == 0),
        vat_number=f"IT0123456789{i}",
        fiscal_code=f"RSSMRA80A01H501{i}",
    )

print("Created 20 test vendors")
```

Adatta i valori `vendor_type`/`vendor_final_evaluation`/`contractual_status` allo specifico scenario di filtro
che stai testando (vedi gli elenchi di opzioni al §5.1).

## 9. Test automatici

File: `vendor_management_system/vendors/tests/test_dashboard.py`.

```bash
python manage.py test vendor_management_system.vendors.tests.test_dashboard
python manage.py test vendor_management_system.vendors               # whole app
python manage.py test vendor_management_system.vendors.tests.test_dashboard -v 2
# or, in Docker:
docker compose exec django python manage.py test vendor_management_system.vendors.tests.test_dashboard
```

**Attenzione — questo file di test è attualmente disallineato rispetto a `dashboard_views.py`** (scoperto
scrivendo questo documento, vale la pena correggerlo piuttosto che fidarsene ciecamente):
- `test_dashboard_stats_api` verifica che il JSON di risposta abbia le chiavi `by_category`/`by_qualification`/
  `by_risk`/`by_country`/`by_quality`/`by_fulfillment`, ma l'attuale `dashboard_stats_api` restituisce solo
  `total`/`active`/`pending_qualification`/`high_risk` (§7) — questa asserzione fallirà contro il codice attuale.
- `test_api_without_token` si aspetta un `401` da `/vendors/dashboard-stats/` per una richiesta non autenticata,
  ma l'endpoint non ha alcun decoratore di autenticazione (solo `@csrf_exempt`) — attualmente restituisce `200`.
- `setUp()` chiama `Vendor.objects.create(..., country='Italia', ...)`, che — stesso problema dello snippet del
  vecchio documento di installazione al §8 — non è un campo valido su `Vendor` e solleverà un `TypeError` prima
  ancora che venga eseguito il corpo di qualsiasi test.

In breve: così com'è stata committata, questa suite probabilmente non passa. Trattala come una specifica del
comportamento *previsto* per un'iterazione precedente della dashboard, non come una suite di regressione
funzionante, finché qualcuno non la riallinea con l'attuale `dashboard_views.py`.

## 10. Troubleshooting specifico per questa funzionalità

| Symptom | Likely cause | Fix |
|---|---|---|
| I grafici vengono renderizzati vuoti / tutti a zero | Non ci sono ancora dati `Vendor`/`Category`/`Address`/`Competence`/`ServiceType` | Popola qualche dato (§8), oppure esegui i management command `populate_*`/`seed_*` descritti in `docs/PROJECT_OVERVIEW_AND_LOCAL_SETUP.md` §9 |
| Un menu a tendina di filtro ("Tipo Servizio", "Categoria") si comporta in modo strano sui fornitori multi-servizio | `service_type.name` (filtro avanzato) e la colonna "service_type" della tabella considerano solo il `VendorService` **primario** del fornitore (`is_primary=True`) — i servizi non primari vengono lì ignorati | Usa invece i filtri da click sui grafici `services`/`service_categories`, che considerano *tutti* i servizi di un fornitore |
| L'export scarica righe in numero minore/diverso rispetto a quelle a schermo | I filtri avanzati non vengono inviati all'endpoint di export (§5.4/§6) — solo i filtri da click sui grafici + la ricerca lo sono | Ricrea la stessa restrizione usando i click sui grafici (o la casella di ricerca) prima di esportare, oppure estendi `exportToExcel()`/`export_vendors_excel` per serializzare anche `advancedFilters` |
| Nel file di export manca una colonna attesa (Partita IVA, indirizzo, metriche di performance) | `export_vendors_excel` scrive solo 7 colonne (§6) | Estendi il ciclo di costruzione `headers`/righe in `export_vendors_excel` |
| Le chiamate a `dashboard-stats/` o `dashboard-vendors/` da uno strumento esterno restituiscono dati in numero minore/diversi da quelli attesi | Questi endpoint sono vestigiali — la UI della dashboard non li usa, e `dashboard-stats/` è stato ridotto a un certo punto (§7) | Non dare per scontato che corrispondano ai grafici della dashboard stessa; leggi direttamente `dashboard_views.py`, oppure estendili se serve la struttura più ricca |
| I test automatici della dashboard falliscono così come sono | Problema noto — vedi §9 | Correggi la chiamata `Vendor.objects.create(country=...)` in `setUp()` e le asserzioni su `dashboard_stats_api`/autenticazione prima di fare affidamento su questa suite |
| Tutto funziona ma il caricamento iniziale della pagina è lento con un numero elevato di fornitori | L'intero dataset filtrato/non filtrato viene serializzato nella pagina a ogni caricamento (§2) — non c'è paginazione né lazy loading | Non risolto nel codice attuale; servirebbe una paginazione lato server oppure spostare il filtraggio sulla API `dashboard-vendors/` (attualmente inutilizzata) |
