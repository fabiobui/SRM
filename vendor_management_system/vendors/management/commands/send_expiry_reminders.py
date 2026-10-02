"""Invia i promemoria di scadenza di documenti e abilitazioni ai fornitori.

Stessa logica del job Celery giornaliero (``send_expiry_reminders_task``):
utile per una verifica manuale o come fallback dove beat non gira.

Uso:
    python manage.py send_expiry_reminders --dry-run
    python manage.py send_expiry_reminders --date 2026-10-31
    python manage.py send_expiry_reminders
"""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from vendor_management_system.vendors.expiry_reminders import (
    send_expiry_reminders,
)


class Command(BaseCommand):
    help = "Invia ai fornitori i promemoria di scadenza del giorno."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe inviato senza inviare né registrare.",
        )
        parser.add_argument(
            "--date",
            help="Simula l'esecuzione in un altro giorno (YYYY-MM-DD).",
        )

    def handle(self, *args, **options):
        today = None
        if options["date"]:
            try:
                today = date.fromisoformat(options["date"])
            except ValueError as exc:
                raise CommandError("Data non valida: usa YYYY-MM-DD.") from exc
        dry_run = options["dry_run"]
        summary = send_expiry_reminders(today=today, dry_run=dry_run)

        for vendor, items in summary["sent"]:
            self.stdout.write(
                f"{vendor.vendor_code} {vendor.name} <{vendor.email}>"
            )
            for item in items:
                self.stdout.write(
                    f"  - {item.kind_label}: {item.label}, scade il "
                    f"{item.expiry_date:%d/%m/%Y} ({item.days_left} gg, "
                    f"{item.stage})"
                )
        for vendor, _items in summary["failed"]:
            self.stderr.write(
                f"Invio non riuscito: {vendor.vendor_code} {vendor.name}"
            )

        verb = "da notificare" if dry_run else "notificati"
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(summary['sent'])} fornitori {verb} "
                f"({summary['items']} elementi), "
                f"{len(summary['failed'])} invii non riusciti."
            )
        )
