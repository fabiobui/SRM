"""Modelli proxy per la sezione admin "Vendor Professional Competences".

I modelli reali (VendorCompetence, Competence, CompetenceSet) restano in
vendor_management_system.vendors.models: qui li esponiamo solo con un altro
nome/app_label per l'admin (nuove URL competences/competence/, competences/
competencecatalog/, competences/competenceset/), senza toccare tabelle, dati
o codice esistente. Vedi vendor_management_system/vendors/admin.py per i
ModelAdmin riusati e config/settings.py (JAZZMIN_SETTINGS) per l'ordinamento
delle sezioni e i modelli "vendors" nascosti dal menu.
"""

from vendor_management_system.vendors.models import Competence as _Competence
from vendor_management_system.vendors.models import (
    CompetenceSet as _CompetenceSet,
)
from vendor_management_system.vendors.models import (
    VendorCompetence as _VendorCompetence,
)


class Competence(_VendorCompetence):
    class Meta:
        proxy = True
        app_label = "competences"
        verbose_name = "Abilitazione/Requisito professionale assegnato"
        verbose_name_plural = "Registro Abilitazioni e Requisiti Professionali"


class CompetenceCatalog(_Competence):
    class Meta:
        proxy = True
        app_label = "competences"
        verbose_name = "Abilitazione/Requisito professionale"
        verbose_name_plural = "Catalogo Abilitazioni e Requisiti Professionali"


class CompetenceSet(_CompetenceSet):
    class Meta:
        proxy = True
        app_label = "competences"
        verbose_name = "Set Abilitazioni e Requisiti Professionali"
        verbose_name_plural = "Set Abilitazioni e Requisiti Professionali"
