from django.apps import AppConfig


class VendorsAnalysisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "vendor_management_system.vendors_analysis"
    # Nome della sezione admin tenuto in inglese (come "Back office portal",
    # vedi portal/apps.py), a prescindere dalla lingua attiva.
    verbose_name = "Vendors - Analysis and Classification"
