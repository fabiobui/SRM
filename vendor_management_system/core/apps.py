# Imports
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


# App configuration
class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vendor_management_system.core"
    verbose_name = _("Core")

    def ready(self):
        # L'app auth di Django traduce il proprio verbose_name in base alla
        # lingua attiva (in italiano "Autenticazione e Autorizzazione").
        # In admin vogliamo tenerla sempre in inglese: assegnando qui una
        # stringa già risolta (non lazy) evitiamo che venga ritradotta.
        from django.apps import apps

        apps.get_app_config(
            "auth"
        ).verbose_name = "Authentication and Authorization"
