"""Riallinea lo stato di qualifica dei fornitori "Approvati".

I fornitori approvati che hanno documenti o requisiti OBBLIGATORI non in
regola (non caricati, non verificati o scaduti) passano a "Da Revisionare".
Non riapprova mai nessuno. Da lanciare, per esempio, dopo il primo deploy
della regola di qualifica o dopo modifiche massive ai cataloghi.

Uso:
    python manage.py sync_qualification_status --dry-run
    python manage.py sync_qualification_status
"""

from django.core.management.base import BaseCommand

from vendor_management_system.vendors.models import Vendor


class Command(BaseCommand):
    help = (
        "Porta a 'Da Revisionare' i fornitori Approvati con documenti o "
        "requisiti obbligatori non in regola."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa cambierebbe senza modificare il database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        approved = list(Vendor.objects.filter(qualification_status="APPROVED"))
        changed = 0
        for vendor in approved:
            blockers = vendor.qualification_blockers
            if not blockers:
                continue
            changed += 1
            self.stdout.write(
                f"{vendor.vendor_code} {vendor.name}: {len(blockers)} "
                "elementi bloccanti"
            )
            if not dry_run:
                vendor.sync_qualification_status()
        verb = "da declassare" if dry_run else "declassati"
        self.stdout.write(
            self.style.SUCCESS(
                f"{changed} fornitori {verb} su {len(approved)} approvati."
            )
        )
