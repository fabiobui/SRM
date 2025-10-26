# Correzione Link Assoluti per Sotto-URL `/fornitori`

## Problema
I template del sistema avevano link assoluti hardcoded (come `/documents/portal/`, `/admin/`, etc.) che non funzionano quando l'applicazione viene servita sotto un sotto-URL come `/fornitori`.

## Modifiche Effettuate

### 1. Template HTML - Sostituzione link assoluti con tag Django `{% url %}`

#### `/vendor_management_system/documents/templates/documents/vendor_portal.html`
- ✅ `href="/documents/portal/"` → `href="{% url 'vendor-portal' %}"`
- ✅ `href="/documents/upload/"` → `href="{% url 'document-upload' %}"`
- ✅ `href="/auth/logout/"` → `href="{% url 'logout' %}"`
- ✅ `href="/admin/vendors/vendor/add/"` → `href="{% url 'admin:vendors_vendor_add' %}"`
- ✅ `href="/admin/documents/documenttype/add/"` → `href="{% url 'admin:documents_documenttype_add' %}"`

#### `/vendor_management_system/documents/templates/documents/admin_dashboard.html`
- ✅ `href="/"` → `href="{% url 'home' %}"`
- ✅ `href="/admin/"` → `href="{% url 'admin:index' %}"`
- ✅ `href="/documents/portal/"` → `href="{% url 'vendor-portal' %}"`

#### `/vendor_management_system/documents/templates/documents/backoffice_dashboard.html`
- ✅ `href="/"` → `href="{% url 'home' %}"`
- ✅ `href="/documents/backoffice/"` → `href="{% url 'backoffice-dashboard' %}"`
- ✅ `href="/documents/admin/"` → `href="{% url 'admin-dashboard' %}"`
- ✅ `href="/admin/"` → `href="{% url 'admin:index' %}"`
- ✅ `href="/documents/portal/"` → `href="{% url 'vendor-portal' %}"`
- ✅ `href="/auth/logout/"` → `href="{% url 'logout' %}"`

### 2. Viste Python - Sostituzione URL hardcoded nelle HttpResponse

#### `/config/urls.py` - Funzione `home_view()`
- ✅ Aggiunto `from django.urls import reverse`
- ✅ `href="/admin/"` → `href="{admin_url}"` usando `reverse('admin:index')`
- ✅ `href="/swagger/"` → `href="{swagger_url}"` usando `reverse('schema-swagger-ui')`

#### `/vendor_management_system/vendors/views.py` - Funzione `dashboard_redirect()`
- ✅ Aggiunto `from django.urls import reverse`
- ✅ `href="/admin/logout/"` → `href="{logout_url}"` usando `reverse('admin:logout')`

#### `/vendor_management_system/core/views.py` - Funzione di fallback
- ✅ Aggiunto `from django.urls import reverse`
- ✅ `href="/admin/logout/"` → `href="{logout_url}"` usando `reverse('admin:logout')`
- ✅ `href="/admin/"` → `href="{admin_url}"` usando `reverse('admin:index')`

### 3. Configurazione Django per Sotto-URL

Il file `config/settings.py` era già configurato correttamente:

```python
# Forza Django a considerare /fornitori come base URL
FORCE_SCRIPT_NAME = '/fornitori'

# URL per risorse statiche
STATIC_URL = "/fornitori/static/"
MEDIA_URL = "/fornitori/media/"

# URL di autenticazione
LOGIN_URL = '/fornitori/auth/login/'
LOGIN_REDIRECT_URL = '/fornitori'
LOGOUT_REDIRECT_URL = '/fornitori/auth/login/'

# Middleware per gestire i redirect
MIDDLEWARE = [
    # ...
    "vendor_management_system.core.middleware.force_prefix.ForcePrefixMiddleware",
    # ...
]
```

## Vantaggi delle Modifiche

1. **Compatibilità Sotto-URL**: L'applicazione ora funziona correttamente quando servita sotto `/fornitori`
2. **Flessibilità**: Se in futuro dovessi cambiare il sotto-URL, basta modificare solo `FORCE_SCRIPT_NAME`
3. **Manutenibilità**: I link sono generati dinamicamente da Django, non più hardcoded
4. **Standard Django**: Uso delle best practice Django con `{% url %}` e `reverse()`

## Test

Per testare che tutto funzioni correttamente:

1. **Test Locale**: Avvia il server Django e verifica che tutti i link funzionino
2. **Test Produzione**: Configura il web server (Apache/Nginx) per servire l'app sotto `/fornitori`
3. **Test URL**: Esegui lo script `test_urls.py` per verificare la generazione degli URL

## Configurazione Web Server

### Apache
```apache
ProxyPass /fornitori/ http://localhost:8000/
ProxyPassReverse /fornitori/ http://localhost:8000/
ProxyPreserveHost On
```

### Nginx
```nginx
location /fornitori/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## File Modificati

- `/vendor_management_system/documents/templates/documents/vendor_portal.html`
- `/vendor_management_system/documents/templates/documents/admin_dashboard.html`
- `/vendor_management_system/documents/templates/documents/backoffice_dashboard.html`
- `/config/urls.py`
- `/vendor_management_system/vendors/views.py`
- `/vendor_management_system/core/views.py`
- `/test_urls.py` (nuovo file di test)

## Note
- Il template `/vendor_management_system/templates/auth/login.html` non richiedeva modifiche
- Il middleware `ForcePrefixMiddleware` era già configurato correttamente
- Le configurazioni di base in `settings.py` erano già a posto