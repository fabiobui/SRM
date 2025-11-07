# Organizzazione delle Views - Vendors App

## Struttura

Le views dell'app `vendors` sono organizzate in due file distinti per separare le responsabilità:

### 1. `views.py` - API REST Endpoints
Contiene tutti i ViewSet per le API REST:
- **AddressViewSet**: Gestione indirizzi (CRUD completo)
- **CategoryViewSet**: Gestione categorie (CRUD + tree/stats/vendors)
- **VendorViewSet**: Gestione fornitori (CRUD + qualification/audit/performance/alerts/address)
- **QueryParamObtainAuthToken**: Autenticazione tramite token

**Caratteristiche:**
- Autenticazione tramite `QueryParameterTokenAuthentication`
- Documentazione Swagger completa
- Endpoint RESTful con serializers dedicati
- Gestione permessi tramite DRF

### 2. `dashboard_views.py` - Dashboard Views
Contiene le views per la dashboard e export:
- **vendor_dashboard_view**: View principale della dashboard con statistiche e grafici
- **dashboard_stats_api**: API per recuperare statistiche aggregate
- **dashboard_vendors_list_api**: API per lista fornitori filtrata
- **export_vendors_excel**: Export fornitori in formato Excel

**Caratteristiche:**
- Decoratore `@login_required` per autenticazione Django
- Template rendering per la dashboard HTML
- Export dati in Excel con openpyxl
- Aggregazioni e statistiche per grafici

## URL Routing

Nel file `urls.py` vengono importate separatamente:
```python
from vendor_management_system.vendors.views import (
    VendorViewSet, 
    AddressViewSet, 
    CategoryViewSet,
)
from vendor_management_system.vendors.dashboard_views import (
    vendor_dashboard_view,
    dashboard_stats_api,
    dashboard_vendors_list_api,
    export_vendors_excel,
)
```

## Vantaggi di questa Separazione

1. **Chiarezza**: Chiara distinzione tra API REST e views tradizionali Django
2. **Manutenibilità**: Più facile trovare e modificare il codice corretto
3. **Testabilità**: Possibilità di testare separatamente API e dashboard
4. **Scalabilità**: Facilita l'aggiunta di nuove funzionalità mantenendo l'organizzazione

## Note

- La funzione `dashboard_redirect` è definita in `core/views.py` (non duplicata qui)
- Le view della dashboard utilizzano l'autenticazione Django standard
- Gli endpoint API utilizzano token-based authentication per integrazione con sistemi esterni
