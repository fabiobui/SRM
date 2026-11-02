# Imports
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


def _allinea_gruppi_ruoli(**kwargs):
    from vendor_management_system.users.roles import ensure_role_groups

    ensure_role_groups()


# App configuration
class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vendor_management_system.users"
    verbose_name = _("Users")

    def ready(self):
        # Ogni migrate riallinea i permessi dei gruppi di ruolo, così un
        # deploy non lascia i gruppi in uno stato diverso dal codice.
        post_migrate.connect(
            _allinea_gruppi_ruoli,
            sender=self,
            dispatch_uid="users_allinea_gruppi_ruoli",
        )
