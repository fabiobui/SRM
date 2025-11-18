from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings

try:
    from vendor_management_system.vendors.models import Vendor
except Exception:  # pragma: no cover
    Vendor = None

VALID_ROLES = ["admin", "bo_user", "vendor"]

class Command(BaseCommand):
    help = "Sync or create LDAP users. Currently supports creating/updating a single LDAP user manually."

    def add_arguments(self, parser):
        parser.add_argument("--create-ldap-user", dest="email", help="Email of the LDAP user to create/update")
        parser.add_argument("--role", dest="role", choices=VALID_ROLES, default="bo_user", help="Role to assign")
        parser.add_argument("--name", dest="name", help="Display name for the user", default=None)
        parser.add_argument("--vendor-code", dest="vendor_code", help="Vendor code to link if role=vendor", default=None)
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen without persisting changes")

    def handle(self, *args, **options):
        email = options.get("email")
        role = options.get("role")
        name = options.get("name")
        vendor_code = options.get("vendor_code")
        dry_run = options.get("dry_run")

        if not email:
            raise CommandError("--create-ldap-user EMAIL è obbligatorio")

        if role == "vendor" and not vendor_code:
            raise CommandError("--vendor-code è obbligatorio quando il ruolo è 'vendor'")

        User = get_user_model()

        # Risolvi vendor se richiesto
        vendor = None
        if role == "vendor":
            if Vendor is None:
                raise CommandError("Modello Vendor non disponibile")
            try:
                vendor = Vendor.objects.get(vendor_code=vendor_code)
            except Vendor.DoesNotExist:
                raise CommandError(f"Vendor con codice '{vendor_code}' non trovato")

        # Transazione per consistenza
        with transaction.atomic():
            user, created = User.objects.get_or_create(email=email, defaults={
                "name": name or email.split("@")[0],
                "role": role,
                "is_ldap_user": True,
            })

            action = "creato" if created else "aggiornato"

            # Aggiornamento attributi se utente esistente
            user.is_ldap_user = True
            if name:
                user.name = name
            user.role = role
            if role == "vendor":
                user.vendor = vendor
            else:
                user.vendor = None

            # Non impostiamo password (LDAP) -> unusable
            if created:
                user.set_unusable_password()

            if dry_run:
                self.stdout.write(self.style.WARNING(f"[DRY-RUN] Utente sarebbe {action}: {email} (role={role})"))
                return

            user.save()

        self.stdout.write(self.style.SUCCESS(f"Utente LDAP {action}: {email} (role={role})"))
        if role == "vendor" and vendor:
            self.stdout.write(self.style.SUCCESS(f"Associato al vendor {vendor.vendor_code}"))
        self.stdout.write("Comando completato.")