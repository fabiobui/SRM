# Dashboard Fornitori - Riepilogo Implementazione

## 🎯 Obiettivo
Creare una dashboard per il modulo vendors con layout simile a admin_dashboard.html ma con logica dedicata alla classificazione e analisi dei fornitori per dimensioni multiple con esportazione Excel.

## ✅ Implementazione Completata

### 1. Template HTML (`vendor_dashboard.html`)
**Posizione**: `vendor_management_system/vendors/templates/vendors/vendor_dashboard.html`

**Caratteristiche**:
- Layout responsive con Bootstrap 5.3.0
- 4 card statistiche in alto (Totali, Attivi, In Qualifica, Alto Rischio)
- 6 grafici interattivi con Chart.js 4.4.0:
  - Fornitori per Categoria (Doughnut)
  - Stato Qualifica (Pie)
  - Livello di Rischio (Bar)
  - Distribuzione Geografica (Horizontal Bar - Top 10)
  - Qualità Media (Bar con fasce)
  - Tasso Adempimento (Bar con fasce percentuali)
- Sistema di filtri interattivi (clic sui grafici)
- Visualizzazione filtri attivi con rimozione
- Ricerca testuale in tempo reale
- Tabella fornitori con badge colorati per status
- Pulsante fisso export Excel con conteggio filtrati

### 2. View Django (`views.py`)
**Funzioni aggiunte**:

#### `vendor_dashboard_view(request)`
- View principale per renderizzare il template
- Calcola statistiche di base: totali, attivi, pending, high-risk
- Richiede autenticazione (`@login_required`)

#### `dashboard_stats_api(request)` 
- Endpoint API REST per dati grafici
- Ritorna JSON con aggregazioni per tutte le dimensioni
- Autenticazione: Token Authentication
- Aggregazioni Django ORM ottimizzate con `Count`, `annotate`

#### `export_vendors_excel(request)`
- Genera file Excel con openpyxl
- Supporta filtri query parameters
- 22 colonne di dati inclusi:
  - Info base (codice, nome, email, telefono)
  - Classificazione (categoria, qualifica, rischio, paese)
  - Indirizzo completo
  - Dati fiscali (P.IVA, CF)
  - Metriche performance
  - Date audit/qualifica
  - Note
- Header formattato con stili
- Colonne auto-ridimensionate
- Nome file con timestamp

### 3. URL Configuration (`urls.py`)
**Route aggiunte**:
```python
path("dashboard/", vendor_dashboard_view, name="vendor-dashboard")
path("dashboard-stats/", dashboard_stats_api, name="dashboard-stats-api")
path("export-excel/", export_vendors_excel, name="export-vendors-excel")
```

**URL completi**:
- `/vendors/dashboard/` - Vista dashboard
- `/vendors/dashboard-stats/` - API dati grafici
- `/vendors/export-excel/?filters` - Download Excel

### 4. Dipendenze (`requirements.txt`)
**Aggiunto**:
```
openpyxl==3.1.2
```

Per gestire creazione file Excel con formattazione.

### 5. Documentazione
**File creati**:
- `README_DASHBOARD.md` - Guida completa utente e sviluppatore
- `tests/test_dashboard.py` - Suite test automatici

## 📊 Dimensioni di Classificazione Implementate

1. **Categoria Merceologica** (`category`)
   - Campo: `vendor.category` (ForeignKey)
   - Gestisce "Non Classificato" per NULL values

2. **Stato Qualifica** (`qualification_status`)
   - Valori: APPROVED, PENDING, REJECTED
   - Badge colorati: Verde, Giallo, Rosso

3. **Livello di Rischio** (`risk_level`)
   - Valori: LOW, MEDIUM, HIGH
   - Badge colorati: Verde, Giallo, Rosso

4. **Paese** (`country`)
   - Stringa libera
   - Top 10 paesi nel grafico
   - Gestisce "Non Specificato" per NULL values

5. **Qualità Media** (`quality_rating_avg`)
   - Range: 0-5
   - Fasce: 0-1, 1-2, 2-3, 3-4, 4-5, N/A

6. **Tasso Adempimento** (`fulfillment_rate`)
   - Percentuale: 0-100
   - Fasce: 0-20%, 20-40%, 40-60%, 60-80%, 80-100%, N/A

## 🎨 Interattività

### Clic sui Grafici
Ogni grafico è cliccabile:
- **Categoria**: Filtra fornitori per categoria selezionata
- **Qualifica**: Filtra per stato qualifica
- **Rischio**: Filtra per livello rischio
- **Paese**: Filtra per paese

### Gestione Filtri
- I filtri si accumulano (AND logic)
- Visualizzazione badge filtri attivi
- Rimozione singola (X su badge)
- Rimozione totale (pulsante "Cancella tutti")
- Filtri applicati anche all'export Excel

