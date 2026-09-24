"""Modelli proxy per la sezione admin "Services".

I modelli reali (VendorService, ServiceType, ServiceSet) restano in
vendor_management_system.vendors.models: qui li esponiamo solo con un altro
nome/app_label per l'admin (nuove URL services/service/, services/
servicecatalog/, services/serviceset/), senza toccare tabelle, dati o codice
esistente. Vedi vendor_management_system/vendors/admin.py per i ModelAdmin
riusati e config/settings.py (JAZZMIN_SETTINGS) per l'ordinamento delle
sezioni e i modelli "vendors" nascosti dal menu.
"""

from vendor_management_system.vendors.models import ServiceSet as _ServiceSet
from vendor_management_system.vendors.models import ServiceType as _ServiceType
from vendor_management_system.vendors.models import (
    VendorService as _VendorService,
)


class Service(_VendorService):
    class Meta:
        proxy = True
        app_label = "services"
        verbose_name = "Servizio Erogato"
        verbose_name_plural = "Registro Servizi Erogati"


class ServiceCatalog(_ServiceType):
    class Meta:
        proxy = True
        app_label = "services"
        verbose_name = "Tipologia di Servizio Erogato"
        verbose_name_plural = "Catalogo Tipologie e Servizi Erogati"


class ServiceSet(_ServiceSet):
    class Meta:
        proxy = True
        app_label = "services"
        verbose_name = "Set Servizi Erogati"
        verbose_name_plural = "Set Servizi Erogati"
