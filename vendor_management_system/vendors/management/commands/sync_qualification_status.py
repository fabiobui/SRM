"""Riallinea lo stato di qualifica dei fornitori "Approvati" e il bollino.

I fornitori approvati che hanno documenti o requisiti OBBLIGATORI non in
regola (non caricati, non verificati o scaduti) passano a "Da Revisionare".
Non riapprova mai nessuno. Poi riallinea la Valutazione Finale di tutti i
fornitori. Stessa logica del job Celery giornaliero
(``sync_qualification_status_task``): utile dopo un deploy, dopo modifiche
massive ai cataloghi o dove beat non gira.

Uso:
    python manage.py sync_qualification_status --dry-run
    python manage.py sync_qualification_status
"""

from django.core.management.base import BaseCommand

from vendor_management_system.vendors.qualification_sync import sync_all


class Command(BaseCommand):
    help = (
        "Porta a 'Da Revisionare' i fornitori Approvati con documenti o "
        "requisiti obbligatori non in regola e riallinea la Valutazione "
        "Finale."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa cambierebbe senza modificare il database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        summary = sync_all(dry_run=dry_run)
        for vendor, blockers in summary["downgraded"]:
            self.stdout.write(
                f"{vendor.vendor_code} {vendor.name}: {len(blockers)} "
                "elementi bloccanti"
            )
        verb = "da declassare" if dry_run else "declassati"
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(summary['downgraded'])} fornitori {verb} su "
                f"{summary['approved']} approvati."
            )
        )
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{summary['realigned']} valutazioni finali riallineate."
                )
            )
