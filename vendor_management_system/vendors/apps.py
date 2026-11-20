# Imports
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# App configuration
class VendorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vendor_management_system.vendors"
    verbose_name = _("Vendors")

    def ready(self):
        from django.db.models.signals import post_migrate

        from vendor_management_system.vendors.models import ensure_companies

        # Le società servono come default delle sezioni: devono esistere
        # anche nei DB creati senza migrazioni (test veloci su SQLite).
        post_migrate.connect(ensure_companies, sender=self)
