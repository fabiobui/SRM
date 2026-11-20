"""Allinea i fornitori censiti alle viste FABRIC_HUB dei fornitori condivisi.

Assegna il codice SAGE, aggiorna i conti Embyon delle sezioni società e il
loro stato attivo. Non crea fornitori né sezioni nuove. Stessa logica del
job Celery giornaliero (``sync_fabric_suppliers_task``).

Uso:
    python manage.py sync_fabric_suppliers --dry-run
    python manage.py sync_fabric_suppliers
"""

from django.core.management.base import BaseCommand

from vendor_management_system.vendors.supplier_sync import sync_suppliers


class Command(BaseCommand):
    help = (
        "Allinea codice SAGE e conti Embyon dei fornitori censiti alle viste "
        "FABRIC_HUB (senza creare fornitori o sezioni)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa cambierebbe senza modificare il database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        summary = sync_suppliers(dry_run=dry_run)
        for vendor, sage, owner in summary["merge_candidates"]:
            self.stdout.write(
                f"Da accorpare: {vendor.pk} {vendor.name} -> SAGE {sage} "
                f"(già su {owner})"
            )
        for vendor, codes in summary["ambiguous"]:
            self.stdout.write(
                f"Più codici SAGE per {vendor.pk} {vendor.name}: "
                f"{', '.join(codes)}"
            )
        verb = "da assegnare" if dry_run else "assegnati"
        self.stdout.write(
            self.style.SUCCESS(
                f"Codici SAGE {verb}: {len(summary['sage_assigned'])}; conti "
                f"aggiornati: {summary['accounts_updated']}, aggiunti: "
                f"{summary['accounts_added']}, non più nelle viste: "
                f"{len(summary['accounts_missing'])}; candidati "
                f"all'accorpamento: {len(summary['merge_candidates'])}."
            )
        )
