"""Impostazioni per la suite pytest "veloce" (locale, senza Docker/MySQL).

Eredita tutto da config.settings ma sostituisce il database con SQLite
in-memory: i test che usano @pytest.mark.django_db girano scrivendo
davvero su un database reale (non mockato), solo temporaneo e locale,
invece che su MySQL. Usata da scripts/run_fast_tests.py (vedi anche
CLAUDE.md). La suite completa via Docker continua a usare config.settings
con MySQL vero.
"""

from config.settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
