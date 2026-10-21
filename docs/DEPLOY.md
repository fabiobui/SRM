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

Una volta per ambiente, dopo il primo `migrate` che porta `documents/0007` (rinomina DocumentType in
DocumentCatalog) e le app proxy `services`/`competences`, riallinea i permessi admin degli utenti staff non
superuser: senza, perdono l'accesso al Catalogo Documenti e alle sezioni Servizi/Requisiti (403):

```bash
.venv/bin/python data_migration_scripts/allinea_permessi_admin.py --dry-run
.venv/bin/python data_migration_scripts/allinea_permessi_admin.py
```

Lo script copia ogni permesso esistente sul modello nuovo corrispondente e non ne toglie mai; è idempotente.

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

Quindi in produzione si migra in due tempi, con il report in mezzo:

```bash
# 1. Fino alla 0042: popola il catalogo geografico, non cancella nulla.
.venv/bin/python manage.py migrate vendors 0042
# 2. Report dell'esito previsto (sola lettura).
.venv/bin/python data_migration_scripts/report_competence_zone_migration.py
# 3. Solo dopo aver rivisto il report: resto delle migrazioni (0043, 0044, ...).
.venv/bin/python manage.py migrate
```

Il report ha bisogno del catalogo geografico già popolato (lo semina la
`0041`): lanciato prima, considererebbe tutto senza match.

Lo script è di sola lettura e scrive
`data_migration_scripts/reports/competence_zone_migration.csv` con l'esito
previsto fornitore per fornitore. Se i casi `NESSUN_MATCH` + `PARZIALE`
superano il 30% lo segnala esplicitamente: conviene allora estendere gli alias
in `vendors/migrations/0043_migrate_competence_zones.py` prima di procedere.

Come interpreta il testo la `0043`:

- i nomi noti si riconoscono anche separati solo da spazi ("LAZIO ROMA");
- una regione citata insieme a una sua provincia vale solo la provincia
  ("Puglia - Taranto" → Taranto); citata da sola vale tutte le sue province;
- forme brevi di province e comuni presenti nei dati legacy sono ricondotti
  alla loro provincia tramite alias ("Monza", "Jesi" → AN, ...);
- le macro-aree ("Nord Italia", "Centro") non vengono mai indovinate;
- una zona nominata senza regole utilizzabili viene interpretata dal suo nome.
  Le regole che puntano agli id delle fixture geografiche vengono risolte per
  codice anche dove la geografia era stata creata con altri id.

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

### Sostituzione dei fornitori IGEAM

