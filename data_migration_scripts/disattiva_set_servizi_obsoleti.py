#!/usr/bin/env python
"""
Disattiva i Set Servizi IGEAM sostituiti dal nuovo file "FORNITORI_SET SERVIZI
con descrizioni.xlsx" (foglio SET SERVIZI). Il seed non li tocca: con
--create-only (deploy) non rimuove set già esistenti, quindi senza questo passo
resterebbero selezionabili accanto ai nuovi.

Da lanciare UNA VOLTA per ambiente, DOPO:
    python manage.py seed_service_sets --solo-igeam --update-catalog

Il set non viene cancellato: resta in tabella con is_active=False, così può
essere riattivato a mano. Se un set non esiste più lo script lo salta.

È IDEMPOTENTE. Con --dry-run esegue tutto e annulla la transazione.

Uso (dalla root del repo, dentro la venv):
    python data_migration_scripts/disattiva_set_servizi_obsoleti.py --dry-run
    python data_migration_scripts/disattiva_set_servizi_obsoleti.py
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from vendor_management_system.vendors.models import ServiceSet  # noqa: E402

# Set IGEAM della prima versione, non più presenti nel file.
SET_OBSOLETI = [
    "RISCHIO MINERARIO",
    "AMBIENTE",
    "FORMAZIONE",
    "VALUTAZIONE RISCHI",
    "STRUMENTI DI MISURA",
]


def log(msg):
    print(f"[set-obsoleti] {msg}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="esegue tutto e annulla la transazione",
    )
    args = parser.parse_args()

    with transaction.atomic():
        for name in SET_OBSOLETI:
            service_set = ServiceSet.objects.filter(name=name).first()
            if service_set is None:
                log(f"'{name}': non presente, salto.")
                continue
            if not service_set.is_active:
                log(f"'{name}': già disattivato.")
                continue
            service_set.is_active = False
            service_set.save(update_fields=["is_active"])
            log(f"'{name}': disattivato.")

        if args.dry_run:
            transaction.set_rollback(True)
            log("--dry-run: modifiche annullate.")


if __name__ == "__main__":
    main()
