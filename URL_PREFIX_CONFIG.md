# Configurazione URL Prefix - Sviluppo vs Produzione

## Problema Risolto

Il sistema era configurato con il path hardcoded `/fornitori` che funzionava in produzione ma non in sviluppo locale. Ora è possibile switchare facilmente tra le due modalità.

## 🔧 Configurazione

### Modalità Sviluppo (Default)
```bash
# Nel file .env
USE_FORNITORI_PREFIX=False
```

**Risultato**:
- URLs normali: `/`, `/admin/`, `/vendors/`, etc.
- STATIC_URL: `/static/`
- MEDIA_URL: `/media/`
- LOGIN_URL: `/auth/login/`

### Modalità Produzione
```bash  
# Nel file .env
USE_FORNITORI_PREFIX=True
```

**Risultato**:
- URLs con prefisso: `/fornitori/`, `/fornitori/admin/`, `/fornitori/vendors/`, etc.
- STATIC_URL: `/fornitori/static/`
- MEDIA_URL: `/fornitori/media/`
- LOGIN_URL: `/fornitori/auth/login/`

## 🚀 Come Utilizzare

### Per Sviluppo Locale
1. Assicurati che nel tuo `.env` sia impostato:
   ```bash
   USE_FORNITORI_PREFIX=False
   ```

2. Avvia il server di sviluppo:
   ```bash
   python manage.py runserver
   ```

3. Accedi a: `http://localhost:8000/`

### Per Produzione
1. Nel tuo `.env` di produzione imposta:
   ```bash
   USE_FORNITORI_PREFIX=True
   ```

2. Configura il web server (Apache/Nginx) per gestire il prefisso `/fornitori`

3. **Esempio Apache**:
   ```apache
   ProxyPass /fornitori/ http://localhost:8000/
   ProxyPassReverse /fornitori/ http://localhost:8000/
   ```

4. **Esempio Nginx**:
   ```nginx
   location /fornitori/ {
       proxy_pass http://localhost:8000/;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

## 🧪 Test Configurazione

Per verificare che tutto sia configurato correttamente:

```bash
python manage.py test_url_config
```

Output atteso in **sviluppo**:
```
🚀 Modalità SVILUPPO attiva
   - Gli URL useranno la root /
   - Perfetto per il runserver di Django
```

Output atteso in **produzione**:
```
🔧 Modalità PRODUZIONE attiva
   - Gli URL useranno il prefisso /fornitori
   - Configura il web server per gestire il prefisso
```

## 📝 File Modificati

### 1. `config/settings.py`
- Aggiunta variabile `USE_FORNITORI_PREFIX`
- URL condizionali per STATIC_URL, MEDIA_URL, LOGIN_URL, etc.

### 2. `config/wsgi.py`
- Middleware `PrefixMiddleware` reso condizionale
- Applica prefisso solo quando necessario

### 3. `.env`
- Aggiunta variabile `USE_FORNITORI_PREFIX=False` per sviluppo

## 🔄 Switching tra Modalità

### Da Sviluppo a Produzione
```bash
# Modifica .env
USE_FORNITORI_PREFIX=True

# Riavvia il server
# Gli URL cambieranno automaticamente
```

### Da Produzione a Sviluppo
```bash
# Modifica .env  
USE_FORNITORI_PREFIX=False

# Riavvia il server
# Gli URL torneranno normali
```

## ⚠️ Note Importanti

1. **Riavvio Necessario**: Dopo aver cambiato `USE_FORNITORI_PREFIX`, è necessario riavviare l'applicazione.

2. **Web Server**: In produzione, assicurati che il web server sia configurato per gestire il prefisso `/fornitori`.

3. **Database**: La configurazione del database non cambia tra le modalità.

4. **Static Files**: In produzione, assicurati che i file statici siano serviti correttamente sotto `/fornitori/static/`.

## 🐛 Troubleshooting

### Problema: 404 su /fornitori in sviluppo
**Soluzione**: Verifica che `USE_FORNITORI_PREFIX=False` nel file `.env`

### Problema: Link rotti in produzione
**Soluzione**: Verifica che `USE_FORNITORI_PREFIX=True` e che il web server sia configurato correttamente

### Problema: CSS/JS non caricano
**Soluzione**: Controlla che STATIC_URL sia configurato correttamente e che i file statici siano serviti dal web server

## 📋 Checklist Deploy

### Sviluppo
- [ ] `USE_FORNITORI_PREFIX=False` nel `.env`
- [ ] Test con `python manage.py test_url_config`
- [ ] Verifica che `http://localhost:8000/` funzioni

### Produzione  
- [ ] `USE_FORNITORI_PREFIX=True` nel `.env`
- [ ] Configurazione web server per `/fornitori`
- [ ] Test con `python manage.py test_url_config` 
- [ ] Verifica che `https://tuodominio.com/fornitori/` funzioni