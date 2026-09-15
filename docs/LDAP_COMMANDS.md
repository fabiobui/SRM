# Comandi di Test LDAP

Comandi Django per verificare la connessione e l'autenticazione LDAP nel sistema SRM/VMS.

## Prerequisiti

- Pacchetto `ldap3` installato (`pip install ldap3`)
- Variabili d'ambiente LDAP configurate nel `.env` (o passate via argomenti)

### Variabili d'ambiente rilevanti

| Variabile | Descrizione | Default |
|---|---|---|
| `LDAP_ENABLED` | Abilita autenticazione LDAP | `False` |
| `LDAP_SERVER` / `LDAP_SERVER_URI` | Host o URI del server LDAP | — |
| `LDAP_PORT` | Porta LDAP | `389` / `636` (SSL) |
| `LDAP_USE_SSL` / `USE_SSL` | Usa LDAPS | `False` |
| `LDAP_BIND_DN` / `LDAP_USER` | DN account di servizio | — |
| `LDAP_BIND_PASSWORD` / `LDAP_PASSWORD` | Password account di servizio | — |
| `LDAP_USER_BASE_DN` | Base DN per ricerca utenti | `ou=users,dc=example,dc=com` |
| `LDAP_TLS_VALIDATE` | Valida certificato TLS | `True` |

---

## 1. `test_ldap_connection` — Test connessione LDAP

Verifica la raggiungibilità del server, il bind con l'account di servizio e (opzionalmente) esegue una ricerca di base.

### Uso

```bash
python manage.py test_ldap_connection
```

### Opzioni

| Argomento | Descrizione |
|---|---|
| `--server-uri URI` | Override dell'URI del server LDAP |
| `--bind-dn DN` | Override del Bind DN di servizio |
| `--bind-password PWD` | Override della password di servizio |
| `--search-base DN` | Override della base DN per la ricerca di test |
| `--no-search` | Salta la ricerca di test (esegue solo il bind) |
| `--timeout N` | Timeout connessione in secondi (default: 10) |

### Esempio

```bash
# Usa la configurazione dal .env
python manage.py test_ldap_connection

# Con parametri espliciti
python manage.py test_ldap_connection \
    --server-uri ldaps://dc01.sicura.loc:636 \
    --bind-dn "CN=svc_vms,OU=ServiceAccounts,DC=sicura,DC=loc" \
    --bind-password "s3cret" \
    --search-base "DC=sicura,DC=loc"

# Solo test bind, senza ricerca
python manage.py test_ldap_connection --no-search
```

### Output atteso (successo)

```
=== Test connessione LDAP ===
  Server URI   : ldaps://dc01.sicura.loc:636
  Bind DN      : CN=svc_vms,OU=ServiceAccounts,DC=sicura,DC=loc
  Search Base  : DC=sicura,DC=loc
  Timeout      : 10s

1) Connessione al server LDAP...
   OK - Server raggiungibile
2) Bind con account di servizio...
   OK - Bind riuscito (0.12s)
3) Informazioni server:
   Naming Context: DC=sicura,DC=loc
4) Ricerca di test su 'DC=sicura,DC=loc'...
   OK - 5 entry trovate (limit 5)
   - OU=Users,DC=sicura,DC=loc
   - OU=Groups,DC=sicura,DC=loc
   ...

=== Connessione LDAP OK ===
```

---

## 2. `test_ldap_auth` — Test autenticazione utente

Esegue il flusso completo di autenticazione: bind di servizio → ricerca utente → bind con le credenziali dell'utente. Utile per verificare che un utente specifico possa effettuare il login.

### Uso

```bash
python manage.py test_ldap_auth <username>
```

La password viene chiesta interattivamente se non fornita via `--password`.

### Opzioni

| Argomento | Descrizione |
|---|---|
| `username` | **(obbligatorio)** Email/UPN dell'utente |
| `--password PWD` | Password utente (se omessa, viene chiesta da stdin) |
| `--server-uri URI` | Override dell'URI del server LDAP |
| `--bind-dn DN` | Override del Bind DN di servizio |
| `--bind-password PWD` | Override della password di servizio |
| `--search-base DN` | Override della base DN per la ricerca |
| `--search-filter FILTRO` | Filtro LDAP custom. Usa `{username}` come placeholder (default: `(userPrincipalName={username})`) |
| `--timeout N` | Timeout connessione in secondi (default: 10) |
| `--show-attrs` | Mostra tutti gli attributi LDAP dell'utente |

### Esempi

```bash
# Test autenticazione (password chiesta interattivamente)
python manage.py test_ldap_auth mario.rossi@sicura.loc

# Con password inline (utile per script/CI)
python manage.py test_ldap_auth mario.rossi@sicura.loc --password "MyP@ss"

# Mostra attributi completi dell'utente
python manage.py test_ldap_auth mario.rossi@sicura.loc --show-attrs

# Filtro di ricerca personalizzato (es. per sAMAccountName)
python manage.py test_ldap_auth mario.rossi \
    --search-filter "(sAMAccountName={username})"
```

### Output atteso (successo)

```
=== Test autenticazione LDAP ===
  Server URI   : ldaps://dc01.sicura.loc:636
  Bind DN      : CN=svc_vms,OU=ServiceAccounts,DC=sicura,DC=loc
  Search Base  : DC=sicura,DC=loc
  Username     : mario.rossi@sicura.loc

1) Bind con account di servizio...
   OK
2) Ricerca utente con filtro: (userPrincipalName=mario.rossi@sicura.loc)
   OK - Utente trovato: CN=Mario Rossi,OU=Users,DC=sicura,DC=loc
   Attributi:
     displayName: Mario Rossi
     mail: mario.rossi@sicura.loc
     memberOf: CN=vms_backoffice,OU=Groups,DC=sicura,DC=loc

3) Autenticazione con credenziali utente...
   Tentativo DN completo: CN=Mario Rossi,OU=Users,DC=sicura,DC=loc
   OK - Autenticazione riuscita con DN completo (0.08s)

=== Autenticazione LDAP riuscita ===
```

---

## 3. `sync_ldap_users` — Creazione/aggiornamento utenti LDAP

Comando preesistente per creare o aggiornare un utente LDAP nel database Django.

```bash
python manage.py sync_ldap_users --create-ldap-user mario.rossi@sicura.loc --role bo_user --name "Mario Rossi"

# Dry run
python manage.py sync_ldap_users --create-ldap-user mario.rossi@sicura.loc --role vendor --vendor-code V001 --dry-run
```

---

## Troubleshooting

| Errore | Causa probabile | Soluzione |
|---|---|---|
| `Impossibile connettersi al server` | Server non raggiungibile, porta bloccata, DNS errato | Verificare URI, firewall, DNS |
| `Bind di servizio fallito` | Credenziali account di servizio errate | Controllare `LDAP_BIND_DN` e `LDAP_BIND_PASSWORD` |
| `Utente non trovato` | Search base o filtro errati | Verificare `LDAP_USER_BASE_DN` e provare con `--search-filter` |
| `Autenticazione fallita con tutti i formati` | Password errata o account bloccato | Verificare password, controllare stato account in AD |
| `CERT_NONE / certificato` | Certificato TLS non valido | Impostare `LDAP_TLS_VALIDATE=False` per test, risolvere il certificato in produzione |
