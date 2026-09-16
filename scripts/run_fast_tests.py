"""Esegue la suite pytest "veloce": SQLite in-memory, no migrazioni, no LDAP.

Usata dal git hook di pre-commit (vedi .pre-commit-config.yaml, hook
"pytest-fast") e a mano per un feedback rapido in locale, senza bisogno di
Docker/MySQL/python-ldap. Vedi CLAUDE.md, sezione Test, per i dettagli e per
la suite completa (Docker + MySQL reale), che resta il source of truth prima
di un merge.

Uso:
    python scripts/run_fast_tests.py
    python scripts/run_fast_tests.py vendor_management_system/vendors
"""

import os
import sys

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"
os.environ.setdefault("LDAP_ENABLED", "False")
# django-redis 5.4.0 (pin di produzione) valida che CACHES LOCATION non sia
# vuoto già alla costruzione del client, prima di qualsiasi tentativo di
# connessione - senza REDIS_URL fallisce con "Missing connections string"
# anche se IGNORE_EXCEPTIONS=True. Non serve un Redis reale in esecuzione:
# IGNORE_EXCEPTIONS gestisce già gli errori di connessione veri.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(["--no-migrations", *sys.argv[1:]]))
