# Gestione Utenti LDAP nell'Admin Django

Questo documento descrive come utilizzare la nuova funzionalità per creare e gestire utenti LDAP attraverso l'interfaccia di amministrazione Django.

## Funzionalità Implementate

### 1. Creazione Utenti dall'Admin
- **Utenti Locali**: Utilizzano l'autenticazione Django tradizionale
- **Utenti LDAP**: Autenticati tramite il server LDAP configurato

### 2. Interfaccia Migliorata
- Selezione dinamica del tipo di utente (Locale/LDAP)
- Campi password nascosti automaticamente per utenti LDAP
- Validazione intelligente dei campi obbligatori
- Interfaccia responsive con JavaScript

### 3. Gestione Ruoli
- **Amministratore**: Accesso completo al sistema
- **Utente Back Office**: Gestione vendor e documenti
- **Fornitore**: Accesso limitato alle proprie informazioni

## Come Utilizzare

### Creare un Nuovo Utente LDAP

1. **Accedi all'Admin Django**: `/admin/`
2. **Vai a Utenti**: Clicca su "Users" nella sezione "USERS"
3. **Aggiungi Utente**: Clicca su "Add User"
4. **Compila il Form**:
   - **Email**: Inserisci l'email dell'utente (deve esistere in LDAP)
   - **Nome**: Inserisci il nome completo
   - **Tipo Utente**: Seleziona "Utente LDAP"
   - **Ruolo**: Scegli il ruolo appropriato
   - **Fornitore**: Solo per utenti con ruolo "Fornitore"

> **Nota**: I campi password sono nascosti automaticamente per utenti LDAP

### Modificare un Utente Esistente

1. **Trova l'Utente**: Nella lista utenti, clicca sull'utente da modificare
2. **Modifica i Campi**: 
   - Per utenti LDAP, email e nome potrebbero essere di sola lettura
   - Puoi modificare ruolo, associazione vendor, e permessi
3. **Salva**: Le modifiche saranno applicate immediatamente

## Comandi di Gestione

### Testare la Connessione LDAP
```bash
python manage.py sync_ldap_users --test-ldap-connection
```

### Elencare Utenti LDAP Disponibili
```bash
python manage.py sync_ldap_users --list-ldap-users
```

### Creare Utente LDAP da Riga di Comando
```bash
python manage.py sync_ldap_users --create-ldap-user email@esempio.com --role bo_user
```

### Sincronizzare Utenti LDAP Esistenti
```bash
python manage.py sync_ldap_users --sync-existing
```

### Testare Autenticazione Specifica
```bash
python manage.py test_ldap_auth email@esempio.com password123 --verbose
```

## Configurazione LDAP

Assicurati che le seguenti variabili d'ambiente siano configurate:

```bash
# Server LDAP
LDAP_SERVER=ldap.esempio.com
LDAP_PORT=389
LDAP_USE_SSL=False
LDAP_ENABLED=True

# Credenziali di Bind
LDAP_BIND_DN=cn=admin,dc=esempio,dc=com
LDAP_BIND_PASSWORD=password_admin

# Base DN per ricerche
LDAP_USER_BASE_DN=ou=users,dc=esempio,dc=com
LDAP_GROUP_BASE_DN=ou=groups,dc=esempio,dc=com

# Filtro per ricerca utenti
LDAP_USER_FILTER=(mail=%(user)s)
```

## Mappatura Gruppi LDAP

I gruppi LDAP vengono mappati automaticamente sui ruoli:

```python
LDAP_GROUP_ROLE_MAPPING = {
    'vms_administrators': 'admin',
    'vms_backoffice': 'bo_user', 
    'vms_vendors': 'vendor',
}
```

## Risoluzione Problemi

### Problema: Utente LDAP non si autentica
**Soluzioni**:
1. Verifica che l'utente esista in LDAP: `python manage.py sync_ldap_users --list-ldap-users`
2. Testa l'autenticazione: `python manage.py test_ldap_auth email@esempio.com password`
3. Controlla la connessione LDAP: `python manage.py sync_ldap_users --test-ldap-connection`

### Problema: Campi password visibili per utenti LDAP
**Soluzione**: 
- Assicurati che i file JavaScript e CSS siano serviti correttamente
- Controlla la console del browser per errori JavaScript

### Problema: Ruoli non assegnati correttamente
**Soluzione**:
- Verifica la mappatura gruppi LDAP nelle settings
- Controlla che l'utente appartenga ai gruppi LDAP corretti

## Caratteristiche di Sicurezza

- **Password Inutilizzabili**: Gli utenti LDAP hanno password Django non utilizzabili
- **Sincronizzazione Automatica**: I dati vengono sincronizzati ad ogni login
- **Validazione Robusta**: Form validation impedisce configurazioni errate
- **Audit Trail**: Tutte le modifiche sono tracciate nei log Django

## Note Tecniche

### File Modificati/Aggiunti
- `vendor_management_system/users/admin.py` - Admin interface migliorata
- `staticfiles/admin/js/ldap_user_admin.js` - JavaScript per UI dinamica  
- `staticfiles/admin/css/ldap_user_admin.css` - Stili personalizzati
- `vendor_management_system/users/management/commands/` - Comandi di gestione
- `vendor_management_system/templates/admin/users/user/` - Template personalizzati

### Backend di Autenticazione
Il sistema utilizza un backend ibrido che:
1. Prova prima l'autenticazione LDAP
2. Se fallisce, prova l'autenticazione locale Django
3. Sincronizza automaticamente i dati utente da LDAP

## Manutenzione

### Backup Utenti
Prima di modifiche importanti, esporta gli utenti:
```bash
python manage.py dumpdata users.User > users_backup.json
```

### Monitoraggio
Monitora i log per identificare problemi di autenticazione:
```bash
tail -f logs/django.log | grep -i ldap
```