### Ricerca
- Campo input con debounce
- Cerca in: codice, nome, email, categoria
- Si combina con filtri grafici

## 🔧 Tecnologie Utilizzate

### Frontend
- **Bootstrap 5.3.0**: Layout responsive
- **Font Awesome 6.0.0**: Icone
- **Chart.js 4.4.0**: Grafici interattivi
- **Vanilla JavaScript**: Logica filtri e interazione

### Backend
- **Django 5.0.6**: Framework web
- **Django REST Framework 3.15.1**: API endpoints
- **openpyxl 3.1.2**: Generazione Excel
- **Django ORM**: Query ottimizzate con aggregazioni

## 📈 Performance

### Ottimizzazioni Implementate
1. **select_related/prefetch_related** nelle query
2. **Aggregazioni database-side** per statistiche
3. **Lazy loading** grafici (caricamento asincrono)
4. **Client-side filtering** tabella (no round-trip server)
5. **CDN** per librerie JS/CSS (caricamento parallelo)

### Scalabilità
Per dataset >1000 fornitori, considerare:
- Paginazione server-side tabella
- Caching Redis per dashboard-stats API
- Lazy loading grafici con scroll
- Web Workers per elaborazione client-side

## 🧪 Testing

### Test Implementati
File: `tests/test_dashboard.py`

Test coverage:
- ✅ Accessibilità dashboard (autenticato)
- ✅ Redirect login (non autenticato)
- ✅ API stats struttura JSON corretta
- ✅ API stats dati aggregati corretti
- ✅ Export Excel accessibile
- ✅ Export Excel con filtri
- ✅ Contesto template corretto
- ✅ Autenticazione API richiesta

**Eseguire test**:
```bash
python manage.py test vendor_management_system.vendors.tests.test_dashboard
```

## 🚀 Deployment

### Passi per Produzione

1. **Installare dipendenze**:
```bash
pip install -r requirements.txt
```

2. **Collect static files**:
```bash
python manage.py collectstatic --noinput
```

3. **Migrazioni** (se necessario):
```bash
python manage.py migrate
```

4. **Verificare URL** nel browser:
```
http://your-domain/vendors/dashboard/
```

5. **Configurare cache** (opzionale ma raccomandato):
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

6. **Applicare cache alla API** (opzionale):
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache 5 minuti
@api_view(['GET'])
def dashboard_stats_api(request):
    # ...
```

## 📝 Checklist Finale

- [x] Template HTML creato e funzionante
- [x] View Django implementate
- [x] API endpoint per grafici
- [x] API endpoint per export Excel
- [x] URL configurati
- [x] Dipendenze aggiunte a requirements.txt
- [x] Documentazione README completa
- [x] Test suite implementata
- [x] Gestione autenticazione
- [x] Filtri interattivi funzionanti
- [x] Export Excel con filtri
- [x] Layout responsive mobile-friendly
- [x] Grafici interattivi Chart.js
- [x] Badge colorati per status
- [x] Ricerca testuale

## 🎓 Come Usare

### Per l'Utente Finale
1. Accedi al sistema: `/admin/` o login page
2. Naviga a: `/vendors/dashboard/`
3. Esplora i grafici cliccando per filtrare
4. Usa la ricerca per trovare fornitori specifici
5. Clicca "Esporta Excel" per scaricare dati filtrati

### Per lo Sviluppatore
```python
# Aggiungere nuova dimensione:

# 1. In views.py - dashboard_stats_api
new_dimension = list(
    Vendor.objects.values('nuovo_campo')
    .annotate(count=Count('vendor_code'))
)

# 2. In template - aggiungere grafico HTML
<div class="chart-container">
    <canvas id="newChart"></canvas>
</div>

# 3. In template - JavaScript
function createNewChart(data) {
    // Chart.js config
}

# 4. Chiamare in loadChartData()
createNewChart(data.by_new_dimension);
```

## 🐛 Known Issues / Limitazioni

1. **Export Excel grandi dataset**: Per >10k fornitori può essere lento
   - Soluzione: Implementare export asincrono con Celery

2. **Browser IE non supportato**: Chart.js richiede browser moderni
   - Soluzione: Aggiungere polyfills o fallback message

3. **Mobile grafici piccoli**: Su schermi <768px i grafici sono compressi
   - Soluzione: Implementare carousel o tab per grafici mobile

## 📞 Supporto e Manutenzione

### Log Debugging
```python
import logging
logger = logging.getLogger(__name__)

# In view:
logger.debug(f"Dashboard accessed by {request.user}")
logger.info(f"Export Excel: {len(vendors)} vendors")
```

### Monitoring
```python
# Aggiungere metriche Prometheus (opzionale)
from prometheus_client import Counter

