# Dashboard Fornitori - Guida Utente

## 📊 Panoramica

La Dashboard Fornitori è uno strumento completo per analizzare e classificare i fornitori secondo diverse dimensioni:

- **Categoria merceologica**
- **Stato qualifica** (Approvato, In attesa, Respinto)
- **Livello di rischio** (Basso, Medio, Alto)
- **Distribuzione geografica**
- **Performance** (Qualità, Adempimento)

## 🚀 Accesso

La dashboard è accessibile all'URL:
```
/vendors/dashboard/
```

È richiesta l'autenticazione. Gli utenti devono essere loggati per accedere.

## 📈 Funzionalità Principali

### 1. Statistiche Generali (Card in Alto)

Quattro card mostrano statistiche chiave:
- **Fornitori Totali**: Numero totale di fornitori nel sistema
- **Attivi**: Fornitori con flag `is_active=True`
- **In Qualifica**: Fornitori con `qualification_status='PENDING'`
- **Alto Rischio**: Fornitori con `risk_level='HIGH'`

### 2. Grafici Interattivi

Sei grafici permettono di visualizzare i fornitori per dimensione:

#### 📦 Fornitori per Categoria
- Tipo: Grafico a ciambella (Doughnut)
- Mostra la distribuzione dei fornitori per categoria merceologica
- **Clic sul grafico**: filtra la tabella per la categoria selezionata

#### ✅ Stato Qualifica
- Tipo: Grafico a torta (Pie)
- Stati: Approvato, In attesa, Respinto
- **Clic sul grafico**: filtra per stato qualifica

#### ⚠️ Livello di Rischio
- Tipo: Grafico a barre orizzontale
- Livelli: Basso, Medio, Alto
- **Clic sul grafico**: filtra per livello di rischio

#### 🌍 Distribuzione Geografica
- Tipo: Grafico a barre orizzontale
- Mostra i top 10 paesi per numero di fornitori
- **Clic sul grafico**: filtra per paese

#### ⭐ Qualità Media
- Tipo: Grafico a barre
- Distribuisce i fornitori in fasce di rating qualità (0-1, 1-2, 2-3, 3-4, 4-5, N/A)
- Basato sul campo `quality_rating_avg`

#### 📊 Tasso di Adempimento
- Tipo: Grafico a barre
- Distribuisce i fornitori in fasce percentuali (0-20%, 20-40%, ..., 80-100%, N/A)
- Basato sul campo `fulfillment_rate`

### 3. Filtri Attivi

Quando si clicca su un grafico, viene applicato un filtro. I filtri attivi vengono visualizzati in un banner blu con la possibilità di:
- Rimuovere singoli filtri (clic sulla X)
- Cancellare tutti i filtri (pulsante "Cancella tutti i filtri")

### 4. Ricerca Testuale

Campo di ricerca in tempo reale che filtra i fornitori per:
- Codice fornitore
- Nome
- Email
- Categoria

### 5. Tabella Fornitori

Tabella completa e responsive con le seguenti colonne:
- **Codice**: Codice univoco fornitore
- **Nome**: Nome e email del fornitore
- **Categoria**: Categoria merceologica
- **Stato Qualifica**: Badge colorato (Verde=Approvato, Giallo=In attesa, Rosso=Respinto)
- **Rischio**: Badge colorato per il livello di rischio
- **Paese**: Paese di provenienza
- **Performance**: Rating qualità con stelle
- **Azioni**: Link per visualizzare dettagli fornitore

### 6. Esportazione Excel

**Pulsante fisso in basso a destra**: 
- Icona Excel verde
- Esporta i fornitori **filtrati** in formato Excel (.xlsx)
- Include tutti i dati del fornitore:
  - Informazioni generali (Codice, Nome, Email, Telefono)
  - Classificazione (Categoria, Qualifica, Rischio, Paese)
  - Indirizzo completo
  - Dati fiscali (P.IVA, Codice Fiscale)
  - Metriche performance (Rating qualità, Tasso consegna, Tasso adempimento)
  - Date audit e qualifica
  - Note revisione

**Caratteristiche del file Excel**:
- Header colorato e formattato
- Colonne auto-ridimensionate
- Riga header fissa (freeze pane)
- Nome file con timestamp: `fornitori_export_YYYYMMDD_HHMMSS.xlsx`

## 🔧 API Endpoints

### Dashboard Stats
```
GET /vendors/dashboard-stats/
```
Ritorna dati aggregati per tutti i grafici in formato JSON.

**Autenticazione**: Richiesta (Token Authentication)

**Response**:
```json
{
  "by_category": [
    {"category": "Servizi", "count": 15},
    {"category": "Materiali", "count": 8}
  ],
  "by_qualification": [
    {"status": "APPROVED", "count": 18},
    {"status": "PENDING", "count": 3}
  ],
  "by_risk": [
    {"risk": "LOW", "count": 10},
    {"risk": "MEDIUM", "count": 8},
    {"risk": "HIGH", "count": 5}
  ],
  "by_country": [
    {"country": "Italia", "count": 20},
    {"country": "Francia", "count": 3}
  ],
  "by_quality": [
    {"range": "4-5", "count": 12},
    {"range": "3-4", "count": 6}
  ],
  "by_fulfillment": [
    {"range": "80-100%", "count": 15},
    {"range": "60-80%", "count": 5}
  ]
}
```

