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
insieme di grafici cliccabili, filtri avanzati a menù a tendina, una barra di ricerca, un export Excel filtrato,
la scheda fornitore in sola lettura e la creazione rapida di un fornitore prospetto. È raggiungibile da Admin, BO User
e Buyer (controllo di ruolo `dashboard_required`, vedi [PERMESSI_RUOLI.md](PERMESSI_RUOLI.md)); i Fornitori ricevono
un redirect al portale.

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
| Positivi | `positive_vendors` | Fornitori (all'interno dell'insieme filtrato corrente) con `vendor_final_evaluation` pari a `POSITIVO` (bollino verde) |

Nove grafici cliccabili (canvas `chart-clickable`), ciascuno costruito a partire da `chart_data_json` e ciascuno
che, al click, attiva/disattiva una voce nell'oggetto `activeFilters` descritto in §4:

| Chart (canvas id) | Dimension | `activeFilters` key |
|---|---|---|
| `vendorTypeChart` | `vendor_type` | `vendor_types` (array) |
| `serviceTypeChart` (etichettato "Consulenti ICO") | `is_ico_consultant` | `ico_consultant` (tri-stato: `null`/`true`/`false`) |
| `regionChart` (etichettato "Regioni") | regioni di **competenza** (`vendor.competence.regions`) | `regions` (array di nomi) |
| `provinceChart` | province di **competenza** (solo all'interno delle regioni selezionate) | `provinces` (array di nomi) |
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

## 4. Barra di ricerca

La barra (`#search-input`, dentro la card "Filtri Avanzati") cerca per sottostringa, senza distinguere maiuscole,
solo su: codice Embyon (`old_code`), codice fornitore, ragione sociale, partita IVA e codice fiscale. Si combina in
AND con i filtri da click sui grafici e con i menù a tendina. Lato server lo stesso criterio sta in
`dashboard_filters.apply_search`, usato dall'export.

## 5. Filtri avanzati (menù a tendina)

La card "Filtri Avanzati" è sempre visibile e contiene un menù a tendina per campo, a selezione multipla con
casella di ricerca interna: Classificazione, Tipo Fornitore, Valutazione Finale, Servizi erogati, Competenze,
Qualifiche professionali, Certificazioni, Paese, Regione, Provincia. Le opzioni sono i valori realmente censiti.

- **Logica**: dentro lo stesso menù i valori sono in **OR** (basta averne uno), tra menù diversi (e con i filtri da
  click sui grafici e la ricerca) in **AND**.
- **Classificazione**: principale o aggiuntive del fornitore.
- **Competenze / Qualifiche professionali**: requisiti assegnati come competenza o come qualifica (flag
  `is_competenza`/`is_qualifica` con `has_competence`), gli stessi dei grafici omonimi.
- **Paese / Regione / Provincia**: zone di **competenza**, non la sede, come i grafici Regioni/Province. Il Paese
  copre le nazioni estere e l'Italia (se il fornitore ha province di competenza).
- Il pulsante "Cancella filtri" azzera menù e ricerca; il badge indica quanti valori sono selezionati.
- I menù influenzano tabella, statistiche e grafici (tramite `matchesDropdownFilters` in `dashboard.js`) e vengono
  inviati all'export con i parametri `dd_classifications`, `dd_vendor_types`, `dd_final_evaluations`, `dd_services`,
  `dd_competenze`, `dd_qualifiche`, `dd_certifications`, `dd_countries`, `dd_regions`, `dd_provinces` (CSV; paese,
  regione e provincia per codice), applicati da `dashboard_filters.apply_dropdown_filters`.

Il vecchio generatore di righe `campo / operatore / valore` è stato rimosso.

### 5.1 Scheda fornitore in sola lettura

L'occhio nella tabella apre una modale con tutte le sezioni del fornitore (informazioni base, contatti, servizi,
abilitazioni e requisiti, documenti, contratti, qualifica e audit, valutazioni, attributi operativi) senza campi
modificabili: `GET /vendors/dashboard/vendor/<codice>/` (`dashboard_vendor_views.vendor_detail_view`) restituisce un
frammento HTML. Dei documenti si vedono tipo, stato e date, non i file. Così chi non entra in `/admin/` consulta
l'anagrafica senza poterla modificare.

### 5.2 Aggiungi fornitore prospetto

Il pulsante sopra ai filtri apre una modale con ragione sociale, partita IVA o codice fiscale (almeno uno) ed email.
`POST /vendors/dashboard/prospect/` (`prospect.create_prospect`) crea il fornitore "In attesa", imposta chi lo crea
come utente di gestione, crea l'utenza del portale e invia subito l'invito. Il codice fiscale duplicato blocca, la
partita IVA duplicata avvisa; un'email già usata da un utente blocca prima di creare l'anagrafica. Se l'invio
dell'email fallisce il fornitore resta creato e l'operatore può usare "Reinvia invito" dall'admin.

