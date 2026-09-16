# Configurazione del Prefisso URL (`/fornitori`)

> Consolida quelli che un tempo erano due file separati nella root (`URL_PREFIX_CONFIG.md`, `CORREZIONE_URL.md`).

## Perché esiste

In produzione l'app viene servita sotto un sotto-percorso `/fornitori` (es.
`https://spoc.fulgard.com/fornitori/`) invece che sulla root del dominio. In locale, dovrebbe comportarsi come
una normale app Django su `/`. Un'unica impostazione permette di passare dall'una all'altra: `USE_FORNITORI_PREFIX`.

```python
# config/settings.py
USE_FORNITORI_PREFIX = os.getenv("USE_FORNITORI_PREFIX", "False") == "True"
FORCE_SCRIPT_NAME = "/fornitori" if USE_FORNITORI_PREFIX else None
```

| | `USE_FORNITORI_PREFIX=False` (dev, default) | `USE_FORNITORI_PREFIX=True` (prod) |
|---|---|---|
| URL | `/`, `/admin/`, `/vendors/`, ... | `/fornitori/`, `/fornitori/admin/`, `/fornitori/vendors/`, ... |
| `STATIC_URL` | `/static/` | `/fornitori/static/` |
| `MEDIA_URL` | `/media/` | `/fornitori/media/` |
| `LOGIN_URL` | `/auth/login/` | `/fornitori/auth/login/` |

Quando è `True`, in `MIDDLEWARE` viene inserito anche
`vendor_management_system.core.middleware.force_prefix.ForcePrefixMiddleware` subito dopo `CommonMiddleware`, per
gestire i redirect consapevoli del prefisso.

**Tutti i template e le view generano gli URL tramite il tag `{% url %}` di Django / `reverse()`** — non restano
percorsi assoluti hardcoded nel codice (es. `href="/admin/"`); è proprio questo che rende il cambio di prefisso
una singola modifica a una variabile d'ambiente invece di una modifica template per template.

## Utilizzo

**Sviluppo locale**: `USE_FORNITORI_PREFIX=False` (già il default in `.envs/.django.env`), poi
`http://localhost:8000/`.

**Produzione**: `USE_FORNITORI_PREFIX=True`, e il web server davanti a Django deve instradare il prefisso
`/fornitori`. Confermato sulla VM di produzione: **Apache + `mod_wsgi`**, usando `DJANGO_SCRIPT_NAME=/fornitori`
(mod_wsgi integra l'app direttamente in Apache — non c'è un salto separato via reverse-proxy). Se invece stai
mettendo l'app dietro un classico reverse proxy (es. per un ambiente diverso), la configurazione equivalente è:

**Apache (`ProxyPass`)**:
```apache
ProxyPass /fornitori/ http://localhost:8000/
ProxyPassReverse /fornitori/ http://localhost:8000/
ProxyPreserveHost On
```

**Nginx**:
```nginx
location /fornitori/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Verificare la configurazione

```bash
python manage.py test_url_config
```

Output atteso in sviluppo (`USE_FORNITORI_PREFIX=False`):
```
🚀 Modalità SVILUPPO attiva
   - Gli URL useranno la root /
   - Perfetto per il runserver di Django
```

Output atteso in modalità prod-like (`USE_FORNITORI_PREFIX=True`):
```
🔧 Modalità PRODUZIONE attiva
   - Gli URL useranno il prefisso /fornitori
   - Configura il web server per gestire il prefisso
```

C'è anche `tests/test_urls.py`, un test pytest che verifica la generazione degli URL principali senza bisogno
di un server in esecuzione (fa parte della suite eseguita con `pytest`).

## Risoluzione problemi

| Sintomo | Causa | Soluzione |
|---|---|---|
| 404 su `/fornitori/...` in locale | `USE_FORNITORI_PREFIX=True` impostato in locale | Impostalo su `False` per lo sviluppo locale |
| Link rotti in produzione | `USE_FORNITORI_PREFIX=False`, oppure il web server non instrada `/fornitori` | Impostalo su `True`; verifica la configurazione di Apache/mod_wsgi o del reverse-proxy |
| CSS/JS non si caricano | `STATIC_URL` non coerente con come i file statici vengono effettivamente serviti | Verifica `STATIC_URL`/`STATIC_ROOT` e che il web server serva quel percorso |
| Riavvio necessario dopo aver cambiato l'impostazione | `USE_FORNITORI_PREFIX` viene letto una sola volta all'avvio del processo | Riavvia il processo Django (dev server / mod_wsgi / gunicorn) dopo averlo cambiato |
