"""Semina il catalogo geografico: Nazioni, Regioni e Province.

Sostituisce lo script manuale ``vendor_management_system/
import_geography.py``, che andava lanciato a mano con ``manage.py shell <``.

Il catalogo è il prerequisito delle zone di competenza dei fornitori:
senza queste righe il selettore territoriale nell'admin e nel portale
fornitori è vuoto. Per questo la geografia viene seminata anche da
una data migration dedicata — ``compose/django/start`` esegue ``migrate``
prima dei comandi di seed, e la migrazione che travasa le vecchie zone di
competenza ha bisogno che le province esistano già.

Il comando resta utile per i re-seed manuali e per gli ambienti già
migrati. È idempotente: riconosce le righe esistenti dal ``code``.

Uso: python manage.py seed_geography [--create-only]
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from vendor_management_system.vendors.geography_seed import seed_geography
from vendor_management_system.vendors.models import Country, Province, Region


class Command(BaseCommand):
    help = (
        "Popola il catalogo geografico (Nazioni, Regioni, Province) usato "
        "dalle zone di competenza dei fornitori"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--create-only",
            action="store_true",
            help=(
                "Crea solo le righe mancanti, senza riallineare il nome di "
                "quelle già presenti. `is_active` e `sort_order` non "
                "vengono comunque mai toccati, in nessuna modalità: "
                "possono essere stati personalizzati da admin. Pensato per "
                "l'esecuzione automatica ad ogni deploy."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Inizio popolamento catalogo geografico...")
        )

        conteggi = seed_geography(
            Country,
            Region,
            Province,
            create_only=options["create_only"],
        )

        for livello, dati in conteggi.items():
            self.stdout.write(
                f"  {livello}: {dati['creati']} create, "
                f"{dati['esistenti']} già presenti, "
                f"{dati['aggiornati']} riallineate al catalogo"
            )

        totale = sum(d["creati"] for d in conteggi.values())
        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogo geografico aggiornato ({totale} righe create)."
            )
        )