## 6. Export Excel

Pulsante: "Esporta Excel" verde (in basso a destra, posizione fissa) → `GET /vendors/export-excel/`
(`vendors:export-vendors-excel`), gestito da `export_vendors_excel` in `dashboard_views.py`.

- **Autenticazione**: `@dashboard_required` (sessione; Admin, BO User e Buyer) — *non* token auth, nonostante quanto
  affermato dai vecchi documenti.
- **Filtri rispettati**: filtri da click sui grafici, menù a tendina (§5) e barra di ricerca.
  Parametri query accettati, separati da virgola per quelli multi-valore:

| Param | Maps to |
|---|---|
| `comp_regions` | fornitori che coprono quelle regioni (codici, es. `LOM,VEN`) |
| `comp_provinces` | fornitori che coprono quelle province (sigle, es. `MI,RA`) |
| `comp_countries` | fornitori che coprono quelle nazioni (codici ISO, es. `FR`) |
| `vendor_types` | `vendor_type__in` |
| `ico_consultant` | `true`/`false` → `is_ico_consultant` |
| `competencies` | `competences__name__in` |
| `certifications` | fornitori con `vendor_competences.has_certification=True` e nome competenza corrispondente |
| `qualifiche` | fornitori con `vendor_competences.is_qualifica=True, has_competence=True` e nome corrispondente |
| `competenze_req` | fornitori con `vendor_competences.is_competenza=True, has_competence=True` e nome corrispondente |
| `service_categories` | `vendor_services__service_type__parent__name__in` |
| `services` | `vendor_services__service_type__name__in` |
| `search` | stessa logica di corrispondenza per sottostringa del §4, applicata lato server (`vendor_code`, `name`, `email`) |

> **Cambio incompatibile**: i vecchi parametri `regions` e `provinces` filtravano per *nome* sulla
> **sede** del fornitore (`address__region` / `address__state_province`) e non esistono più. Al loro posto ci
> sono `comp_regions`/`comp_provinces`/`comp_countries`, che filtrano per *codice* sulle **zone di competenza**.
> Vecchi link o bookmark dell'export che usavano i nomi smettono di filtrare (senza errori).

Esistono anche parametri "legacy" ancora gestiti per retrocompatibilità, provenienti da una versione precedente
della dashboard: `category`, `qualification_status`, `risk_level`, `service_type` — nessuno di questi viene mai
inviato dal template/JS attuale, ma l'endpoint continua ad accettarli se si costruisce l'URL a mano.

- **Colonne esportate** (codice attuale — molto più ridotto delle "22 colonne" pubblicizzate dai vecchi
  documenti, che descrivevano una versione precedente di questo endpoint): **Nome, Tipo, Email, Telefono,
  Regione, Provincia, Valutazione Finale, Zone di Competenza, Province Competenza**. Nessun codice fornitore, nessuna Partita IVA/Codice Fiscale,
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

for i in range(20):
    Vendor.objects.create(
        name=f"Fornitore Test {i}",
        email=f"fornitore{i}@test.com",
        phone=f"+39 02 1234567{i}",
        category=cat1 if i % 2 == 0 else cat2,
        address=addr,
        vendor_type=vendor_types[i % len(vendor_types)],
        # Il bollino (vendor_final_evaluation) lo calcola save().
        qualification_status="APPROVED" if i % 3 == 0 else "PENDING",
        embyon_active=i % 5 != 0,
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

Adatta i valori `vendor_type`/`qualification_status`/`embyon_active`/`contractual_status` allo specifico scenario di filtro
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
| Nel file di export manca una colonna attesa (Partita IVA, indirizzo, metriche di performance) | `export_vendors_excel` scrive solo 7 colonne (§6) | Estendi il ciclo di costruzione `headers`/righe in `export_vendors_excel` |
| Le chiamate a `dashboard-stats/` o `dashboard-vendors/` da uno strumento esterno restituiscono dati in numero minore/diversi da quelli attesi | Questi endpoint sono vestigiali — la UI della dashboard non li usa, e `dashboard-stats/` è stato ridotto a un certo punto (§7) | Non dare per scontato che corrispondano ai grafici della dashboard stessa; leggi direttamente `dashboard_views.py`, oppure estendili se serve la struttura più ricca |
| I test automatici della dashboard falliscono così come sono | Problema noto — vedi §9 | Correggi la chiamata `Vendor.objects.create(country=...)` in `setUp()` e le asserzioni su `dashboard_stats_api`/autenticazione prima di fare affidamento su questa suite |
| Tutto funziona ma il caricamento iniziale della pagina è lento con un numero elevato di fornitori | L'intero dataset filtrato/non filtrato viene serializzato nella pagina a ogni caricamento (§2) — non c'è paginazione né lazy loading | Non risolto nel codice attuale; servirebbe una paginazione lato server oppure spostare il filtraggio sulla API `dashboard-vendors/` (attualmente inutilizzata) |
