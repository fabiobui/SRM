from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vendor_management_system.portal"
    # Nome della sezione admin tenuto in inglese (come "Authentication and
    # Authorization", vedi core/apps.py), a prescindere dalla lingua attiva.
    verbose_name = "Back office portal"
