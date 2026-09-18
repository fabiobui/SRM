# SRM / Vendor Management System — Panoramica del progetto e setup locale

> Documento di riferimento generato. Completa il [`README.md`](../README.md) di livello superiore (che include
> anche l'approfondimento architetturale — business logic, modello dati, workflow, design delle API) e i docs già
> esistenti in `docs/` (`SISTEMA_OVERVIEW.md` = panoramica funzionale in italiano, `MANUALE_UTENTE_ADMIN.md` =
> manuale utente admin, `ANALISI_AREA_FORNITORE.md`, `COMPETENZE_DOCUMENTI.md` = note su feature specifiche,
> `VENDOR_DASHBOARD.md` = la dashboard di analytics fornitori, `LDAP.md` = autenticazione LDAP/AD,
> `URL_PREFIX_CONFIG.md` = il prefisso `/fornitori`, `SCRIPT_IMPORT.md` = gli script di import/manutenzione dati,
> `PRE_COMMIT.md` = installazione e funzionamento di pre-commit, `DEPLOY.md` = procedura di deploy sulla VM di
> test/produzione).
> Questo file si concentra su: **cos'è il progetto**, **come è organizzato**, **quali portali web esistono**, e
> **come farlo girare su una macchina locale**, incluse le lacune trovate nei docs/config esistenti e come
> puntarlo su una copia di dati reali invece che su un database vuoto/seedato (§11).

---

## 1. Cos'è questo progetto

**SRM (Supplier Relationship Management)**, chiamato internamente anche **VMS (Vendor Management System)**, è
un'applicazione web Django costruita per **Fulgard** per gestire l'intero ciclo di vita dei fornitori esterni:
qualificazione, documentazione di compliance, competenze/certificazioni, valutazioni e ordini di acquisto.

È uno strumento interno di back-office + self-service, non un prodotto pubblico — lo dimostrano la UI/modello di
dominio pensati prima di tutto per l'italiano (tipi di contratto, DURC, verifiche antimafia, certificazioni ISO,
ecc.) e un'integrazione opzionale con un sistema legacy interno chiamato **Embyon** (un'anagrafica fornitori più
vecchia basata su MySQL che l'admin può interrogare/incrociare).

## 2. Stack tecnologico (riferimento rapido)