Va rifatta a ogni nuovo export della query IGEAM, su **ogni ambiente**. Ogni
carico sostituisce i fornitori Igeam già censiti: su test quelli del
censimento precedente, in produzione quelli eventualmente presenti. I dettagli
(mappatura dei campi, esiti) sono in
[SCRIPT_IMPORT.md](SCRIPT_IMPORT.md#data_migration_scriptsimport_igeam_vendorspy).

1. Dopo `git pull` e `migrate`, copia l'export sulla VM. È fuori da git perché
   contiene dati fornitore:

   ```bash
   # dal proprio PC
   scp "Fornitori_IGEAM_Attivi_Portale_v2.xlsx" <utente>@<vm>:<percorso-repo>/data_migration_scripts/input/
   ```

2. Analisi (sola lettura), da rifare su ogni ambiente:

   ```bash
   .venv/bin/python data_migration_scripts/import_igeam_vendors.py analizza \
       -f data_migration_scripts/input/Fornitori_IGEAM_Attivi_Portale_v2.xlsx
   ```

   Controlla il riepilogo per esito e rivedi
   `data_migration_scripts/reports/igeam_nuovi.csv`. Le righe da non caricare si
   possono togliere dal file.

3. Sostituzione, prima in prova e poi reale. Prima del reale, fai un dump del
   database (non c'è rollback automatico):

   ```bash
   .venv/bin/python data_migration_scripts/import_igeam_vendors.py carica \
       -f data_migration_scripts/reports/igeam_nuovi.csv --dry-run
   .venv/bin/python data_migration_scripts/import_igeam_vendors.py carica \
       -f data_migration_scripts/reports/igeam_nuovi.csv
   ```

4. Conserva `data_migration_scripts/reports/igeam_inseriti.csv`. Poi verifica da
   Admin → Fornitori con il filtro *Società Embyon = Igeam*. Non serve riavviare
   Apache per vedere i dati: il riavvio del punto precedente basta per il codice.
## Verifica

- Apri l'app nel browser e controlla che il login risponda normalmente.
- In caso di errori: `sudo tail -n 50 /var/log/apache2/error.log`.

## Celery e promemoria scadenze

Se sulla VM è attivo un worker/beat Celery per questa app, riavvialo allo stesso modo dopo il pull (verifica il
nome del servizio con `systemctl list-units | grep celery` se non lo conosci già).

I promemoria scadenze al fornitore partono dal task Celery Beat `send_expiry_reminders_task` (vedi §6 di
`PROJECT_OVERVIEW_AND_LOCAL_SETUP.md`). Dove beat non gira, lo stesso job può girare da cron di sistema. Sulla VM di
produzione (verificato il 2026-10-12) non c'è un worker/beat Celery di SRM: il job è un cron dell'utente `redmine`:

```bash
0 7 * * * cd /home/redmine/SRM && .venv/bin/python manage.py send_expiry_reminders >> /home/redmine/SRM/send_expiry_reminders.log 2>&1
```

Verifica con `crontab -l | grep send_expiry_reminders`. Usa un solo meccanismo per VM: il registro degli invii evita
i doppioni, ma due job che girano insieme sono comunque un errore di configurazione.

Imposta anche `PORTAL_BASE_URL` nel `.env` della VM (URL pubblico del portale, senza `/` finale), altrimenti
l'email parte senza link al portale.

### Attivazione dei promemoria in produzione

Con `EMAIL_REDIRECT_TO` vuoto il job scrive ai fornitori reali. Prima di lasciarlo attivo:

1. controlla `PORTAL_BASE_URL` nel `.env`;
2. verifica l'elenco del giorno con il dry-run, che non invia e non registra nulla:

   ```bash
   .venv/bin/python manage.py send_expiry_reminders --dry-run --date AAAA-MM-GG
   ```

   Un fornitore riceve la mail solo se ha attivo "Notifiche scadenze via email" e se il suo documento o requisito
   ha "Richiede Rinnovo" (vedi §6 di `PROJECT_OVERVIEW_AND_LOCAL_SETUP.md`);
3. dopo il primo run del cron, controlla il log:

   ```bash
   tail -n 50 /home/redmine/SRM/send_expiry_reminders.log
   ```

### Disattivare il redirect delle email (VM test e produzione)

Il redirect (`EMAIL_REDIRECT_TO`, vedi `core/emails.py`) è nel `.env` della VM, fuori da git: va tolto a mano su
ciascuna VM per le email dell'accesso al portale (invito, reset password) e per i promemoria.

1. nel `.env` della VM lascia `EMAIL_REDIRECT_TO=` vuoto (oppure togli la riga);
2. riavvia l'applicazione, perché le variabili sono lette solo all'avvio, e Celery per il job dei promemoria:

   ```bash
   sudo systemctl restart apache2
   ```

3. controlla `PORTAL_BASE_URL`, `DEFAULT_FROM_EMAIL=albo.fornitori@fulgard.com` e il permesso Send As della casella
   condivisa (§8 A8 di `PROJECT_OVERVIEW_AND_LOCAL_SETUP.md`);
4. verifica con un invito a un fornitore di prova: senza redirect la mail parte verso l'indirizzo vero del fornitore.

Con il redirect vuoto ogni email esce ai destinatari reali: attivalo solo quando i dati sul DB sono quelli giusti.

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