dashboard_views = Counter('dashboard_views', 'Dashboard page views')
excel_exports = Counter('excel_exports', 'Excel export count')
```

## 🔄 Roadmap Future

Prossimi sviluppi suggeriti:
- [ ] Dashboard personalizzabile per utente
- [ ] Salvataggio filtri preferiti
- [ ] Export PDF con grafici
- [ ] Confronto temporale (trend)
- [ ] Alert configurabili
- [ ] Drill-down grafici multi-livello
- [ ] Integrazione Business Intelligence
- [ ] Dashboard mobile app
- [ ] Real-time updates (WebSocket)

## 📅 Aggiornamenti Recenti

### Versione 1.1.0 - 13 Novembre 2025

#### 🎯 Nuova Funzionalità: Filtri Avanzati Stile Redmine

**Descrizione**: Aggiunta una sezione di filtri avanzati completamente personalizzabile, simile al sistema di filtri di Redmine, che permette di filtrare i fornitori su qualsiasi campo con operatori multipli.

**Caratteristiche implementate**:

1. **Pannello Filtri Espandibile**
   - Card collassabile con header cliccabile
   - Badge con contatore filtri attivi
   - Posizionato tra le statistiche e i grafici

2. **Sistema di Filtri Dinamico**
   - Possibilità di aggiungere/rimuovere filtri dinamicamente
   - 22 campi disponibili per il filtraggio
   - 4 tipi di campo supportati (testo, numero, selezione, booleano)
   - Operatori specifici per ogni tipo di campo

3. **Campi Disponibili**:
   - Info base: nome, codice, tipo, email, telefono
   - Dati fiscali: P.IVA, codice fiscale
   - Stato: qualifica, valutazione finale, attivo, ICO, contrattuale
   - Performance: qualità, adempimento
   - Localizzazione: città, regione, provincia, paese
   - Classificazione: categoria, tipo servizio

4. **Operatori per Tipo**:
   - **Testo**: contiene, non contiene, uguale, diverso, inizia con, finisce con, vuoto, non vuoto
   - **Numero**: uguale, diverso, maggiore, minore, maggiore/uguale, minore/uguale, vuoto, non vuoto
   - **Selezione**: uguale, diverso, vuoto, non vuoto
   - **Booleano**: è vero, è falso

5. **Interfaccia Utente**:
   - Riga filtro con 3 dropdown + pulsante rimuovi
   - Pulsante "Aggiungi Filtro" per aggiungere nuove righe
   - Pulsante "Applica Filtri" per eseguire il filtraggio
   - Pulsante "Cancella Tutti" per reset completo
   - Badge colorati per visualizzare filtri attivi (stile gradiente viola)

6. **Integrazione**:
   - Lavora in combinazione con filtri grafici esistenti
   - Compatibile con la ricerca testuale
   - Aggiorna automaticamente statistiche e grafici
   - Rispettato nell'export Excel

**File modificati**:
- `templates/vendors/vendor_dashboard.html`: aggiunto pannello filtri
- `static/vendors/css/dashboard.css`: nuovi stili per filtri avanzati
- `static/vendors/js/dashboard.js`: logica JavaScript per filtri dinamici

**Nuovi file**:
- `README_FILTRI_AVANZATI.md`: documentazione completa utente

**Testing**:
- Testato con dataset di 100+ fornitori
- Verificato su Chrome, Firefox, Safari
- Compatibilità mobile responsive

**Performance**:
- Filtri applicati lato client (nessun carico server)
- Risposta istantanea anche con 10+ filtri attivi
- Nessun impatto sulle performance esistenti

**Esempi d'uso**:
```javascript
// Esempio 1: Fornitori attivi di Milano
Campo: Città → Operatore: è uguale a → Valore: Milano
Campo: Attivo → Operatore: è vero

// Esempio 2: Società senza P.IVA
Campo: Tipo Fornitore → Operatore: è uguale a → Valore: Società
Campo: Partita IVA → Operatore: è vuoto

// Esempio 3: Alto rischio con basso adempimento
Campo: Stato Qualifica → Operatore: è uguale a → Valore: APPROVED
Campo: Tasso Adempimento → Operatore: è minore di → Valore: 50
```

**Roadmap filtri**:
- [ ] Salvataggio preset filtri per utente
- [ ] Condivisione URL con filtri
- [ ] Operatore OR tra gruppi di filtri
- [ ] Export/import configurazione filtri
- [ ] Filtri su date e range temporali
- [ ] Suggerimenti intelligenti basati su dati

---

**Implementazione completata**: Novembre 2025  
**Modulo**: vendors  
**Versione**: 1.1.0
