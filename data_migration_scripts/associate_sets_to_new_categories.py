#!/usr/bin/env python
"""
Associa i Set Documentali e i Set Abilitazioni e Requisiti FORMATORE,
CONSULENTE e LABORATORIO alle nuove Classificazioni omonime (AIDEV-118).
Da lanciare UNA VOLTA per ambiente, DOPO migrate_vendor_types_to_categories.py
(che crea le Classificazioni 106, 107 e 108).

Per ogni coppia (tipo di set, nome) il set viene collegato alla classificazione
solo se oggi non ne ha nessuna: una classificazione già impostata da admin non
viene mai sovrascritta. Se una classificazione non esiste lo script si ferma
senza modificare nulla.

È IDEMPOTENTE. Con --dry-run esegue tutto e annulla la transazione.

Uso (dalla root del repo, dentro la venv):
    python data_migration_scripts/associate_sets_to_new_categories.py \
        --dry-run
    python data_migration_scripts/associate_sets_to_new_categories.py
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from vendor_management_system.documents.models import DocumentSet  # noqa: E402
from vendor_management_system.vendors.models import (  # noqa: E402
    Category,
    CompetenceSet,
)

# nome del set (e della classificazione) -> codice Classificazione
CATEGORY_CODES = {
    "FORMATORE": "106",
    "CONSULENTE": "107",
    "LABORATORIO": "108",
}
SET_MODELS = (DocumentSet, CompetenceSet)


def log(msg):
    print(f"[sets-categories] {msg}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="esegue tutto e annulla la transazione",
    )
    args = parser.parse_args()

    modalita = "DRY-RUN (nessuna modifica)" if args.dry_run else "ESECUZIONE"
    log(f"Modalità: {modalita}")

    codes = list(CATEGORY_CODES.values())
    categories = {c.code: c for c in Category.objects.filter(code__in=codes)}
    missing = [code for code in codes if code not in categories]
    if missing:
        log(
            f"STOP: classificazioni non trovate: {', '.join(missing)}. "
            "Lancia prima migrate_vendor_types_to_categories.py."
        )
        return 2

    updated = 0
    with transaction.atomic():
        for model in SET_MODELS:
            label = model._meta.verbose_name
            for name, code in CATEGORY_CODES.items():
                category = categories[code]
                sets = model.objects.filter(name=name)
                if not sets:
                    log(f"{label} '{name}': non trovato, salto.")
                for obj in sets:
                    if obj.category_id is None:
                        obj.category = category
                        obj.save(update_fields=["category"])
                        updated += 1
                        log(f"{label} '{name}': associato a {code}.")
                    elif obj.category_id == category.pk:
                        log(f"{label} '{name}': già associato a {code}.")
                    else:
                        log(
                            f"{label} '{name}': ha già la classificazione "
                            f"'{obj.category}', non toccato."
                        )
        if args.dry_run:
            transaction.set_rollback(True)
            log("DRY-RUN: modifiche annullate.")

    log(f"Set associati: {updated}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
