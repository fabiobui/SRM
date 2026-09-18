from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CompetencesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vendor_management_system.competences"
    verbose_name = _("Vendor Professional Competences")
