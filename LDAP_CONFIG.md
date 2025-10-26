# Configurazione LDAP - Guida rapida

## Come ho configurato LDAP

Ho aggiornato la tua configurazione LDAP per utilizzare il server `172.16.1.90:636` con le credenziali fornite:

### File modificati:
- **`.env`** - Aggiunte variabili LDAP specifiche per il tuo server
- **`config/settings.py`** - Aggiornata sezione LDAP per supportare le nuove variabili
- **`vendor_management_system/core/management/commands/test_ldap.py`** - Migliorato comando di test

### Variabili LDAP configurate in `.env`:

```bash
# LDAP abilitato
LDAP_ENABLED=True

# Server e porta
LDAP_SERVER=172.16.1.90
LDAP_PORT=636

# Credenziali di bind (account di servizio)
LDAP_USER=spoc@sicura.loc
LDAP_PASSWORD=Gz8#kV!3pT@q9Xw$M1

# SSL/TLS
USE_SSL=True
LDAP_TLS_VALIDATE=False  # Solo per test - in produzione mettere True

# Base DN (da configurare secondo la tua AD)
LDAP_USER_BASE_DN=OU=Users,DC=sicura,DC=loc
LDAP_GROUP_BASE_DN=OU=Groups,DC=sicura,DC=loc
```

## Test della configurazione

### Comando base
```bash
python manage.py test_ldap
```

### Test con autenticazione utente
```bash
python manage.py test_ldap --test-user user@sicura.loc --password password123
```

### Listing utenti e gruppi
```bash
python manage.py test_ldap --list-users --list-groups
```

## ⚠️ SICUREZZA - IMPORTANTE

### 1. File `.env` e credenziali
- **MAI commitare il file `.env` in git** (è già in `.gitignore`)
- Le password in `.env` sono in chiaro - proteggere il file con permessi appropriati:
  ```bash
  chmod 600 .env
  ```

### 2. Validazione certificati TLS
- Attualmente `LDAP_TLS_VALIDATE=False` per test
- **In produzione**: impostare `LDAP_TLS_VALIDATE=True` e:
  - Installare certificati CA appropriati sul server
  - O usare certificati SSL validi sul server LDAP
  - O configurare correttamente la trust chain

### 3. Account di servizio LDAP
- `spoc@sicura.loc` è l'account usato per il bind
- Dovrebbe avere **permessi minimi** necessari:
  - Solo lettura sulla directory
  - Accesso agli attributi utente necessari
  - Nessun permesso di scrittura a meno che strettamente necessario

### 4. Firewall e rete
- La porta 636 (LDAPS) deve essere aperta tra il server Django e il server LDAP
- Considerare l'uso di VPN o connessioni private per il traffico LDAP

## Configurazioni da completare

### Base DN da verificare
I Base DN potrebbero dover essere adattati alla struttura della tua Active Directory:

```bash
# Esempi comuni per Active Directory:
LDAP_USER_BASE_DN=CN=Users,DC=sicura,DC=loc
LDAP_GROUP_BASE_DN=CN=Groups,DC=sicura,DC=loc

# O per OU organizzative:
LDAP_USER_BASE_DN=OU=Dipendenti,OU=Users,DC=sicura,DC=loc
```

### Filtro di ricerca utenti
Attualmente usa `(userPrincipalName=%(user)s)`. Potrebbe essere necessario cambiarlo:

```bash
# Per sAMAccountName invece di UPN:
LDAP_USER_FILTER=(sAMAccountName=%(user)s)

# Per email:
LDAP_USER_FILTER=(mail=%(user)s)
```

## Troubleshooting comune

### Errore "Connection reset by peer"
- Verifica che la porta 636 sia raggiungibile
- Controlla se il server richiede StartTLS invece di LDAPS
- Prova a impostare `LDAP_TLS_VALIDATE=True` se hai i certificati

### Errore "Invalid credentials"
- Verifica username e password dell'account di servizio
- Controlla il formato del Bind DN (potrebbe essere `CN=spoc,OU=Service Accounts,DC=sicura,DC=loc`)

### Utenti non trovati
- Verifica il `LDAP_USER_BASE_DN`
- Controlla il `LDAP_USER_FILTER`
- Usa `--list-users` per vedere cosa trova il sistema

## Backup configurazione precedente

Le configurazioni precedenti sono state mantenute in `.env` come commenti per riferimento futuro.

---

**Per ulteriori modifiche alla configurazione LDAP, modifica solo il file `.env` e riavvia l'applicazione.**