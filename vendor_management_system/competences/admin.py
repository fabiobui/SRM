from django.contrib import admin

from vendor_management_system.vendors.admin import (
    CompetenceAdmin as _CompetenceAdmin,
)
from vendor_management_system.vendors.admin import (
    CompetenceSetAdmin as _CompetenceSetAdmin,
)
from vendor_management_system.vendors.admin import (
    VendorCompetenceAdmin as _VendorCompetenceAdmin,
)

from .models import Competence, CompetenceCatalog, CompetenceSet

admin.site.register(Competence, _VendorCompetenceAdmin)
admin.site.register(CompetenceCatalog, _CompetenceAdmin)
admin.site.register(CompetenceSet, _CompetenceSetAdmin)
