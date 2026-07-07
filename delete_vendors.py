#!/usr/bin/env python
"""
Cancellazione di fornitori (Vendor) e di tutte le righe collegate.

Seleziona i fornitori per id singoli/multipli oppure per range, sul campo
indicato (default: old_code = Codice Embyon, l'unico numerato in modo ordinato;
vendor_code è invece un codice casuale, utile solo per valori esatti).

La cancellazione usa il .delete() dell'ORM di Django: le righe collegate con
on_delete=CASCADE (documenti, competenze, servizi, valutazioni, contratti, ...)
vengono eliminate automaticamente; quelle con on_delete=SET_NULL vengono
scollegate (il campo messo a NULL), non cancellate.

Di default è SICURO: mostra l'anteprima di cosa verrà eliminato e chiede
conferma. Usa --dry-run per non toccare nulla, --yes per saltare la conferma.

ESEMPI (sul server, dentro la venv):
    # singolo id (Codice Embyon)
    python delete_vendors.py --ids 1024
    # più id espliciti
    python delete_vendors.py --ids 1024,1030,1055
    # range inclusivo
    python delete_vendors.py --from 1000 --to 1050
    # per chiave primaria (vendor_code), valori esatti
    python delete_vendors.py --field vendor_code --ids A1B2C3D4E5
    # solo anteprima
    python delete_vendors.py --from 1000 --to 1050 --dry-run
"""
import argparse
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from django.db.models.deletion import Collector  # noqa: E402

from vendor_management_system.vendors.models import Vendor  # noqa: E402

ALLOWED_FIELDS = ("old_code", "vendor_code")


def parse_args():
    p = argparse.ArgumentParser(
        description="Cancella fornitori e righe collegate per id singolo o range."
    )
    p.add_argument(
        "--field", choices=ALLOWED_FIELDS, default="old_code",
        help="Campo su cui filtrare (default: old_code = Codice Embyon).",
    )
    p.add_argument(
        "--ids",
        help="Uno o più valori esatti separati da virgola (es. 1024,1030).",
    )
    p.add_argument("--from", dest="range_from",
                   help="Estremo iniziale del range (incluso).")
    p.add_argument("--to", dest="range_to",
                   help="Estremo finale del range (incluso).")
    p.add_argument("--dry-run", action="store_true",
                   help="Mostra solo l'anteprima, non cancella nulla.")
    p.add_argument("--yes", action="store_true",
                   help="Non chiede conferma (cancella subito dopo l'anteprima).")
    return p.parse_args()


def select_vendors(field, ids, range_from, range_to):
    """Restituisce il queryset dei vendor selezionati."""
    if ids:
        values = [v.strip() for v in ids.split(",") if v.strip()]
        if not values:
            raise SystemExit("ERRORE: --ids non contiene valori validi.")
        return Vendor.objects.filter(**{f"{field}__in": values})

    if range_from is None or range_to is None:
        raise SystemExit(
            "ERRORE: specifica --ids oppure entrambi --from e --to."
        )

    numeric = str(range_from).isdigit() and str(range_to).isdigit()
    if numeric:
        lo, hi = int(range_from), int(range_to)
        if lo > hi:
            lo, hi = hi, lo
        # I codici possono avere lunghezze/formati diversi: confronto numerico
        # in Python sui valori interpretabili come interi.
        pks = []
        qs = Vendor.objects.exclude(**{f"{field}__isnull": True})
        for pk, val in qs.values_list("pk", field):
            try:
                n = int(val)
            except (TypeError, ValueError):
                continue
            if lo <= n <= hi:
                pks.append(pk)
        return Vendor.objects.filter(pk__in=pks)

    # Range non numerico: confronto lessicografico lato DB.
    lo, hi = sorted([str(range_from), str(range_to)])
    return Vendor.objects.filter(**{f"{field}__gte": lo, f"{field}__lte": hi})


def build_preview(vendors):
    """Usa il Collector di Django per elencare cosa verrà eliminato/scollegato."""
    collector = Collector(using="default")
    collector.collect(list(vendors))

    to_delete = {}  # label -> conteggio

    def add_delete(label, n):
        to_delete[label] = to_delete.get(label, 0) + n

    # Oggetti raccolti "normalmente" (possono avere ulteriori cascate/segnali).
    for model, instances in collector.data.items():
        add_delete(model._meta.label, len(instances))

    # Oggetti eliminabili in blocco (nessuna ulteriore cascata): stanno qui,
    # NON in .data (es. competenze/servizi/valutazioni del fornitore).
    for qs in getattr(collector, "fast_deletes", []):
        add_delete(qs.model._meta.label, qs.count())

    # Campi messi a NULL (SET_NULL): scollegati, non cancellati.
    # In Django 5.x field_updates è un dict {(field, value): [queryset, ...]}.
    to_nullify = {}
    field_updates = getattr(collector, "field_updates", {}) or {}
    for key, querysets in field_updates.items():
        try:
            field, _value = key
        except (TypeError, ValueError):
            continue
        count = 0
        for qs in querysets:
            try:
                count += qs.count()
            except (AttributeError, TypeError):
                count += len(qs)
        if not count:
            continue
        model = getattr(field, "model", None)
        fname = getattr(field, "name", str(field))
        label = f"{model._meta.label}.{fname}" if model is not None else fname
        to_nullify[label] = to_nullify.get(label, 0) + count

    return to_delete, to_nullify


def main():
    args = parse_args()
    vendors = select_vendors(args.field, args.ids, args.range_from, args.range_to)

    count = vendors.count()
    if count == 0:
        print("Nessun fornitore corrisponde ai criteri indicati. Niente da fare.")
        return 0

    print(f"Fornitori selezionati ({count}) [campo: {args.field}]:")
    for pk, old_code, name in vendors.values_list("pk", "old_code", "name")[:200]:
        print(f"  - {pk}  (old_code={old_code})  {name}")
    if count > 200:
        print(f"  ... e altri {count - 200}")

    to_delete, to_nullify = build_preview(vendors)

    print("\nRighe che verranno ELIMINATE (CASCADE):")
    for label, n in sorted(to_delete.items(), key=lambda x: (-x[1], x[0])):
        if n:
            print(f"  {n:>6}  {label}")

    if to_nullify:
        print("\nRighe che verranno SCOLLEGATE (SET_NULL, non cancellate):")
        for label, n in sorted(to_nullify.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {n:>6}  {label}")

    if args.dry_run:
        print("\n--dry-run: nessuna modifica effettuata.")
        return 0

    if not args.yes:
        print(f"\nStai per ELIMINARE {count} fornitori e le righe collegate qui sopra.")
        resp = input("Digita 'CANCELLA' per confermare: ").strip()
        if resp != "CANCELLA":
            print("Annullato: nessuna modifica effettuata.")
            return 1

    with transaction.atomic():
        total, per_model = vendors.delete()
    print(f"\nEliminati {total} record totali.")
    for label, n in sorted(per_model.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {n:>6}  {label}")
    print("Fatto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
