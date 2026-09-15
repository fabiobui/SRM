# Autenticazione LDAP / Active Directory

> Consolida quelli che un tempo erano tre file separati (`LDAP_CONFIG.md`, `LDAP_USER_ADMIN.md` nella root del
> repo, e `docs/LDAP_COMMANDS.md`) in un unico riferimento. Vedi
> [PROJECT_OVERVIEW_AND_LOCAL_SETUP.md](PROJECT_OVERVIEW_AND_LOCAL_SETUP.md) per come LDAP si inserisce nel setup
> locale (è disabilitato di default in locale).

## Come funziona

L'autenticazione è gestita da un backend ibrido custom, `vendor_management_system.core.simple_ldap_backend.HybridAuthBackend`,
che prova prima LDAP (via `ldap3`) e poi ricade sul `ModelBackend` nativo di Django. È controllato da
`LDAP_ENABLED` — quando è `False` (il default locale), LDAP viene saltato del tutto e funzionano solo gli account
Django locali.

Gli utenti LDAP ottengono una password Django inutilizzabile, vengono ri-sincronizzati da LDAP a ogni login
(`AUTH_LDAP_ALWAYS_UPDATE_USER`), e l'appartenenza ai gruppi AD viene mappata su un ruolo applicativo tramite
`LDAP_GROUP_ROLE_MAPPING`:

```python
LDAP_GROUP_ROLE_MAPPING = {
    'vms_administrators': 'admin',
    'vms_backoffice': 'bo_user',
    'vms_vendors': 'vendor',
}
```

