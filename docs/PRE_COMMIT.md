# Pre-commit — lint, formattazione e test automatici ad ogni commit

Questo repo usa [pre-commit](https://pre-commit.com/) per far girare automaticamente controlli di qualità
(lint/formattazione con **ruff**, igiene di base, e una suite pytest veloce) su ogni commit, prima che il
codice entri nella cronologia. Questo documento copre **come installarlo** e **dove/quando gira**. Per i
dettagli sulla suite di test (veloce vs. completa) vedi anche `CLAUDE.md`.

## Installazione

Un solo file di dipendenze (`requirements.txt`), Python **3.12** (stessa versione della VM di produzione):

```powershell
# Solo la prima volta, se py -3.12 non trova nulla:
py install 3.12

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pre-commit install
```

`pre-commit install` registra l'hook Git (`.git/hooks/pre-commit`) nel repo locale — va rifatto una volta per
ogni checkout del repo (non è qualcosa che si "installa" a livello globale sulla macchina).

> **Nota Windows nativo**: `requirements.txt` installa senza bisogno di Visual C++ Build Tools o dell'SDK
> OpenLDAP. Questo è intenzionale — vedi i commenti in testa al file e in `CLAUDE.md` ("Ambiente Python") per
> il motivo (versioni con wheel Windows disponibili, `python-ldap`/`django-auth-ldap` saltati su Windows perché
> non servono con `LDAP_ENABLED=False`, il default locale).

## Dove e quando gira

Ci sono **due punti di innesco indipendenti**, entrambi già configurati in questo repo:

1. **Ad ogni `git commit`** (dopo `pre-commit install`) — gira sui soli file **staged**, bloccando il commit se
   qualche hook fallisce e non riesce ad auto-correggersi.
2. **Ad ogni modifica fatta da Claude Code** (se usi l'estensione/CLI) — un hook `PostToolUse` configurato in
   `.claude/settings.json` esegue `pre-commit run --files <file>` subito dopo ogni `Write`/`Edit` di Claude,
   segnalando in chat quello che non è stato auto-corretto. Non richiede nulla in più oltre all'installazione
   sopra.

Per lanciarlo manualmente in qualsiasi momento (utile per controllare tutto il repo, non solo i file staged):

```powershell
pre-commit run --all-files      # tutti i file del repo
pre-commit run                  # solo i file staged
pre-commit run <hook-id>        # un singolo hook, es. `pre-commit run ruff-check`
```

> **Prima esecuzione su `--all-files`**: ruff non ha mai visto gran parte di questo codice legacy, quindi la
> prima volta riformatterà/segnalerà molto più che nei run successivi (che toccano solo i file davvero
> modificati). È normale — valuta di farlo in un commit dedicato invece che mischiarlo a un cambio funzionale.

## Cosa controlla (`.pre-commit-config.yaml`)

| Hook | Cosa fa |
|---|---|
| `ruff-check` (con `--fix`) | Lint Python (regole `E`, `F`, `I`, `UP`, `B` — vedi `pyproject.toml`), auto-corregge quello che può |
| `ruff-format` | Formattazione Python (stile Black-like) |
| `trailing-whitespace` | Rimuove spazi bianchi a fine riga |
| `end-of-file-fixer` | Garantisce una newline finale |
| `check-yaml` / `check-toml` / `check-json` | Verifica che i file di config non abbiano errori di sintassi |
| `check-merge-conflict` | Blocca marker di conflitto Git dimenticati (`<<<<<<<`, ecc.) |
| `check-added-large-files` | Blocca file >1MB aggiunti per errore |
| `detect-private-key` | Blocca chiavi private accidentalmente committate |
| `pytest-fast` (hook locale, `scripts/run_fast_tests.py`) | Fa girare l'intera suite pytest su SQLite in-memory, senza migrazioni, senza LDAP — **niente Docker/MySQL richiesto**. Vedi `CLAUDE.md`, sezione Test, per i dettagli e per la suite completa (Docker + MySQL vero), che resta il riferimento definitivo prima di un merge su `master`. |

## Problemi comuni

| Sintomo | Causa | Soluzione |
|---|---|---|
| `pre-commit: comando non trovato` | Il venv con `pre-commit` installato non è attivo | `.venv\Scripts\Activate.ps1` prima di lanciare `pre-commit`/`git commit` |
| L'hook `pytest-fast` fallisce con `ImproperlyConfigured: Missing connections string` | Non dovrebbe succedere: `scripts/run_fast_tests.py` imposta già un `REDIS_URL` placeholder | Verifica di non aver sovrascritto `REDIS_URL` con una stringa vuota nell'ambiente |
| Il primo `pre-commit run --all-files` riformatta decine di file | Normale, vedi sopra | Fallo in un commit dedicato |
| `pip install -r requirements.txt` fallisce compilando `mysqlclient`/`python-ldap` | Stai usando una versione di Python diversa da 3.12, oppure un OS/architettura non coperti dalle wheel disponibili su PyPI per i pin in `requirements.txt` | Usa Python 3.12 (`py install 3.12`); se il problema persiste, vedi i commenti in testa a `requirements.txt` |
