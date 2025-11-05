# Istruzioni di Installazione - Dashboard Fornitori

## 📦 Installazione Dipendenze

### Metodo 1: Con Ambiente Virtuale (Raccomandato)

```bash
# Naviga nella directory del progetto
cd /home/fabio/SRM

# Attiva l'ambiente virtuale esistente (se presente)
source venv/bin/activate
# oppure
source env/bin/activate

# Installa openpyxl
pip install openpyxl==3.1.2

# Oppure installa tutte le dipendenze da requirements.txt
pip install -r requirements.txt
```

### Metodo 2: Senza Ambiente Virtuale (Non Raccomandato)

```bash
# Solo se necessario, con --break-system-packages
pip install openpyxl==3.1.2 --break-system-packages
```

### Metodo 3: Con apt (Sistema Debian/Ubuntu)

```bash
# Installa il pacchetto di sistema
sudo apt install python3-openpyxl
```

## ✅ Verifica Installazione

Dopo l'installazione, verifica che openpyxl sia disponibile:

```bash
python -c "import openpyxl; print(openpyxl.__version__)"
```

Output atteso: `3.1.2` (o versione installata)

## 🚀 Test della Dashboard

### 1. Esegui le Migrazioni (se necessario)

```bash
python manage.py migrate
```

### 2. Avvia il Server di Sviluppo

```bash
python manage.py runserver
```

### 3. Accedi alla Dashboard

Apri il browser e vai a:
```
http://localhost:8000/vendors/dashboard/
```

**Nota**: È richiesta l'autenticazione. Assicurati di aver effettuato il login.

### 4. Testa l'Export Excel

1. Nella dashboard, applica alcuni filtri cliccando sui grafici
2. Clicca sul pulsante verde "Esporta Excel" in basso a destra
3. Verifica che il file Excel venga scaricato correttamente

## 🧪 Esegui i Test

```bash
# Test della dashboard
python manage.py test vendor_management_system.vendors.tests.test_dashboard

# Test completi del modulo vendors
python manage.py test vendor_management_system.vendors

# Con verbose output
python manage.py test vendor_management_system.vendors.tests.test_dashboard -v 2
```

## 🐛 Troubleshooting

### Errore: ModuleNotFoundError: No module named 'openpyxl'

**Soluzione**: Installa openpyxl seguendo i passaggi sopra.

### Errore: 404 - Page not found per /vendors/dashboard/

**Possibili cause**:
1. URL non configurato correttamente
2. App 'vendors' non inclusa in INSTALLED_APPS

**Soluzione**:
```python
# Verifica config/settings.py
INSTALLED_APPS = [
    # ...
    'vendor_management_system.vendors',
    # ...
]

# Verifica config/urls.py
urlpatterns = [
    # ...
    path('vendors/', include('vendor_management_system.vendors.urls')),
    # ...
]
```

### Errore: Redirect al login anche se autenticato

**Soluzione**: Verifica che il decorator `@login_required` funzioni correttamente:
```python
# In settings.py
LOGIN_URL = '/admin/login/'  # o il tuo URL di login
```

### Grafici non si caricano

**Possibili cause**:
1. Endpoint API non risponde
2. Errore JavaScript nella console
3. CORS issues (se frontend separato)

**Debugging**:
```bash
# Test endpoint API
curl -H "Authorization: Token YOUR_TOKEN" http://localhost:8000/vendors/dashboard-stats/

# Controlla i log Django
python manage.py runserver --verbosity 2

# Apri Developer Tools nel browser e controlla Console/Network
```

### Export Excel vuoto o incompleto

**Verifica**:
1. Che ci siano fornitori nel database
2. I filtri applicati non escludano tutti i fornitori
3. I permessi di scrittura nella directory temporanea

**Debug**:
```python
# In Django shell
python manage.py shell

from vendor_management_system.vendors.models import Vendor
print(Vendor.objects.count())  # Dovrebbe essere > 0
```

## 📊 Creazione Dati di Test

Per testare la dashboard con dati di esempio:

```bash
python manage.py shell
```

```python
from vendor_management_system.vendors.models import Vendor, Category, Address

# Crea categorie
cat1 = Category.objects.create(code='SERV', name='Servizi', is_active=True)
cat2 = Category.objects.create(code='PROD', name='Prodotti', is_active=True)

# Crea indirizzo
addr = Address.objects.create(
    street_address='Via Roma 123',
    city='Milano',
    postal_code='20100',
    country='Italia'
)

# Crea fornitori
for i in range(20):
    Vendor.objects.create(
        name=f'Fornitore Test {i}',
        email=f'fornitore{i}@test.com',
        phone=f'+39 02 1234567{i}',
        category=cat1 if i % 2 == 0 else cat2,
        qualification_status='APPROVED' if i % 3 == 0 else 'PENDING',
        risk_level=['LOW', 'MEDIUM', 'HIGH'][i % 3],
        country='Italia' if i % 4 != 0 else 'Francia',
        quality_rating_avg=3.5 + (i * 0.1),
        fulfillment_rate=70 + (i * 1.5),
        on_time_delivery_rate=80 + (i * 1),
        is_active=True,
        address=addr,
        vat_number=f'IT0123456789{i}',
        fiscal_code=f'RSSMRA80A01H501{i}'
    )

print("✅ Creati 20 fornitori di test")
```

## 🔐 Creazione Utente Admin

Se non hai ancora un utente admin:

```bash
python manage.py createsuperuser
```

Segui le istruzioni per creare username, email e password.

## 📚 Risorse Aggiuntive

- **Documentazione Dashboard**: `README_DASHBOARD.md`
- **Riepilogo Implementazione**: `DASHBOARD_IMPLEMENTATION_SUMMARY.md`
- **Test Suite**: `tests/test_dashboard.py`
- **API Documentation**: http://localhost:8000/swagger/

## 🎯 Checklist Post-Installazione

- [ ] openpyxl installato e verificato
- [ ] Server Django avviabile senza errori
- [ ] Dashboard accessibile via browser
- [ ] Login funzionante
- [ ] Grafici si caricano correttamente
- [ ] Filtri interattivi funzionanti
- [ ] Ricerca testuale funzionante
- [ ] Export Excel scarica file correttamente
- [ ] Test automatici passano
- [ ] Dati di test creati (opzionale)

## 📞 Supporto

In caso di problemi:

1. Controlla i log Django: `python manage.py runserver --verbosity 2`
2. Controlla la console JavaScript nel browser (F12)
3. Esegui i test: `python manage.py test vendor_management_system.vendors.tests.test_dashboard`
4. Verifica la configurazione in `config/settings.py` e `config/urls.py`

---

**Nota**: Tutti i comandi assumono che tu sia nella directory root del progetto (`/home/fabio/SRM`).
