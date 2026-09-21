"""Modello proxy per la sezione admin "Vendors - Analysis and Classification".

Stesso pattern di vendor_management_system/services/models.py e
vendor_management_system/competences/models.py: nessuna tabella propria,
il modello reale resta in vendor_management_system.vendors.models. Serve
solo a far esistere la sezione admin (JAZZMIN_SETTINGS in config/
settings.py la usa per agganciarci il custom_link "Dashboard", che rimanda
a vendors/dashboard/, e nasconde questo modello dal menu tramite
"hide_models" - vedi AIDEV-46).
"""

from vendor_management_system.vendors.models import Vendor as _Vendor


class VendorAnalysisSection(_Vendor):
    class Meta:
        proxy = True
        app_label = "vendors_analysis"
        verbose_name = "Fornitore"
        verbose_name_plural = "Vendors - Analysis and Classification"
