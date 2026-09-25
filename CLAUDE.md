# CLAUDE.md

SRM / VMS (Vendor Management System): applicazione web Django per Fulgard per la gestione del ciclo di vita dei
fornitori (qualificazione, documenti di compliance, competenze, valutazioni, ordini di acquisto). Vedi
[README.md](README.md) e [docs/PROJECT_OVERVIEW_AND_LOCAL_SETUP.md](docs/PROJECT_OVERVIEW_AND_LOCAL_SETUP.md) per
l'overview completa e il setup locale (Docker o nativo).

## Azioni da fare sempre

- **Mai hardcodare segreti** (password, API key, host/IP interni) in codice, script o commit — usa variabili
  d'ambiente (`.env`/`.envs/`, già in `.gitignore`). Questo repo ha già avuto credenziali reali committate per
  errore (vedi `manual_scripts/testldap.py`): se ne trovi altre, segnalale invece di darle per buone.
- **Esegui la suite pytest rilevante** dopo ogni modifica a codice Python, prima di considerare il lavoro concluso
  (`pytest` dalla root, oppure `pytest tests/test_x.py::test_y` per un test mirato).
- **Lascia agire pre-commit** sui file toccati (l'hook Claude Code lo fa già in automatico dopo ogni `Write`/`Edit`
  — vedi sotto) e correggi quello che segnala prima di finire.
- Se aggiungi un nuovo script una-tantum, **mettilo nella cartella giusta invece che nella root**:
  `data_migration_scripts/` (import/fix/cancellazioni dati), `shell_scripts/` (script shell di setup/avvio),
  `manual_scripts/` (tool diagnostici manuali, mai eseguiti da pytest/CI). Vedi la sezione layout più sotto.
- Se cambi `vendor_management_system/*/models.py`, genera/controlla le migrazioni (`python manage.py
  makemigrations --check --dry-run`) prima di finire.
- **Ogni nuovo sviluppo o fix applicativo deve avere il proprio set di unit test**, nella cartella appropriata:
  dentro `vendor_management_system/<app>/tests/` se riguarda una app Django esistente, dentro `tests/` nella root
  se è trasversale/di configurazione (vedi sezione Test più sotto). Non consegnare codice nuovo senza test. Non
  vale per gli script una tantum di `data_migration_scripts/`/`shell_scripts/`/`manual_scripts/` (vedi layout più
  sotto): non richiedono una suite di test dedicata, verificali con un'esecuzione reale (es. `--dry-run` quando
  disponibile) prima di consegnarli. Quando i test servono, preferisci pochi test mirati sul comportamento
  richiesto invece di una copertura esaustiva di ogni combinazione di input: coprono meglio l'intento e restano
  più facili da mantenere.
- **La documentazione va sempre scritta o aggiornata in italiano** (README, `docs/*.md`, `CLAUDE.md`, commenti e
  docstring destinati a chi mantiene il progetto) — coerente con lo stile già usato in tutto il repo.
- **Se stai testando su Docker (Track A) e modifichi codice Python mentre il container `django` è già in
  esecuzione, fai `docker compose restart django` prima di verificare la modifica nel browser.** Il container
  gira `runserver_plus` (Werkzeug), che in teoria fa autoreload, ma su Docker Desktop per Windows con bind mount
  (`.:/app` in `docker-compose.yml`) le modifiche fatte da fuori al container spesso non vengono rilevate in
  modo affidabile: il refresh del browser da solo non basta.

## Ambiente Python

- Gestione dipendenze via **pip**, **un solo file**: `requirements.txt` — **non uv**. Contiene sia le dipendenze
  di produzione sia il tooling di sviluppo (ruff, pre-commit, requests), in una sezione separata in fondo al
  file (innocuo avere quei pacchetti anche in produzione).