| Layer | Technology |
|---|---|
| Language / Framework | Python 3.12 (fissato nell'immagine Docker), Django 5.0.6, Django REST Framework 3.15 |
| Database | **MySQL** (via `mysqlclient`) — vedi §7 per una discrepanza con il setup Docker committato, che è configurato per PostgreSQL |
| Cache / Broker | Redis (`django-redis` per la cache, usato anche come broker Celery) |
| Async tasks | Celery 5.4 + Celery Beat (`django-celery-beat`, schedule su DB) + Flower (UI di monitoraggio task) |
| Auth | Autenticazione a sessione per la UI web (login view custom) + un'autenticazione a token JWT-like via query-param custom per la REST API; autenticazione **LDAP/Active Directory** opzionale tramite un backend ibrido custom (`ldap3`), attivabile con `LDAP_ENABLED` |
| Password hashing | Argon2 |
| Admin UI | Django Admin con tema **Jazzmin** |
| API docs | `drf-yasg` → Swagger UI (`/swagger/`) |
| Import/Export | `django-import-export` + `openpyxl` (import/export Excel nell'admin e nella dashboard fornitori) |
| Testing | `pytest` + `pytest-django` + `factory_boy` / `Faker` |
| i18n | Italiano (default), Inglese, Francese — `locale/` |
| Static/media serving (prod) | **Apache + `mod_wsgi`** — confermato sulla VM (integra l'app direttamente nei processi worker di Apache; non c'è un hop separato `gunicorn`/reverse-proxy come storicamente assumeva lo stack tecnologico). `whitenoise` e `gunicorn` sono ancora entrambi presenti nell'insieme delle dipendenze di produzione ma non sono ciò che serve effettivamente le richieste — vedi §7, punto 7. |
| Containerization | Docker + docker-compose (django, postgres, redis, celeryworker, celerybeat, flower) — vedi avvertenza in §7 |

## 3. App Django (mappa dei moduli)

Layout del progetto: `manage.py` nella root del repo, settings in `config/`, tutte le app di business sotto
`vendor_management_system/`.

| App | Responsabilità | Modelli chiave |
|---|---|---|
| `core` | Fondamenta: autenticazione a token JWT-style via query-param, backend di autenticazione LDAP/ibridi, permessi, decoratori, routing di redirect verso la dashboard | — |
| `users` | Modello utente custom, sistema di ruoli | `User` (ruoli: `admin`, `bo_user`, `vendor`) |
| `vendors` | Il cuore del sistema: anagrafica fornitori, geografia, categorie, competenze, servizi, contratti, valutazioni | `Vendor`, `Category`, `Address`, `Country`/`Region`/`Province`, `CompetenceZone(+Rule)`, `Competence`, `VendorCompetence`, `CompetenceSet`, `QualificationType`, `ServiceType`, `VendorService`, `ServiceSet`, `Contract`, `EvaluationFrequency`, `EvaluationCriterion`, `Evaluator`, `VendorEvaluation` |
| `documents` | Ciclo di vita dei documenti di compliance (upload, revisione, scadenza) + dashboard per ruolo | `DocumentType`, `Document`, `DocumentSet` |
| `portal` | Il portale fornitori self-service più recente (`/portale/`) — documenti, requisiti, richieste di modifica profilo, stato di qualificazione | `VendorChangeRequest` |
| `purchase_orders` | Macchina a stati degli ordini di acquisto (PENDING→ISSUED→ACKNOWLEDGED→DELIVERED / CANCELLED) | `PurchaseOrder` |
| `historical_performances` | Snapshot a serie temporale dei KPI dei fornitori, catturati ogni 6h via Celery Beat | `HistoricalPerformance` |

**Nota sul numero di modelli**: solo `vendors/models.py` conta ~20 classi di modello (molto più ricco del modello
dati semplificato descritto nella narrazione architetturale del [`README.md`](../README.md) di livello superiore,
che riflette una versione precedente/semplificata del sistema. Considera questo file + il codice come la fonte di
verità attuale.

## 4. Portali web / interfacce

L'app espone **punti di ingresso basati sul ruolo**, tutti dietro un singolo login (`/auth/login/`). Dopo il
login, `redirect_by_role()` / `dashboard_redirect` invia l'utente nel posto giusto:

| Ruolo | Area di atterraggio | URL | Note |
|---|---|---|---|
| **Admin / superuser** | Django Admin (tema Jazzmin) | `/admin/` | CRUD completo su ogni modello; ha anche una scorciatoia "Selezione" verso la dashboard fornitori |
| **Back Office (bo_user)** | Django Admin | `/admin/` (anche `/documents/backoffice/`) | Gestione operativa: fornitori, documenti, ordini, valutazioni. `documents/backoffice/` è una vista dashboard specifica dell'app, distinta da `/admin/` |
| **Vendor (self-service)** | Portale Fornitori | `/portale/` (namespace `portal:`) | Area self-service per fornitori attivi/correnti: i miei documenti, i miei requisiti/competenze, il mio profilo (+ richieste di modifica), il mio stato di qualificazione |
| — legacy | `/documents/portal/` | Vecchio URL del portale fornitori — ora è solo un redirect 301 verso `/portale/`, mantenuto per retrocompatibilità |
| Tutti (dashboard interna) | Dashboard analytics fornitori | `/vendors/dashboard/` | Grafici/statistiche/filtri + export Excel sull'anagrafica fornitori (orientata a BO/Admin) |
| — | Dashboard generica legacy | `/documents/admin/` e `/documents/dashboard/` | Entrambe mappano su `AdminDashboardView` |

Altri endpoint importanti non-portale:

- `/swagger/` — documentazione REST API interattiva (drf-yasg)
- Gli endpoint REST in stile `/api` sono in realtà montati alla radice dell'app, es. `/vendors/`, `/users/`,
  `/purchase-orders/`, `/documents/` (sia le viste HTML sia i viewset DRF condividono questi prefissi — vedi
  `config/urls.py`)
- `POST /core/obtain-auth-token/` — ottiene il token API (email/password) usato come `?token=...` nelle chiamate
  API (`QueryParameterTokenAuthentication`)
- `/auth/login/`, `/auth/logout/` — il vero login/logout HTML usato da tutti i ruoli

Se `USE_FORNITORI_PREFIX=True` (produzione dietro un reverse proxy), tutti gli URL sopra vengono serviti anche
sotto un prefisso `/fornitori` (anche static/media). Lascia questo a `False` per lo sviluppo locale.

## 5. Come funziona (flussi di lavoro principali, in breve)

- **Ciclo di vita del fornitore**: un fornitore viene registrato (da BO/Admin) con geografia, categoria,
  competenze, servizi, contratti; i documenti richiesti dalla sua categoria devono essere caricati e approvati; un
  punteggio di qualificazione/valutazione determina `qualification_status` (PENDING/APPROVED/REJECTED/TO_REVIEW) e
  `vendor_final_evaluation`.
- **Ordini di acquisto**: semplice macchina a stati PENDING → ISSUED → ACKNOWLEDGED → DELIVERED, annullabile da
  qualsiasi stato non terminale; i segnali Django impostano automaticamente i campi data pertinenti ad ogni
  transizione; la consegna innesca il ricalcolo delle metriche di performance del fornitore.
- **Analytics delle performance**: tasso di consegna puntuale, media del rating di qualità, tempo di risposta,
  tasso di evasione — calcolati dai dati di `PurchaseOrder` e salvati come snapshot in `HistoricalPerformance` ogni
  6 ore da un task Celery Beat.
- **Compliance documentale**: i documenti hanno finestre di validità specifiche per tipo e vengono tracciati
  attraverso gli stati PENDING/UPLOADED/APPROVED/REJECTED/EXPIRED con avvisi di scadenza.
- **Auth**: account locali (Django) per default; autenticazione LDAP/Active Directory opzionale
  (`HybridAuthBackend`) che prova prima LDAP (via `ldap3`) e ricade sul `ModelBackend` standard di Django —
  disabilitata localmente per default (`LDAP_ENABLED=False`).
- **Integrazione Embyon**: il form admin del Vendor ha una modale "search Embyon" che esegue una query SQL grezza
  contro una tabella MySQL legacy esterna (`EMBYON_FORNITORI_TABLE`, default `redmine_test.Embyon_Fornitori_T`)
  per precompilare i dati del fornitore in base a vecchio codice fornitore / partita IVA / codice fiscale. È
  tooling opzionale per il team BO — fallisce in modo controllato se la tabella/database non è raggiungibile, quindi
  **non** è richiesto per lo sviluppo locale.

## 6. Job in background (Celery)

- Broker & result backend: Redis (`CELERY_BROKER_URL`, la stessa istanza Redis usata come cache)
- Scheduler: `django_celery_beat` (schedule salvato nel DB, modificabile da Django Admin)
- Task schedulato: `record_historical_performance` ogni 6 ore (`config/settings.py` → `CELERY_BEAT_SCHEDULE`)
- UI di monitoraggio: **Flower** sulla porta `5555`

---

## 7. ⚠️ Lacune note tra i docs/config del repo e il codice effettivo

Vale la pena conoscerle prima di provare a far girare questo progetto, perché seguire alla lettera i docs/config
*originali* committati non avrebbe funzionato. I punti 1 e 2 qui sotto sono già stati **corretti in questo repo**
(nell'ambito del setup del percorso Docker in §8); i punti 3–6 sono ancora reali e vale la pena conoscerli; i
punti 7–9 sono nuovi riscontri emersi dall'ispezione diretta della VM di produzione (2026-09-15) che correggono
assunzioni precedenti in questo documento.

1. **Discrepanza sul motore database — corretta.** `docker-compose.yml`, `compose/django/entrypoint`, e il vecchio
   `docs/README.md` / `readme.md` (i due file sono stati da allora unificati nel `README.md` di livello superiore
   — vedi §7, punto 10) originariamente descrivevano/assumevano **PostgreSQL**
   (`DATABASE_URL=postgres://...`, `psycopg`). Ma `config/settings.py` in realtà costruisce `DATABASES` a partire
   da **variabili discrete in stile MySQL** (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`,
   `DB_PORT`, con `charset: utf8mb4`), e `requirements.txt` installa `mysqlclient` con `psycopg` commentato —
   **MySQL è il database di destinazione reale**, non Postgres. `docker-compose.yml`, `compose/django/Dockerfile`,
   e `compose/django/entrypoint` sono stati aggiornati per fornire e attendere **MySQL** invece (vedi §8, Track A).
   La vecchia cartella `compose/postgres/` è ancora presente nel repo ma non è più referenziata da
   `docker-compose.yml` — si può ignorare o eliminare più avanti.
2. **`requirements.txt` era fondamentalmente rotto — ora corretto e verificato contro la produzione
   (2026-09-15).** `config/settings.py` esegue incondizionatamente:
   ```python
   from dotenv import load_dotenv  # needs python-dotenv

   ...
   import ldap  # needs python-ldap
   from django_auth_ldap.config import (
       LDAPSearch,
       ActiveDirectoryGroupType,
   )  # needs django-auth-ldap
   ```
   Una versione precedente di questo documento affermava che `python-dotenv`, `python-ldap`, `django-auth-ldap`, e
   `ldap3` fossero tutti "fissati in `requirements.txt`" — **non era vero.** Quello che era effettivamente
   committato era un `pip freeze` casuale del Python di *sistema* della VM (`dbus-python`, `PyGObject`,
   `launchpadlib`, `cloud-init`, `netifaces`, ecc. — pacchetti a livello OS provenienti da `apt`, non dipendenze
   dell'app), e mancava **Django stesso**, oltre a `djangorestframework`, `drf-yasg`, `django-redis`,
   `django-celery-beat`, `django-jazzmin`, `argon2-cffi`, `python-dotenv`, `python-ldap`, `pytest-django`,
   `factory-boy`/`Faker`. Installando da quel file, avrebbe fallito già su `import django` — **l'app non avrebbe
   potuto avviarsi dal `requirements.txt` committato.**

   Questo è stato ora sostituito con l'**output esatto di `pip freeze` preso direttamente dal venv di produzione**
   (`/home/redmine/SRM/.venv` sulla VM Ubuntu 24.10 di produzione, Python 3.12.7 — vedi il punto 7 più sotto per
   come questo differisce da ciò che questo documento assumeva in precedenza), con `mod_wsgi` intenzionalmente
   escluso (solo Apache, vedi punto 7; non serve per il percorso Docker/dev-server usato localmente). Questo è ora
   verificato funzionante end-to-end: `docker compose up --build` installa senza errori, `python manage.py
   migrate` si completa contro MySQL, e il dev server serve `/auth/login/` con `200 OK`.
   > Nota a margine per un manutentore, non qualcosa che questo documento cambia: le impostazioni basate su
   > `django_auth_ldap` (`AUTH_LDAP_USER_SEARCH`/`AUTH_LDAP_GROUP_SEARCH` costruite con `LDAPSearch(...)`)
   > sembrano essere **configurazione morta** — `AUTHENTICATION_BACKENDS` in realtà punta a
   > `simple_ldap_backend.HybridAuthBackend`, che usa `ldap3` e legge impostazioni come semplici stringhe via
   > `getattr`, senza mai toccare quegli oggetti `LDAPSearch`. Questo è il motivo per cui `python-ldap`
   > /`django-auth-ldap` servono solo a soddisfare l'*import*, non per alcun comportamento a runtime. Vale la pena
   > un passaggio di pulizia indipendente da questo lavoro di setup.
3. **`python-ldap` è difficile da compilare su Windows nativo** (richiede l'OpenLDAP SDK / un compilatore C).
   Questo è uno dei motivi principali per cui la Track A (Docker) è ora il percorso consigliato — l'immagine basata
   su Debian installa automaticamente i pacchetti `apt` giusti (`libldap2-dev`, `libsasl2-dev`, `libssl-dev`). Vedi
   §8.
4. **Tre file di requirements diversi** (`requirements.txt`, `requirements_mysql.txt`, `requirements_upd.txt`)
   esistono con versioni di Django diverse (5.0.6 vs 4.2.7) e set di pacchetti diversi. `requirements.txt` è quello
   più completo/aggiornato (corrisponde a Django 5.0.6 in settings/Docker, ed è quello che
   `compose/django/Dockerfile` installa) — usa quello, non gli altri due.
5. **Non è committato alcun file `.env` per le esecuzioni native/locali (non Docker)** (correttamente escluso via
   gitignore) e non esiste un `.env.example`. Devi crearlo tu stesso se usi la Track B — vedi Track B, passo 6, per
   le chiavi esatte. (Il percorso Docker ora fornisce i propri template committati-ma-gitignorati:
   `.envs/.django.env` e `.envs/.mysql.env`.)
6. **Python 3.13** (quello attualmente su questa macchina) è più recente di quello con cui questo progetto è stato
   costruito/testato (l'immagine Docker fissa Python 3.12.3). Django 5.0.x supporta ufficialmente fino a Python
   3.12; le wheel di mysqlclient per la 3.13 potrebbero essere disponibili oppure no. Questo non è un problema per
   la Track A (Docker fissa il proprio Python). Per la Track B (nativa), crea il venv con **Python 3.12**
   specificamente, non con qualunque cosa `python` risolva.
7. **Come funziona davvero la produzione — confermato ispezionando direttamente la VM, corregge assunzioni
   precedenti di questo documento.** L'app è deployata **nativamente** (senza Docker) su un host Ubuntu 24.10,
   Python 3.12.7, tramite un venv in `/home/redmine/SRM/.venv` — non `/home/fabio/SRM` come dice
   `INSTALLATION_INSTRUCTIONS.md` (obsoleto; la directory del progetto/utente proprietario è cambiata a un certo
   punto). Viene servita da **Apache + `mod_wsgi`**, che integra l'app direttamente nei processi worker di Apache —
   non c'è un processo `gunicorn` né `runserver_plus` in produzione (`shell_scripts/start_django.sh`, che
   esegue `runserver_plus` sulla `:8088`, sembra essere uno script residuo per dev/test manuale, non ciò che è
   effettivamente in esecuzione). MySQL è un **server MySQL 8.0 separato e remoto** (non colocato sulla VM
   dell'app). Redis 7.0 gira localmente sulla VM con una password impostata (`requirepass`), usato sia per la
   cache sia per il broker Celery; al momento dell'ispezione non è stato trovato in esecuzione un worker Celery per
   *questa* app (erano attivi solo worker per app non correlate che condividono la VM — `sendpdf`, `fapp`).
   `LDAP_ENABLED=True` in produzione, con autenticazione contro un dominio Active Directory (`sicura.loc`) via
   LDAPS (porta 636, `LDAP_TLS_VALIDATE=False`). Nulla di tutto ciò cambia il setup Docker locale (LDAP resta
   disabilitato localmente secondo la tua preferenza — vedi §8 — e MySQL/Redis sono comunque container locali in
   entrambi i casi), ma corregge la tabella dello stack tecnologico in §2 e spiega perché
   `shell_scripts/start_django.sh`/`INSTALLATION_INSTRUCTIONS.md` non corrispondono alla realtà.
8. **Rilevante per la sicurezza, non un blocco per il setup locale, ma da segnalare a chi gestisce la VM.** Il
   `.env` di produzione ha `DEBUG=True` e una `SECRET_KEY` debole e non casuale. Nessuno dei due influisce sullo
   sviluppo locale (localmente si usano sempre valori propri solo per dev — vedi §8, A2), ma entrambi meritano una
   correzione sulla VM indipendentemente da questo documento.
9. **Un conflitto di porte Docker locale, non legato alla configurazione di questa app.** Se un altro stack
   `docker compose` di un altro progetto è già in esecuzione su questa macchina e ha già occupato le porte host
   `3306`/`6379` (es. è stato trovato in esecuzione qui uno stack `sendpdf`), i mapping di porta predefiniti del
   `docker-compose.yml` di questo progetto per MySQL (`3306`) e Redis (`6379`) non riusciranno a fare il bind.
   Risolto rimappando solo le porte **lato host** di questo progetto — vedi §8, A3 — il traffico
   container-to-container all'interno della rete compose non è comunque interessato.

---

## 8. Checklist per il setup locale

Due percorsi supportati:

- **Track A — Docker (consigliato).** Un solo `docker compose up`, senza bisogno di alcun toolchain nativo per
  MySQL/LDAP — il container fa ciò che ti darebbe WSL2, ma è interamente descritto da file già presenti nel repo
  (corretti nell'ambito di questo documento — vedi §7, punti 1–2). Usa questo percorso a meno che tu non abbia un
  motivo specifico per far girare Django direttamente sull'host.
- **Track B — Windows nativo (o WSL2 a mano).** Più parti in movimento (versione Python, server MySQL, Redis,
  strumenti di build per `mysqlclient`/`python-ldap`), ma nessuna dipendenza da Docker e un debugger si attacca
  direttamente.

---

### Track A — Docker (consigliato)

#### A1 — Prerequisiti

Installa [Docker Desktop](https://www.docker.com/products/docker-desktop/) e assicurati che sia effettivamente in
**esecuzione** (l'icona della balena nel tray; `docker compose version` dovrebbe stampare una versione, e `docker
info` non dovrebbe dare errore). Su Windows, usa il backend WSL2 (default di Docker Desktop) invece di Hyper-V.

#### A2 — File env

Già creati per te ed esclusi da git (mai committati, secondo la regola `.envs/*` del `.gitignore`):
- `.envs/.django.env` — `SECRET_KEY`, `DEBUG`, URL Redis/Celery, `LDAP_ENABLED=False`, ecc.
- `.envs/.mysql.env` — sia le variabili `MYSQL_*` di cui l'immagine ufficiale `mysql:8.0` ha bisogno per
  auto-inizializzarsi, sia le variabili `DB_*` che `config/settings.py` legge (`DB_HOST=mysql` — il nome del
  servizio compose, non `localhost`, dato che i container si raggiungono tra loro tramite il nome del servizio
  sulla rete compose).

I default sono password placeholder solo per sviluppo — va bene lasciarle così localmente; cambiale se vuoi.

#### A3 — Build e avvio dell'intero stack

Dalla root del repo:
```powershell
docker compose up --build
```
Questo costruisce l'immagine `django` (Python 3.12.3, con le dipendenze di sistema per `mysqlclient` e
`python-ldap` ora incluse — vedi §7.2/§7.3) e avvia:

| Servizio | Cosa fa | Porta sull'host |
|---|---|---|
| `mysql` | MySQL 8.0, database/utente creati automaticamente da `.envs/.mysql.env` | `13306` (→ container `3306`) |
| `redis` | Cache + broker Celery | `16379` (→ container `6379`) |
| `django` | Attende MySQL (vedi `compose/django/entrypoint`), poi esegue `makemigrations`, `migrate`, e `runserver_plus` (vedi `compose/django/start`) | `8000` |
| `celeryworker` | Elabora i task in background | — |
| `celerybeat` | Innesca il task schedulato `record_historical_performance` ogni 6h | — |
| `flower` | UI di monitoraggio Celery (protetta da basic-auth con `CELERY_FLOWER_USER`/`PASSWORD`) | `5555` |

> **Perché `13306`/`16379` invece del "naturale" `3306`/`6379`**: un altro progetto Docker già presente su questa
> macchina (`sendpdf`) occupa già le porte host `3306` e `6379`. `docker-compose.yml` è stato aggiornato per
> mappare MySQL/Redis di questo progetto su `13306`/`16379` sull'host — un remap puramente lato host, i container
> continuano a parlarsi internamente come `mysql:3306`/`redis:6379`, quindi non è stato necessario cambiare nulla
> in `.envs/`. Se non hai uno stack in conflitto in esecuzione, sentiti libero di riportarle a `3306:3306`/
> `6379:6379` in `docker-compose.yml`.

Il primo avvio richiederà alcuni minuti (installazione dei pacchetti di sistema + Python). Lascia questo terminale
in esecuzione, oppure aggiungi `-d` per eseguire in background. **Verificato funzionante end-to-end il
2026-09-15**: la build va a buon fine, tutte le migrazioni si applicano senza errori contro MySQL, il dev server
serve `/auth/login/` con `200 OK`, il worker Celery si connette e riporta `ready`, Celery Beat parte con lo
scheduler basato su DB, e Flower risponde (`401` senza credenziali basic-auth, come atteso).

#### A4 — Crea un utente admin

In un secondo terminale, una volta che lo stack è attivo:
```powershell
docker compose exec django python manage.py createsuperuser
```

#### A5 — (Opzionale) seeda i dati di riferimento

Stessi comandi della versione nativa, eseguiti però dentro il container — vedi §9 più sotto per cosa fa
effettivamente ciascuno:
```powershell
docker compose exec django python manage.py populate_document_types
docker compose exec django python manage.py populate_competences
docker compose exec django python manage.py seed_competence_sets
docker compose exec django python manage.py seed_service_sets
docker compose exec django python manage.py seed_document_sets
```

#### A6 — Usalo

- App: `http://localhost:8000/` (→ login → atterraggio basato sul ruolo, vedi §4)
- Swagger: `http://localhost:8000/swagger/`
- Flower: `http://localhost:5555/` (basic-auth: `CELERY_FLOWER_USER`/`CELERY_FLOWER_PASSWORD` da
  `.envs/.django.env`)
- MySQL: `localhost:13306` se vuoi connettere un client GUI (credenziali in `.envs/.mysql.env`; la porta è
  `13306`, non la `3306` di default — vedi la nota in A3)

#### A7 — Comandi quotidiani

```powershell
docker compose up -d                 # avvia in background
docker compose logs -f django        # segui i log di Django
docker compose exec django python manage.py <cmd>   # qualsiasi management command
docker compose exec django pytest    # esegue la suite di test nel container
docker compose down                  # ferma tutto (mantiene i volumi dati)
docker compose down -v               # ferma E cancella i volumi dati di MySQL/Redis
```
Le modifiche al codice sull'host vengono recepite live (il repo è montato via bind mount in `/app`, e
`start`/`start-celery*` usano `watchfiles` / l'autoreload di Django).

---

### Track B — Windows nativo (fallback)

#### B1 — Procurati il Python giusto

Installa **Python 3.12** se non già presente (Python 3.13 è quello attualmente su questa macchina e non è testato
con Django 5.0.6 / mysqlclient — non è un problema per la Track A, dato che l'immagine Docker fissa il proprio
Python). Dalla root del repo:
```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

#### B2 — Soddisfa le dipendenze di build native per MySQL + LDAP

Il principale punto di attrito su Windows nativo (esattamente ciò che la Track A evita): installa
[MySQL Server](https://dev.mysql.com/downloads/installer/) (edizione Community) e i
[Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/), dato che `mysqlclient`
e/o `python-ldap` potrebbero dover compilare contro di essi. `python-ldap` è tipicamente la parte più dolorosa; se
non riesci a installarlo e non ti serve LDAP funzionante, puoi commentare temporaneamente le due righe solo-LDAP
in `config/settings.py` (`import ldap` / `from django_auth_ldap...` — vedi la nota sul codice morto in §7.2) —
**workaround solo locale, non committarlo**.

Alternativa: esegui questa stessa Track B *dentro WSL2 Ubuntu* invece che su Windows nativo — `apt install
default-libmysqlclient-dev libldap2-dev libsasl2-dev` ti garantisce build pulite, esattamente come fa l'immagine
Docker.

#### B3 — Installa le dipendenze Python

```powershell
pip install -r requirements.txt
```
(`requirements.txt` ora include `python-dotenv`, `django-auth-ldap`, `python-ldap`, `ldap3` — vedi §7.2.)

#### B4 — Crea e avvia un database MySQL locale

```sql
CREATE DATABASE vms_local CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vms_user'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON vms_local.* TO 'vms_user'@'localhost';
FLUSH PRIVILEGES;
```

#### B5 — Installa e avvia Redis localmente

Necessario per il backend di cache e (se vuoi eseguire Celery) per il broker. Il modo più semplice su Windows:
esegui solo la parte Redis via Docker (`docker run -d -p 6379:6379 redis:7.2.5-alpine`) oppure via WSL2 (`apt
install redis-server`). Le build native Redis per Windows sono non ufficiali/non mantenute — evitale.

#### B6 — Crea il file `.env`

Crea un file chiamato `.env` nella root del repo (nella stessa cartella di `manage.py` — `config/settings.py`
chiama `load_dotenv()` senza percorso, che cerca nella directory di lavoro corrente / nel `.env` più vicino):

```dotenv
# Django core
SECRET_KEY=dev-only-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# URL prefix (keep False locally)
USE_FORNITORI_PREFIX=False

# i18n / tz (defaults are fine, shown for clarity)
LANGUAGE_CODE=it
TIME_ZONE=Europe/Rome

# Database (MySQL)
DB_ENGINE=django.db.backends.mysql
DB_NAME=vms_local
DB_USER=vms_user
DB_PASSWORD=change-me
DB_HOST=localhost
DB_PORT=3306

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# LDAP (leave disabled for local dev)
LDAP_ENABLED=False
```

> Se vuoi il percorso più veloce possibile per "fammi solo vedere l'app" con **zero setup di MySQL**, puoi invece
> impostare `DATABASE_URL=sqlite:///db.sqlite3` (l'*unico* caso in cui `settings.py` effettivamente interpreta
> `DATABASE_URL`) e saltare completamente il B4 — non è come gira l'app in produzione, ma va bene per curiosare
> nella UI/admin.

#### B7 — Esegui le migrazioni e crea un utente admin

```powershell
python manage.py migrate
python manage.py createsuperuser
```
Dai al superuser email/password; un superuser atterra sempre su `/admin/` indipendentemente dal campo `role`.
(Questo passo `migrate` applica le **migrazioni di schema** proprie di Django — vedi §9 per come questo sia
diverso dai comandi di seed-data in B8.)

#### B8 — (Opzionale) Seed dei dati di riferimento/demo

Vedi §9 più sotto per una spiegazione completa di ciascun comando:
```powershell
python manage.py populate_document_types
python manage.py populate_competences
python manage.py seed_competence_sets
python manage.py seed_service_sets
python manage.py seed_document_sets
```
Ci sono anche script di import standalone una-tantum nella root del repo (`import_vendors.py`,
`import_competenze.py`, `import_servizi.py`, `import_titoli.py`, `import_valutazioni.py`, `import_geography.py`,
`import_documenti.py`) — sono stati scritti per una migrazione dati una-tantum da un sistema legacy/CSV e in
genere si aspettano file sorgente specifici; leggi l'intestazione di ciascuno script prima di eseguirlo invece di
assumere che sia un seeder generico.

#### B9 — Avvia il dev server

```powershell
python manage.py runserver
```
Visita `http://localhost:8000/` → reindirizza a `/auth/login/` → accedi con il superuser → atterri su `/admin/`.
Altri punti di ingresso da provare: `http://localhost:8000/vendors/dashboard/`,
`http://localhost:8000/swagger/`, `http://localhost:8000/portale/` (richiede un utente con ruolo `vendor`
collegato a un record `Vendor` per essere utile).

#### B10 — (Opzionale) Esegui worker Celery + beat + Flower

Necessario solo se stai lavorando su task in background / snapshot delle performance storiche. Ciascuno nel suo
terminale (venv attivato, Redis in esecuzione):
```powershell
celery -A config.celery_app worker -l info --pool=solo   # --pool=solo needed on native Windows
celery -A config.celery_app beat -l info
celery -A config.celery_app flower --port=5555
```

#### B11 — Esegui la suite di test

```powershell
pytest
```
Usa `pytest-django` con `DJANGO_SETTINGS_MODULE=config.settings` (vedi `pytest.ini`) e factory `factory_boy`/
`Faker` nel pacchetto `tests/` di ciascuna app — non servono fixture speciali oltre a una connessione DB
funzionante.

---

## 9. Migrazioni di schema vs. i management command di seed-data

Due cose *diverse* vengono entrambe chiamate genericamente "migrazioni" in questo progetto — vale la pena
distinguerle:

- **`python manage.py migrate`** applica le **migrazioni di schema** auto-generate proprie di Django (i file
  sotto la cartella `migrations/` di ciascuna app, es. `vendors/migrations/0031_vendor_embyon_blocked_and_more.py`).
  Queste creano/alterano tabelle e colonne del database per farle corrispondere a `models.py`. Non contengono dati
  di business, solo DDL. Questo comando va sempre eseguito; è ciò che fa sì che le tabelle dell'app esistano
  affatto.
- **I management command `populate_*` / `seed_*`** (eseguiti *dopo* `migrate`, interamente opzionali) sono
  comandi custom, una-tantum, di **seeding dei dati**, specifici del dominio di questa app — inseriscono righe di
  dati di riferimento sulla compliance dei fornitori italiani (tipi di documento, competenze/certificazioni, ecc.)
  che i menu a tendina della UI e i form dell'admin si aspettano esistano. Nulla nell'app *richiede* questi dati
  per avviarsi, ma diverse schermate (es. scegliere un "Set Documentale" su un fornitore) sono vuote/inutilizzabili
  senza. Tutti e cinque sono idempotenti (sicuri da rieseguire — usano `update_or_create`/`get_or_create`, quindi
  rieseguirli aggiorna semplicemente le righe esistenti invece di duplicarle).

L'ordine di esecuzione è importante per un paio di essi, dato che alcuni seedano righe di catalogo che altri
collegano insieme:

```
1. populate_document_types   →  creates DocumentType rows (DURC, ISO 9001, RC Professionale, ...)
2. populate_competences      →  creates Competence rows (RSPP, ASPP, Energy Manager, ...)
3. seed_competence_sets      →  creates/links Competence rows *and* groups them into CompetenceSet
                                 (per-Category bundles of professional requirements)
4. seed_service_sets         →  creates ServiceType rows (hierarchical: parent categories + specific
                                 services) and groups them into ServiceSet
5. seed_document_sets        →  requires (1) to already exist — links existing DocumentType rows into
                                 named DocumentSet bundles; anything not found is skipped with a warning,
                                 not an error
```

Cosa fa ciascuno, in termini semplici:

| Comando | App / modello/i | Scopo |
|---|---|---|
| `populate_document_types` | `documents.DocumentType` | Seeda ~20 tipi di documento standard per la compliance dei fornitori italiani (DURC, Visura Camerale, certificato antimafia, ISO 9001/14001/45001/50001, polizze assicurative, documenti di sicurezza come DVR/DUVRI/POS, ecc.), ciascuno con il suo flag di obbligatorietà, periodo di validità di default e lead time di avviso di scadenza. È il catalogo master dei "documenti che un fornitore potrebbe dover fornire." |
| `populate_competences` | `vendors.Competence` | Seeda ~25 qualifiche/certificazioni professionali che il personale di un fornitore può possedere (ruoli di sicurezza RSPP/ASPP, ATEX, HAZOP chairman, Energy Manager, certificazioni auditor ISO, ecc.), ciascuna con se richiede certificazione, se/con che frequenza richiede rinnovo, e se è obbligatoria. |
| `seed_competence_sets` | `vendors.Competence`, `vendors.CompetenceSet`, `vendors.Category` | Si basa su `populate_competences`: aggiunge un ulteriore lotto di codici di competenza specifici del dominio (da un foglio di calcolo sorgente reale, es. qualifiche medico/infermiere di Medicina del Lavoro, requisiti per subappaltatori come SOA/F-Gas), poi li raggruppa in bundle **`CompetenceSet`** nominati, uno per ciascuna `Category` di fornitore (es. "MDL - MEDICO COMPETENTE"). Questi set guidano la checklist dei requisiti mostrata nella scheda "Requisiti Professionali" di un fornitore in base alla sua classificazione. |
| `seed_service_sets` | `vendors.ServiceType`, `vendors.ServiceSet`, `vendors.Category` | Pattern simile ma per i servizi invece che per le competenze: crea una gerarchia `ServiceType` a due livelli (categoria genitore + servizi specifici, es. "Medicina del Lavoro" → "Prelievi ematochimici", "Drug test", ...) e li raggruppa in bundle `ServiceSet` usati dal menu a tendina della scheda "Servizi". |
| `seed_document_sets` | `documents.DocumentSet`, `documents.DocumentType` | Raggruppa le righe `DocumentType` esistenti (create da `populate_document_types`) in bundle `DocumentSet` nominati (es. "SUBAPPALTATORE", "MEDICINA DEL LAVORO") — scegliere un set sulla scheda "Documenti" di un fornitore crea automaticamente l'intera checklist di documenti richiesti per quella categoria di fornitore in un'unica azione, invece di aggiungere i documenti uno per uno. |

In breve: `migrate` = "fai esistere lo schema del database"; questi cinque comandi = "rendi utilizzabili nella UI
admin/portale i menu a tendina dei dati di riferimento (tipi di documento, competenze, e i *set* di livello
superiore che li raggruppano per categoria di fornitore)." Saltabili se vuoi solo cliccare in giro sulle schermate
CRUD vuote, necessari se vuoi che i flussi di documenti/competenze/servizi abbiano opzioni realistiche tra cui
scegliere.

---

## 10. Risoluzione rapida dei problemi

**Docker (Track A):**

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| `error during connect ... dockerDesktopLinuxEngine` / qualsiasi comando `docker` non riesce a raggiungere il daemon | Docker Desktop non è in esecuzione | Avvia Docker Desktop, attendi che l'icona della balena si stabilizzi, riprova |
| Il container `django` continua a riavviarsi, il log mostra ripetutamente `Waiting for MySQL to become available...` e non procede mai | Il container `mysql` non è riuscito ad avviarsi/inizializzarsi, oppure credenziali sbagliate in `.envs/.mysql.env` | `docker compose logs mysql`; conferma che i valori `DB_*` in `.envs/.mysql.env` corrispondano ai valori `MYSQL_*` |
| `port is already allocated` sulla `8000`/`13306`/`16379`/`5555` | Un altro processo (un MySQL/Redis nativo dalla Track B, o lo stack Docker di un altro progetto) sta già usando quella porta | Ferma il processo in conflitto, oppure cambia la porta di sinistra (host) in `docker-compose.yml` ulteriormente — questo progetto rimappa già MySQL/Redis su `13306`/`16379` per coesistere con un altro stack locale (vedi §8, A3) |
| Le modifiche a `requirements.txt` o al `Dockerfile` non sembrano avere effetto | L'immagine è stata messa in cache da una build precedente | `docker compose build --no-cache django` poi `docker compose up` |
| Vuoi ripartire pulito | — | `docker compose down -v` (cancella anche il volume dati di MySQL — dovrai rimigrare/riseedare) |

**Nativo (Track B):**

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| `ModuleNotFoundError: No module named 'dotenv'` | `python-dotenv` non installato | `pip install -r requirements.txt` (ora lo include — vedi §7.2) |
| `ModuleNotFoundError: No module named 'ldap'` | `python-ldap` non installato / build fallita | `pip install python-ldap` (vedi Track B, passo 2, se la build fallisce) |
| `ModuleNotFoundError: No module named 'django_auth_ldap'` | `django-auth-ldap` non installato | `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'ldap3'` | `ldap3` non installato (usato dal backend ibrido attivo) | `pip install -r requirements.txt` |
| Django non riesce a connettersi a MySQL / `2002, "Can't connect..."` | MySQL non in esecuzione, oppure `DB_HOST`/`DB_PORT` sbagliati in `.env` | Conferma che MySQL sia in esecuzione localmente e che le credenziali corrispondano a Track B, passo 4 |

**Entrambi i percorsi:**

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| File statici in 404 in dev | Di solito va bene — `DEBUG=True` serve automaticamente static/media (vedi `config/urls.py`); controlla `STATICFILES_DIRS`/`STATIC_ROOT` se personalizzati | Esegui `python manage.py collectstatic` solo se imposti `DEBUG=False` |
| Reindirizzato al login in loop | Nessun ruolo assegnato al tuo utente, oppure l'utente non è superuser/staff | Imposta `role` sull'`User` in `/admin/` oppure via `createsuperuser` |
| La modale di ricerca Embyon dà errore nell'admin Vendor | Atteso localmente — il DB esterno `redmine_test` non è raggiungibile | Ignora; è tooling BO opzionale, non richiesto per le funzionalità core |

---

## 11. Usare una copia di dati reali in locale (invece di un DB vuoto/seedato)

Il setup della Track A in §8 ti dà un'app funzionante contro un database MySQL **vuoto** (eventualmente riempito
con i dati di riferimento generici dei comandi `populate_*`/`seed_*` del §9). A volte invece vuoi navigare/testare
contro **record reali** — es. una copia della produzione ripristinata da un `mysqldump`, o qualsiasi altro
database MySQL che hai già localmente con dati caricati.

**Il modello mentale**: all'app non importa *dove* il suo database vive fisicamente — è una connessione Django +
MySQL del tutto normale in entrambi i casi. Lo stack Docker Compose della Track A si limita a eseguire per
comodità un proprio container MySQL vuoto, ma niente lo richiede. Per usare invece una copia di dati reali, devi
(1) caricare quei dati in *qualche* server MySQL raggiungibile da Docker Desktop — un'installazione nativa
sull'host, una in esecuzione in WSL2, un altro container, ovunque — e (2) puntare i container `django`/`celery*`
di questo progetto verso quel server invece che verso il proprio. Questo documento non copre *come* ottenere o
ripristinare un dump di dati (è specifico di dove lo stai recuperando) — solo come collegarlo una volta che è in
esecuzione da qualche parte.

> **Nota di sicurezza**: ogni esempio qui sotto usa segnaposto (`<...>`). Gli hostname/porte/credenziali reali per
> qualsiasi database a cui ti connetti appartengono **solo** a `.envs/.mysql.env` (già escluso da git via
> `.envs/*`) — mai in un documento, commit, o script. Se delle credenziali reali finiscono per errore incollate in
> una chat/terminale/file, trattale come compromesse e ruotale, indipendentemente da dove sia finito l'incolla.

### 11.1 Prima di collegare qualsiasi cosa

**Controlla i conflitti di porta.** Se il tuo server MySQL esterno gira sullo stesso host di Docker Desktop e
ascolta sulla `3306` di default, conferma che nient'altro abbia già quella porta — il MySQL Docker *proprio* di
questo progetto è stato spostato sulla porta host `13306` esattamente per questo motivo (§8, A3: un altro stack
Docker locale aveva già la `3306`). Per controllare su cosa è configurato un servizio MySQL Windows e spostarlo se
necessario:

```powershell
Get-Service | Where-Object { $_.Name -like "*mysql*" }                 # find the service name
(Get-WmiObject Win32_Service -Filter "Name='<ServiceName>'").PathName  # find its --defaults-file / my.ini path
Select-String -Path "<path to my.ini>" -Pattern "^port"                # check the configured port

# To change it (needs an elevated/Administrator PowerShell — ProgramData is admin-only):
$path = "<path to my.ini>"
(Get-Content $path) -replace '^port=3306$', 'port=<new port>' | Set-Content -Encoding ascii $path
Restart-Service <ServiceName>
```

> **Non è solo per il cambio di porta iniziale — riguarda ogni sessione.** Avviare/fermare il servizio MySQL
> nativo (es. `MySQL80`) richiede sempre una PowerShell **elevata** (Amministratore), non solo la prima volta che
> ne cambi la porta:
> ```powershell
> Start-Service MySQL80   # prima di lavorare
> Stop-Service MySQL80    # a fine sessione, se vuoi liberare la porta/risorse
> Get-Service MySQL80 | Select-Object Name, Status   # per controllare lo stato
> ```
> Se stai facendo eseguire questi comandi a un agente/assistente senza accesso admin (com'è il caso di un
> ambiente di sviluppo assistito da AI tipico), questi due comandi vanno lanciati manualmente **a ogni avvio e
> arresto** della sessione di lavoro, non solo durante il setup iniziale di §11.1 — insieme all'avvio di Docker
> Desktop stesso (§8, A1), che pure va fatto manualmente se non è già in esecuzione.

**Fai prima un backup dei dati.** `compose/django/start` esegue `python manage.py makemigrations` e `migrate`
**automaticamente ogni volta che il container `django` si avvia** — contro qualsiasi database sia attualmente
configurato. Se la copia a cui ti stai collegando non è già allo stato di migrazione esatto di questo branch
(verificalo con `SELECT app, MAX(name) FROM django_migrations GROUP BY app;` su di essa), Django applicherà
silenziosamente qualsiasi migrazione mancante nel momento in cui il container si avvia. Di solito va bene (è così
che porteresti aggiornata una copia più vecchia), ma modifica comunque lo schema di quel database — fai un backup
`mysqldump` prima di collegarlo la prima volta, così hai qualcosa da cui ripristinare se una migrazione fa
qualcosa che non ti aspettavi:

```bash
mysqldump -h <host> -P <port> -u <user> -p'<password>' --routines --triggers --single-transaction <db_name> > backup.sql
```

### 11.2 Punta lo stack Docker su di esso

Modifica il blocco `DB_*` di `.envs/.mysql.env` (lascia `MYSQL_ROOT_PASSWORD`/`MYSQL_DATABASE`/`MYSQL_USER`/
`MYSQL_PASSWORD` così come sono — configurano solo il servizio `mysql` di docker-compose, che diventa inutilizzato
ma innocuo una volta che `DB_HOST` punta altrove; fermalo con `docker compose stop mysql` se preferisci non
lasciarlo in esecuzione):

```dotenv
DB_ENGINE=django.db.backends.mysql
DB_NAME=<your database name>
DB_USER=<user>
DB_PASSWORD=<password>
DB_HOST=host.docker.internal
DB_PORT=<port from 11.1>
```

`host.docker.internal` è il nome DNS speciale di Docker Desktop per raggiungere la macchina host dall'interno di
un container (funziona sul setup Docker Desktop per Mac/Windows a cui punta questo documento; su Docker Linux
nativo dovresti invece usare `network_mode: host` oppure `extra_hosts:
["host.docker.internal:host-gateway"]`). Se i tuoi dati vivono invece in un altro container o in un MySQL nativo
di WSL2, usa invece l'indirizzo/nome servizio raggiungibile di quell'host.

Poi ricrea i container così che recepiscano effettivamente il nuovo file env (un semplice restart dei container
esistenti **non** rilegge `env_file`; un `down`/`up` completo sì):

```bash
docker compose down
docker compose up -d
docker compose logs django --tail=50   # watch for "Applying <app>.<migration>... OK" and confirm no errors
```

Verifica che i dati reali siano presenti:

```bash
docker compose exec django python manage.py shell -c "from vendor_management_system.vendors.models import Vendor; print(Vendor.objects.count())"
```

### 11.3 Ottenere accesso admin su un database copiato

Un database copiato porta con sé le proprie righe di `users_user` — ma gli account esistenti spesso **non
riescono ad accedere localmente**: gli account con `is_ldap_user=True` sono stati creati con
`set_unusable_password()` (nessuna password locale) quindi, con LDAP disabilitato localmente
(`LDAP_ENABLED=False`, il default consigliato — vedi §7, punto 7), non possono autenticarsi per nessuna via finché
non gliene dai una. Due modi per entrare:

**Opzione A — nuovo account locale** (la più semplice, non tocca i dati esistenti):
```bash
docker compose exec django python manage.py createsuperuser
```

**Opzione B — promuovi/riutilizza un account esistente:**
```bash
# 1. Set a real local password (interactive prompt, not logged/stored in shell history)
docker compose exec django python manage.py changepassword <email>
```
```bash
# 2. Promote to admin via the ORM — not a raw `UPDATE users_user` statement. Reasons: admin login needs BOTH
#    is_superuser AND is_staff set together (easy to miss with raw SQL), and going through .save() keeps you on
#    the model's real code path (vendor_management_system/users/models.py) instead of bypassing it.
docker compose exec django python manage.py shell -c "
from vendor_management_system.users.models import User
u = User.objects.get(email='<email>')
u.is_superuser = True
u.is_staff = True
u.is_ldap_user = False
u.save()
"
```

> **Perché ribaltare anche `is_ldap_user` a `False`**: `UserAdmin.save_model()` in
> `vendor_management_system/users/admin.py` chiama `obj.set_unusable_password()` ad **ogni** salvataggio dal
> pannello Admin ogniqualvolta `is_ldap_user=True`. Se lasci quel flag a `True` dopo aver dato all'account una
> password locale, la *prossima* volta che qualcuno modifica questo utente in `/admin/` (ruolo, collegamento al
> fornitore, qualsiasi cosa), la password locale viene silenziosamente cancellata di nuovo senza alcun avviso.
> Guida anche altri comportamenti della UI Admin mentre è `True`: `email`/`name` diventano di sola lettura e il
> campo password viene nascosto dal form. Vedi [docs/LDAP.md](LDAP.md) per il quadro completo di cosa
> `is_ldap_user` influenza e cosa no.

### 11.4 Tornare a un database locale vuoto e pulito

Riporta il blocco `DB_*` di `.envs/.mysql.env` ai default della Track A del §8, A2 (`DB_HOST=mysql`,
`DB_PORT=3306`, `DB_NAME=vms_local`, `DB_USER=vms_user`, `DB_PASSWORD=vms_dev_password`), poi `docker compose
down` seguito da `docker compose up -d`.

---

*Generato da una lettura di `docs/*.md`, `config/*.py`, `docker-compose.yml`, `compose/django/*`,
`requirements*.txt`, `vendor_management_system/**` (modelli, urls, viste, admin) alla data del branch `release2`.
Aggiornato il 2026-09-15 con i riscontri dell'ispezione diretta della VM di produzione (versioni OS/Python/MySQL/
Redis, `ps aux`, configurazione Apache, e il `pip freeze` reale del venv), da un'esecuzione Docker locale
end-to-end verificata (`docker compose up --build`, migrazioni, pagina di login, worker/beat Celery, Flower), e da
un percorso verificato di collegamento di un database copiato localmente (§11) sul branch
`feature/AIDEV-14-portale-fornitori`.*
