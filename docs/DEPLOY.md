# Deploy in ambiente di test

Procedura per aggiornare il codice sulla VM di test a partire dal branch `master` (dopo che le PR sono state
mergiate su GitHub). Entrambe le VM (test e produzione) servono l'app con **Apache + `mod_wsgi`**, che integra il
processo Django direttamente nei worker di Apache — vedi
[PROJECT_OVERVIEW_AND_LOCAL_SETUP.md, §7 punto 7](PROJECT_OVERVIEW_AND_LOCAL_SETUP.md). Per le differenze rispetto
alla produzione vedi la tabella in fondo.

## Prerequisiti

- Accesso SSH alla VM di test.
- Il repo è già clonato con un venv Python in `.venv/` e un `.env` già configurato — il pull non li tocca
  (`.env` è escluso da git).

## Procedura

Dalla VM di test:

```bash
cd /home/ubuntu/SRM
git status                        # conferma che non ci siano modifiche locali non committate
git log --oneline -1               # annota il commit attuale, utile per un rollback rapido
```

Se `git status` mostra modifiche non attese, fermati e capiscine l'origine prima di continuare — non scartarle
alla cieca.

```bash
git checkout master
git pull origin master
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
```

Usa sempre il binario dentro `.venv/bin/` esplicitamente (non `source .venv/bin/activate` + `pip`/`python` nudi):
su Ubuntu il Python di sistema è "externally managed" (PEP 668) e rifiuta `pip install` con
`error: externally-managed-environment` — capita se questi comandi finiscono per essere eseguiti in una shell/
sessione SSH diversa da quella in cui hai fatto `source`, dove il venv non risulta più attivo.

Aggiorna anche i dati di riferimento (tipi documento, requisiti/servizi, e i set che li raggruppano per
categoria fornitore — vedi [PROJECT_OVERVIEW_AND_LOCAL_SETUP.md, §9](PROJECT_OVERVIEW_AND_LOCAL_SETUP.md) per
il dettaglio di ciascun comando). `migrate` porta solo lo schema: senza questo step, nuovi censimenti aggiunti
dal codice (nuovi tipi documento/requisiti/set) restano assenti dal DB finché non li si lancia esplicitamente:

```bash
.venv/bin/python manage.py seed_geography --create-only
.venv/bin/python manage.py populate_document_types --create-only
.venv/bin/python manage.py seed_competence_sets --create-only
.venv/bin/python manage.py seed_service_sets --create-only
.venv/bin/python manage.py seed_document_sets --create-only
```

`--create-only` crea solo ciò che manca (nuovo codice/nome mai visto) e **non tocca** righe o set già
esistenti — utile perché tutti questi oggetti sono editabili da admin (nome, descrizione, lista
documenti/requisiti collegati a un set): senza questo flag, ogni deploy risincronizzerebbe anche gli
esistenti col contenuto hardcoded nello script, cancellando eventuali personalizzazioni fatte a mano. Vanno
quindi lanciati **ad ogni deploy**, non solo la prima volta — con `--create-only` è sicuro farlo
incondizionatamente.

**Non lanciare `populate_competences`** in questa sequenza: usa una codifica (`RSPP`, `ASPP`...) diversa da
quella già a catalogo (`REQ-001`, `REQ-002`...) e duplicherebbe requisiti già censiti sotto un altro codice.
Richiede un confronto manuale caso per caso, non un comando da deploy automatico.

### Prima release delle zone di competenza territoriali

Vale **solo per il deploy che introduce questa funzionalità**, una volta sola.

La migrazione `vendors/0044_remove_competence_zone_stack` cancella in modo
**irreversibile** il vecchio campo testuale `Vendor.competences_zone` e le
tabelle delle vecchie zone nominate. La migrazione `0043` prova a travasarne il
contenuto nei nuovi campi territoriali, ma quello che non riesce a interpretare
(es. macro-aree ambigue come "Nord Italia") va sistemato a mano, e dopo `0044`
non c'è più modo di sapere cosa fosse.

Quindi, **prima** di lanciare `migrate` in produzione:

```bash
.venv/bin/python data_migration_scripts/report_competence_zone_migration.py
```

Lo script è di sola lettura e scrive
`data_migration_scripts/reports/competence_zone_migration.csv` con l'esito
previsto fornitore per fornitore. Se i casi `NESSUN_MATCH` + `PARZIALE`
superano il 30% lo segnala esplicitamente: conviene allora estendere gli alias
in `vendors/migrations/0043_migrate_competence_zones.py` prima di procedere.

Il report contiene ragioni sociali: la cartella `reports/` non è servita da
Django, non spostarlo sotto `static/`.

In alternativa, si può deployare fino a `0043` e tenere `0044` per un rilascio
successivo, dopo aver sistemato i dati dall'admin.

Esegui sempre `collectstatic`, **indipendentemente dal valore di `DEBUG`**:

```bash
.venv/bin/python manage.py collectstatic --noinput
```