- **Usa Python 3.12** (`py install 3.12` se il launcher `py` non lo trova già — vedi l'errore "No runtime
  installed that matches 3.12"), la stessa versione della VM di produzione (Python 3.12.7). Su Python 3.13
  alcuni pin non hanno wheel Windows disponibili (vedi punto sotto) e andrebbero aggiornati caso per caso.
- Setup: `py -3.12 -m venv .venv` → `.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt`.
- **Perché questo file installa senza build tools nativi su Windows, con Python 3.12**, pur restando (quasi) il
  pip freeze esatto della produzione — due deviazioni deliberate, documentate anche nell'intestazione del file:
  - `mysqlclient` e `argon2-cffi-bindings` sono stati aggiornati di una versione patch (2.2.0→2.2.7,
    21.2.0→26.1.0): le versioni originali non pubblicano wheel Windows per cp312, quelle nuove sì. Nessun
    cambio di comportamento, solo pacchetti precompilati disponibili invece di dover compilare da sorgente.
  - `django-auth-ldap`/`python-ldap` hanno il marker `; sys_platform != "win32"`: `python-ldap` non ha **mai**
    pubblicato una wheel Windows (serve l'SDK OpenLDAP + un compilatore C per buildarlo da sorgente). Su
    Windows vengono semplicemente saltati — sicuro perché `config/settings.py` li importa solo se
    `LDAP_ENABLED=True`, e in locale resta sempre `False` (vedi sezione Test). Linux/Docker/produzione
    (`LDAP_ENABLED=True` lì) li installano e usano normalmente, marker o meno.
- Avvio locale (per far girare l'app vera, non solo pre-commit/test): vedi Track A (Docker, consigliata — gestisce
  lei i pacchetti di sistema per `mysqlclient`/`python-ldap`) o Track B (nativa) in
  `docs/PROJECT_OVERVIEW_AND_LOCAL_SETUP.md`.

## Linting & formattazione

- **ruff** è configurato in `pyproject.toml` (`select = ["E", "F", "I", "UP", "B"]`, `target-version = "py312"`).
- Applicato via **pre-commit** (`.pre-commit-config.yaml`): ruff check+format, più hook di igiene di base
  (trailing whitespace, EOF fixer, validità YAML/TOML/JSON, marker di merge conflict, file grandi, chiavi private).
- **L'intero repo è già stato passato da `ruff-check`/`ruff-format`** (pulizia lint/formattazione completa,
  AIDEV-42): `pre-commit run --all-files` ora produce diff minimi, limitati ai file davvero toccati da una
  modifica — non deve più riformattare a raffica file legacy mai visti da ruff.
- **Attenzione all'hook su un file toccato per la prima volta da ruff** (es. un file nuovo, o uno escluso in
  passato da `pyproject.toml`): l'hook Claude Code fa girare `ruff-format` sull'INTERO file ad ogni `Write`/
  `Edit`, anche per una modifica di una riga — su un file mai passato da ruff questo produce un diff enorme e
  fuori scopo. Vale anche per i `.md`: `ruff-format` riformatta pure i blocchi ` ```python ` incorporati nella
  documentazione (es. gli esempi di codice in `README.md`), non solo i file `.py`. Per una modifica chirurgica a
  un file del genere, applicala con uno script (es. `python -c "..."` via Bash) invece che con `Write`/`Edit`,
  così l'hook non scatta e il diff resta minimo. Se invece emergono violazioni `ruff-check` non auto-fixabili
  (tipicamente E501 su un file toccato per la prima volta), **sistemale subito, nello stesso giro di
  modifiche** — non rimandarle a un commit "solo formattazione" separato: una volta che il file è stato toccato
  anche una sola volta da `Write`/`Edit` i numeri di riga cambiano rispetto all'ultimo commit, quindi a
  posteriori non è più possibile isolare in modo pulito un commit di solo reformat che si applichi sulla
  versione originale (serve riscrivere la cronologia, non praticabile su un branch già pushato).
- Installa il git hook una volta: `pre-commit install` (così gira anche su ogni `git commit`).
- Un hook Claude Code (`.claude/settings.json` → `PostToolUse` su `Write|Edit`) esegue già
  `pre-commit run --files <file>` automaticamente dopo ogni modifica di Claude, segnalando in chat quello che non
  è stato auto-corretto. Richiede `pre-commit` installato nello stesso Python che esegue l'hook (vedi sopra —
  `requirements.txt`, sezione tooling in fondo al file).

## Test

- **pytest** + **pytest-django**. Due posti dove vivono i test, entrambi raccolti automaticamente da pytest:
  - `tests/` nella root — test trasversali/di configurazione (URL, swagger, integrazioni esterne mockate).
  - `vendor_management_system/<app>/tests/` — test per-app (modelli, viste, factory `factory_boy`/`Faker`).
- Nessun test deve fare chiamate di rete reali: usa `unittest.mock.patch` per mockare HTTP/servizi esterni (vedi
  `tests/test_ricerca_anagrafica.py`).
- **Due modalità di esecuzione, stessi test:**
  - **Veloce, locale, senza Docker (default per pre-commit)**: `config/settings_test.py` sostituisce il database
    con SQLite in-memory (`@pytest.mark.django_db` scrive/legge davvero su un DB reale, solo temporaneo — non è
    mock dell'ORM) e non richiede `mysqlclient`. Serve anche a evitare `python-ldap`/`django-auth-ldap`: con
    `LDAP_ENABLED=False` (default locale) `config/settings.py` non li importa nemmeno (vedi sotto). Comando:
    `DJANGO_SETTINGS_MODULE=config.settings_test LDAP_ENABLED=False pytest --no-migrations`. `--no-migrations`
    crea le tabelle direttamente dai model attuali invece di rigiocare tutta la cronologia delle migrazioni —
    necessario perché un paio di migrazioni vecchie (`vendors/migrations/0019_...`, `0020_...`) usano
    `INFORMATION_SCHEMA`/`DATABASE()`, sintassi solo-MySQL che romperebbe la creazione del DB di test su SQLite.
    Il git hook di pre-commit (`.pre-commit-config.yaml`, hook `pytest-fast`) esegue esattamente questo comando
    ad ogni commit tramite `scripts/run_fast_tests.py`, che imposta anche un `REDIS_URL` placeholder: senza,
    `django-redis==5.4.0` (il pin di produzione) solleva `ImproperlyConfigured` già alla costruzione del client
    cache, prima ancora di provare a connettersi — non serve un Redis reale in esecuzione, `IGNORE_EXCEPTIONS`
    gestisce già i veri errori di connessione.
  - **Completa, con Docker (source of truth prima di un merge)**: `docker compose exec django pytest` — usa
    `config.settings` con MySQL vero e rigioca tutta la cronologia delle migrazioni. La modalità veloce è un
    proxy utile per un feedback immediato, ma SQLite maschera differenze di comportamento specifiche di MySQL
    (collation, le migrazioni `INFORMATION_SCHEMA` sopra, ecc.) — non saltare la suite Docker prima di un merge
    su `master`.
- **LDAP negli import di `config/settings.py`**: `import ldap` / `django_auth_ldap` sono dentro `if
  LDAP_ENABLED:` — non richiesti per lavorare in locale (`LDAP_ENABLED=False` di default). Sono comunque dead
  code anche quando abilitati: il backend realmente usato (`HybridAuthBackend`, `AUTHENTICATION_BACKENDS`) usa
  `ldap3` e legge `AUTH_LDAP_*` come stringhe via `getattr()`, senza mai toccare gli oggetti `LDAPSearch`
  costruiti in quel blocco — un'eventuale pulizia di quel codice morto è indipendente da questo lavoro.

## Sicurezza — follow-up noti (non normalizzare questi test per farli passare)

- **`vendor_management_system/vendors/dashboard_views.py::dashboard_stats_api`** (`GET
  /vendors/dashboard-stats/`) non ha **nessun controllo di autenticazione**: chiunque può leggere conteggi/rischio
  fornitori senza login, a differenza delle altre viste API dello stesso file (che usano
  `QueryParameterTokenAuthentication` + `IsAuthenticated`). I test `test_api_without_token` e
  `test_dashboard_stats_api` in `vendor_management_system/vendors/tests/test_dashboard.py` sono skippati con
  motivazione esplicita invece di essere riscritti per accettare lo stato attuale — richiede una scelta
  consapevole (ripristinare l'auth + eventualmente il payload più ricco che il test si aspettava) in un cambio
  dedicato, non un fix silenzioso dentro un giro di refactor.

## Layout del repo (script fuori dall'app Django)

- `data_migration_scripts/` — script una-tantum di import/fix/cancellazione dati (richiedono
  `DJANGO_SETTINGS_MODULE`, vanno lanciati dalla root: `python data_migration_scripts/<script>.py`).
  `data_migration_scripts/reports/` contiene i CSV di esito generati da questi script (es.
  `embyon_match_report.csv`, da `import_embyon_codes.py`) — cartella scelta apposta perché **non** è servita da
  Django, a differenza di `static/`: i report possono contenere dati fornitore (P.IVA, C.F., ragioni sociali).
- `shell_scripts/` — script shell di setup/avvio locale (`setup_ldap.sh`, `start_django.sh`,
  `test_production.sh`), anch'essi da lanciare dalla root del repo.
- `manual_scripts/` — tool diagnostici manuali (es. `testldap.py`), mai raccolti da pytest, mai da eseguire in CI.
- `env_example/` — file di esempio per variabili d'ambiente (es. `.env.ldap.example`), solo placeholder, mai
  valori reali.
- `vendor_management_system/` — le app Django vere e proprie (vedi §3 di `docs/PROJECT_OVERVIEW_AND_LOCAL_SETUP.md`
  per la mappa dei moduli); gli script di import/seed specifici di un'app restano lì dove già sono.