> Nota per il manutentore: `config/settings.py` costruisce anche `AUTH_LDAP_USER_SEARCH`/`AUTH_LDAP_GROUP_SEARCH`
> tramite `django_auth_ldap.config.LDAPSearch` (servono `python-ldap`/`django-auth-ldap` solo per soddisfare
> l'import) — ma `AUTHENTICATION_BACKENDS` punta in realtà a `HybridAuthBackend`, che usa `ldap3` direttamente e
> non tocca mai quegli oggetti. Quella configurazione LDAPSearch è codice morto; vale un intervento di pulizia
> indipendente da questo documento.

## Configurazione

Tutte le impostazioni LDAP sono variabili d'ambiente, lette in `config/settings.py`. Impostale nel tuo `.env`
(nativo) o in `.envs/.django.env` (Docker) — **non committare mai credenziali reali**; i valori sotto sono
segnaposto.

| Variabile | Scopo | Default |
|---|---|---|
| `LDAP_ENABLED` | Interruttore generale on/off | `False` |
| `LDAP_SERVER` / `LDAP_PORT` | Host/porta del server LDAP (alternativa a `LDAP_SERVER_URI`) | — |
| `LDAP_SERVER_URI` | URI completo, es. `ldaps://dc01.example.com:636` | costruito da `LDAP_SERVER`/`LDAP_PORT` se impostati, altrimenti `ldap://ldap.example.com` |
| `USE_SSL` / `LDAP_USE_SSL` | Usa LDAPS (porta 636) | `False` |
| `LDAP_START_TLS` | Usa StartTLS invece di LDAPS | `False` |
| `LDAP_TLS_VALIDATE` | Valida il certificato TLS del server | `True` (imposta `False` solo per test locali contro un server con certificato self-signed) |
| `LDAP_BIND_DN` / `LDAP_USER` | DN (o UPN) dell'account di servizio/bind | — |
| `LDAP_BIND_PASSWORD` / `LDAP_PASSWORD` | Password dell'account di servizio/bind | — |
| `LDAP_USER_BASE_DN` | Base DN per la ricerca utenti | `ou=users,dc=example,dc=com` |
| `LDAP_GROUP_BASE_DN` | Base DN per la ricerca gruppi | `ou=groups,dc=example,dc=com` |
| `LDAP_USER_FILTER` | Filtro di ricerca per lo username | `(mail=%(user)s)` — le installazioni Active Directory tipicamente usano invece `(userPrincipalName=%(user)s)` o `(sAMAccountName=%(user)s)` |

**Sviluppo locale**: lascia `LDAP_ENABLED=False` (il default in `.envs/.django.env` del repo) — non serve
nessun'altra configurazione LDAP per far girare l'app in locale.

**Note di sicurezza per chi configura una connessione LDAP/AD reale:**
- Non committare mai su git la password reale dell'account di bind, l'IP/hostname del server, o le base DN —
  tienile solo in `.env`/`.envs/` (già in gitignore) e da nessun'altra parte.
- L'account di bind/servizio dovrebbe avere accesso **di sola lettura** alla directory — nessun permesso di
  scrittura.
- In produzione, mantieni `LDAP_TLS_VALIDATE=True` e installa i certificati CA corretti; rilassa questa
  impostazione solo per test locali contro un server con certificato self-signed.
- La porta LDAP (tipicamente 636 per LDAPS) deve essere raggiungibile da dove gira Django — configura il
  firewall di conseguenza.

## Testare la configurazione

### `test_ldap_connection` — connettività + bind

Verifica che il server sia raggiungibile, che l'account di bind si autentichi e (opzionalmente) esegue una
ricerca di test.

```bash
python manage.py test_ldap_connection
python manage.py test_ldap_connection --no-search          # solo bind, salta la ricerca
python manage.py test_ldap_connection \
    --server-uri ldaps://dc01.example.com:636 \
    --bind-dn "CN=svc_vms,OU=ServiceAccounts,DC=example,DC=com" \
    --bind-password "..." \
    --search-base "DC=example,DC=com"
```

| Opzione | Descrizione |
|---|---|
| `--server-uri URI` | Sovrascrive l'URI del server LDAP |
| `--bind-dn DN` | Sovrascrive il bind DN di servizio |
| `--bind-password PWD` | Sovrascrive la password di bind di servizio |
| `--search-base DN` | Sovrascrive la base DN della ricerca di test |
| `--no-search` | Solo bind, salta la ricerca di test |
| `--timeout N` | Timeout di connessione in secondi (default 10) |

### `test_ldap_auth` — flusso completo di autenticazione utente

Esegue il flusso completo: bind di servizio → ricerca utente → bind con le credenziali dell'utente. Utile per
verificare che un utente specifico possa effettivamente effettuare il login.

```bash
python manage.py test_ldap_auth mario.rossi@example.com          # password richiesta interattivamente
python manage.py test_ldap_auth mario.rossi@example.com --password "..." --show-attrs
python manage.py test_ldap_auth mario.rossi --search-filter "(sAMAccountName={username})"
```

| Opzione | Descrizione |
|---|---|
| `username` | **(obbligatorio)** Email/UPN dell'utente da testare |
| `--password PWD` | Password utente (richiesta da stdin se omessa) |
| `--server-uri` / `--bind-dn` / `--bind-password` / `--search-base` | Stesse override di `test_ldap_connection` |
| `--search-filter FILTER` | Filtro LDAP custom, `{username}` come segnaposto (default `(userPrincipalName={username})`) |
| `--timeout N` | Timeout di connessione in secondi (default 10) |
| `--show-attrs` | Stampa tutti gli attributi LDAP restituiti per l'utente |

## Gestire gli utenti LDAP

### Django Admin UI

L'admin di `users` (`/admin/`, sezione "Users") supporta sia utenti locali che LDAP dallo stesso form "Add User":
1. Apri **Add User**.
2. Imposta **Tipo Utente** su "Utente LDAP" — i campi password si nascondono automaticamente (gli utenti LDAP si
   autenticano contro la directory, non con una password locale).
3. Compila **Email** (deve esistere in LDAP), **Nome**, **Ruolo**, e (solo per il ruolo `vendor`) il
   **Fornitore** collegato.
4. Salva. Gli utenti LDAP ottengono una password locale inutilizzabile e vengono ri-sincronizzati da LDAP a ogni
   login successivo.

Modificare un utente LDAP esistente: email/nome potrebbero essere di sola lettura (provengono dalla directory);
ruolo, associazione fornitore e permessi restano modificabili localmente.

### `sync_ldap_users` — gestione utenti da riga di comando

```bash
# Testa la connettività
python manage.py sync_ldap_users --test-ldap-connection

# Elenca gli utenti LDAP disponibili per l'import
python manage.py sync_ldap_users --list-ldap-users

# Crea/aggiorna un singolo utente senza richiedergli di autenticarsi prima
python manage.py sync_ldap_users --create-ldap-user mario.rossi@example.com --role bo_user --name "Mario Rossi"
python manage.py sync_ldap_users --create-ldap-user fornitore@example.com --role vendor --vendor-code ABC123
python manage.py sync_ldap_users --create-ldap-user admin@example.com --role admin --dry-run

# Ri-sincronizza gli utenti già presenti localmente con i dati LDAP correnti
python manage.py sync_ldap_users --sync-existing
```

| Opzione | Descrizione |
|---|---|
| `--create-ldap-user EMAIL` | Crea o aggiorna questo utente senza autenticarlo |
| `--role` | Ruolo da assegnare: `admin` \| `bo_user` \| `vendor` (default `bo_user`) |
| `--name` | Nome visualizzato (derivato dalla parte locale dell'email se omesso) |
| `--vendor-code` | Obbligatorio con `--role vendor` — deve essere un codice fornitore esistente |
| `--dry-run` | Mostra cosa succederebbe senza salvare |
| `--test-ldap-connection` | Verifica solo la connettività |
| `--list-ldap-users` | Elenca gli utenti visibili nella directory |
| `--sync-existing` | Ri-sincronizza gli utenti già locali con i dati LDAP correnti |

## Risoluzione problemi

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| `Impossibile connettersi al server` / connection reset | Server non raggiungibile, porta bloccata, DNS errato | Verifica `LDAP_SERVER_URI`, firewall, DNS |
| `Bind di servizio fallito` | Credenziali account di servizio errate | Verifica `LDAP_BIND_DN`/`LDAP_USER` e `LDAP_BIND_PASSWORD`/`LDAP_PASSWORD` |
| Bind OK ma utente non trovato | Base DN o filtro errati | Verifica `LDAP_USER_BASE_DN`, prova con `--search-filter` esplicito |
| Autenticazione fallita per un utente reale | Password errata, o account bloccato in AD | Verifica le credenziali e lo stato dell'account direttamente in AD |
| Errori di certificato (`CERT_NONE`, ecc.) | Certificato TLS non valido/self-signed | `LDAP_TLS_VALIDATE=False` solo per test locali; risolvi la catena di certificati per la produzione |
| I campi password restano visibili per un utente LDAP nell'admin | JS/CSS per il form dinamico dell'admin non caricati | Verifica che `staticfiles/admin/js/ldap_user_admin.js` e `.../ldap_user_admin.css` vengano serviti; controlla la console del browser |
| Ruoli errati assegnati dopo il login LDAP | L'appartenenza ai gruppi AD non corrisponde a `LDAP_GROUP_ROLE_MAPPING` | Verifica che i nomi dei gruppi AD dell'utente corrispondano alla mappatura in `config/settings.py` |