### Export Excel
```
GET /vendors/export-excel/?category=<cat>&qualification_status=<status>&risk_level=<risk>&country=<country>&search=<term>
```
Scarica un file Excel con i fornitori filtrati.

**Parametri Query** (tutti opzionali):
- `category`: Nome categoria
- `qualification_status`: APPROVED, PENDING, o REJECTED
- `risk_level`: LOW, MEDIUM, o HIGH
- `country`: Nome paese
- `search`: Termine di ricerca

**Autenticazione**: Richiesta (Token Authentication)

**Response**: File Excel binario

## 📋 Installazione

### 1. Dipendenze Python

Assicurati che `openpyxl` sia installato:

```bash
pip install openpyxl==3.1.2
```

O aggiungi al `requirements.txt`:
```
openpyxl==3.1.2
```

### 2. Template e Static Files

I template sono già posizionati in:
```
vendor_management_system/vendors/templates/vendors/vendor_dashboard.html
```

Le librerie JavaScript/CSS sono caricate da CDN:
- Bootstrap 5.3.0
- Font Awesome 6.0.0
- Chart.js 4.4.0

### 3. URL Configuration

Gli URL sono configurati in `vendor_management_system/vendors/urls.py`:

```python
urlpatterns = [
    path("dashboard/", vendor_dashboard_view, name="vendor-dashboard"),
    path("dashboard-stats/", dashboard_stats_api, name="dashboard-stats-api"),
    path("export-excel/", export_vendors_excel, name="export-vendors-excel"),
    # ... altri URL
]
```

Accessibili tramite il prefisso `/vendors/` definito in `config/urls.py`.

## 🎨 Personalizzazione

### Colori e Temi

I colori sono definiti nel tag `<style>` del template. Puoi personalizzare:

```css
.stats-card {
    border-left-color: #007bff; /* Colore principale */
}

.stats-card.warning { border-left-color: #ffc107; }
.stats-card.danger { border-left-color: #dc3545; }
.stats-card.success { border-left-color: #28a745; }
```

### Aggiungere Nuovi Grafici

Per aggiungere un nuovo grafico:

1. **Aggiungi HTML nel template**:
```html
<div class="col-lg-6 mb-3">
    <div class="chart-container">
        <h5 class="mb-3">Nuovo Grafico</h5>
        <canvas id="nuovoChart"></canvas>
    </div>
</div>
```

2. **Crea funzione JavaScript**:
```javascript
function createNuovoChart(data) {
    const ctx = document.getElementById('nuovoChart').getContext('2d');
    charts.nuovo = new Chart(ctx, {
        type: 'bar',
        data: { /* ... */ },
        options: { /* ... */ }
    });
}
```

3. **Aggiungi dati in dashboard_stats_api**:
```python
# In views.py
new_data = list(
    Vendor.objects.values('campo')
    .annotate(count=Count('vendor_code'))
)
return JsonResponse({
    # ... altri dati
    'by_new_dimension': new_data
})
```

## 🐛 Troubleshooting

### Grafici non si caricano
- Verifica che l'endpoint `/vendors/dashboard-stats/` risponda correttamente
- Controlla la console browser per errori JavaScript
- Verifica autenticazione utente

### Export Excel non funziona
- Verifica che `openpyxl` sia installato: `pip list | grep openpyxl`
- Controlla i log Django per errori
- Verifica permessi di scrittura temporanei

### Filtri non funzionano
- Verifica che i dati dei grafici contengano le chiavi corrette
- Controlla la console browser per errori JavaScript
- Verifica che i nomi delle dimensioni corrispondano

## 📝 Note Tecniche

### Performance

Per dataset molto grandi (>1000 fornitori):
- Considera paginazione lato server
- Implementa caching per dashboard_stats_api
- Usa select_related/prefetch_related nelle query

### Sicurezza

- Tutti gli endpoint richiedono autenticazione
- I filtri usano query Django ORM (protezione SQL injection)
- Export Excel limitato ai dati accessibili all'utente autenticato

## 🔄 Aggiornamenti Futuri

Possibili miglioramenti:
- [ ] Paginazione lato server per tabella fornitori
- [ ] Salvataggio filtri preferiti per utente
- [ ] Export in altri formati (PDF, CSV)
- [ ] Dashboard personalizzabile con drag&drop
- [ ] Grafici drill-down (clic per dettagli)
- [ ] Notifiche real-time per cambiamenti dati
- [ ] Confronto temporale (dashboard storica)

## 📞 Supporto

Per domande o problemi:
- Consulta la documentazione API: `/swagger/`
- Verifica i log Django
- Controlla la configurazione URL

---

**Versione**: 1.0  
**Data**: Novembre 2025  
**Modulo**: vendors
