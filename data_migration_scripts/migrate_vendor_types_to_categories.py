#!/usr/bin/env python
"""
Sposta Formatore, Consulente e Laboratorio da Tipo Fornitore a Classificazione
(AIDEV-118). Da lanciare UNA VOLTA per ambiente.

Cosa fa, in un'unica transazione:
  1. crea le tre Classificazioni radice (senza padre) se non esistono già:
     106 FORMATORE, 107 CONSULENTE, 108 LABORATORIO;
  2. per ogni fornitore con il vecchio tipo corrispondente:
       - se non ha una classificazione principale, gli assegna la nuova;
       - se ne ha già una diversa, aggiunge la nuova alle aggiuntive;
       - svuota il Tipo Fornitore (da compilare a mano in seguito).

È IDEMPOTENTE: rilanciato non trova più fornitori da spostare. Con --dry-run
esegue tutto e annulla la transazione, stampando comunque il report.

Dopo questo script lancia associate_sets_to_new_categories.py.

Uso (dalla root del repo, dentro la venv):
    python data_migration_scripts/migrate_vendor_types_to_categories.py \
        --dry-run
    python data_migration_scripts/migrate_vendor_types_to_categories.py
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from vendor_management_system.vendors.models import (  # noqa: E402
    Category,
    Vendor,
)

# vecchio vendor_type -> (codice, nome, ordinamento) della Classificazione
# (letterale: i valori non sono più in VENDOR_TYPE_CHOICES)
MAPPING = {
    "Formatore": ("106", "FORMATORE", 400),
    "Consulente": ("107", "CONSULENTE", 410),
    "Laboratorio": ("108", "LABORATORIO", 420),
}


def log(msg):
    print(f"[vendor-types] {msg}")


def get_or_create_category(code, name, sort_order):
    category, created = Category.objects.get_or_create(
        code=code,
        defaults={
            "name": name,
            "parent": None,
            "is_active": True,
            "sort_order": sort_order,
        },
    )
    if created:
        log(f"Creata classificazione {code} - {name}.")
    else:
        log(f"Classificazione {code} già presente ('{category.name}').")
        if category.name != name or category.parent_id is not None:
            log(
                f"  ATTENZIONE: attesa radice '{name}', trovata "
                f"'{category.name}' (padre: {category.parent_id})."
            )
    return category


def migrate_vendors(vendor_type, category):
    moved = 0
    for vendor in Vendor.objects.filter(vendor_type=vendor_type):
        if vendor.category_id is None:
            vendor.category = category
            dove = "principale"
        elif vendor.category_id == category.pk:
            dove = "già principale"
        else:
            vendor.additional_categories.add(category)
            dove = "aggiuntiva"
        # update() evita effetti collaterali di save() (segnali, stati)
        Vendor.objects.filter(pk=vendor.pk).update(
            category=vendor.category, vendor_type=None
        )
        log(f"  {vendor.vendor_code} - {vendor.name}: {dove}.")
        moved += 1
    return moved


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="esegue tutto e annulla la transazione",
    )
    args = parser.parse_args()

    log(
        "Modalità: "
        + ("DRY-RUN (nessuna modifica)" if args.dry_run else "ESECUZIONE")
    )

    totale = 0
    with transaction.atomic():
        for vendor_type, (code, name, order) in MAPPING.items():
            category = get_or_create_category(code, name, order)
            count = Vendor.objects.filter(vendor_type=vendor_type).count()
            log(f"Fornitori con tipo '{vendor_type}': {count}")
            totale += migrate_vendors(vendor_type, category)
        if args.dry_run:
            transaction.set_rollback(True)
            log("DRY-RUN: modifiche annullate.")

    log(f"Fornitori spostati: {totale}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