Il "`DEBUG=True` serve automaticamente gli statici" documentato in
[PROJECT_OVERVIEW_AND_LOCAL_SETUP.md, §10](PROJECT_OVERVIEW_AND_LOCAL_SETUP.md) vale **solo** per il dev server
locale (`runserver`/`runserver_plus`, usato da Docker): quel comando avvolge l'app in
`django.contrib.staticfiles.handlers.StaticFilesHandler`, che risolve i file al volo dalle `STATICFILES_DIRS`
tramite i finder, senza bisogno di `collectstatic`. Le VM di test e produzione girano invece su **Apache +
`mod_wsgi`** (vedi §7 punto 7), che espone direttamente `config/wsgi.py` senza quel wrapper: l'unica serving view
attiva è quella aggiunta da `config/urls.py` quando `DEBUG=True` (`urlpatterns += static(...)`), e punta a
`document_root=settings.STATIC_ROOT` — cioè alla cartella `staticfiles/` popolata da `collectstatic`, non alle
`STATICFILES_DIRS` sorgente. Su queste VM, quindi, i file statici nuovi o modificati restano in 404 finché non
si lancia `collectstatic`, a prescindere da `DEBUG` (causa esatta del bug AIDEV-85: il selettore zone di
competenza compariva senza stile e non cliccabile su test perché `geo/js/competence_area_selector.js` e
`geo/css/competence_area_selector.css` non erano mai stati copiati in `staticfiles/`).

Riavvia Apache — necessario perché `mod_wsgi` tiene il processo Django caricato nei worker: un `git pull` da solo
non fa ricaricare il codice:

```bash
sudo systemctl restart apache2
sudo systemctl status apache2      # conferma che sia ripartito senza errori
```

### Popolamento una tantum dei fornitori IGEAM

Vale **solo per il deploy che introduce la Società Embyon *Igeam***, una volta
per ambiente: prima su test, poi in produzione. I dettagli (mappatura dei
campi, esiti, rollback) sono in
[SCRIPT_IMPORT.md](SCRIPT_IMPORT.md#data_migration_scriptsimport_igeam_vendorspy).

1. Dopo `git pull` e `migrate`, che applica `vendors/0046_alter_vendor_embyon_company`,
   copia l'estrazione sulla VM. È fuori da git perché contiene dati fornitore:

   ```bash
   # dal proprio PC
   scp "IGEAM_ANAGRAFICA FORNITORI_Completa<data>.xlsx" <utente>@<vm>:<percorso-repo>/data_migration_scripts/input/
   ```

2. Analisi (sola lettura). Va rifatta **su ogni ambiente**, perché i fornitori
   già presenti cambiano da database a database:

   ```bash
   .venv/bin/python data_migration_scripts/import_igeam_vendors.py analizza \
       -f "data_migration_scripts/input/IGEAM_ANAGRAFICA FORNITORI_Completa<data>.xlsx"
   ```

   Controlla il riepilogo per esito e rivedi
   `data_migration_scripts/reports/igeam_nuovi.csv`. Le righe da non caricare si
   possono togliere dal file.

3. Caricamento, prima in prova e poi reale:

   ```bash
   .venv/bin/python data_migration_scripts/import_igeam_vendors.py carica \
       -f data_migration_scripts/reports/igeam_nuovi.csv --dry-run
   .venv/bin/python data_migration_scripts/import_igeam_vendors.py carica \
       -f data_migration_scripts/reports/igeam_nuovi.csv
   ```

4. Conserva `data_migration_scripts/reports/igeam_inseriti.csv`, che serve per
   un eventuale rollback con `delete_vendors.py`. Poi verifica da Admin →
   Fornitori con il filtro *Società Embyon = Igeam*. Non serve riavviare Apache
   per vedere i dati: il riavvio del punto precedente basta per il codice.

## Verifica

- Apri l'app nel browser e controlla che il login risponda normalmente.
- In caso di errori: `sudo tail -n 50 /var/log/apache2/error.log`.

## Se gira anche Celery

Se sulla VM è attivo un worker/beat Celery per questa app, riavvialo allo stesso modo dopo il pull (verifica il
nome del servizio con `systemctl list-units | grep celery` se non lo conosci già).

## Rollback rapido

Se qualcosa si rompe dopo il deploy:

```bash
git checkout <commit-sha-annotato-sopra>
sudo systemctl restart apache2
```

Le migrazioni di schema **non** vengono annullate da un semplice `checkout` indietro — se il deploy ha introdotto
nuove migrazioni, valuta caso per caso prima di tornare indietro col codice, per non lasciare schema e codice
disallineati.

## Differenze per la VM di produzione

Stessa procedura, ma:

| | Test | Produzione |
|---|---|---|
| Percorso repo | `/home/ubuntu/SRM` | `/home/redmine/SRM` |
| `DEBUG` (verificato) | `True` (2026-09-18) | `True` (2026-09-15) — valore non sicuro per produzione, follow-up noto e già segnalato in [PROJECT_OVERVIEW_AND_LOCAL_SETUP.md, §7 punto 8](PROJECT_OVERVIEW_AND_LOCAL_SETUP.md); non "normalizzarlo" adattando questa procedura, è fuori scope di un deploy |

Verifica comunque il valore reale con `grep -E "^DEBUG=" .env` prima di decidere se serve `collectstatic`, invece
di fidarti della tabella sopra: può cambiare nel tempo.
