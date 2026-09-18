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

Controlla se serve anche `collectstatic` (necessario solo con `DEBUG=False` — vedi
[PROJECT_OVERVIEW_AND_LOCAL_SETUP.md, §10](PROJECT_OVERVIEW_AND_LOCAL_SETUP.md)):

```bash
grep -E "^DEBUG=" .env
```

Se il valore è `False`:

```bash
.venv/bin/python manage.py collectstatic --noinput
```

Riavvia Apache — necessario perché `mod_wsgi` tiene il processo Django caricato nei worker: un `git pull` da solo
non fa ricaricare il codice:

```bash
sudo systemctl restart apache2
sudo systemctl status apache2      # conferma che sia ripartito senza errori
```

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
