from django.contrib import admin

from vendor_management_system.vendors.admin import (
    ServiceSetAdmin as _ServiceSetAdmin,
)
from vendor_management_system.vendors.admin import (
    ServiceTypeAdmin as _ServiceTypeAdmin,
)
from vendor_management_system.vendors.admin import (
    VendorServiceAdmin as _VendorServiceAdmin,
)

from .models import Service, ServiceCatalog, ServiceSet

admin.site.register(Service, _VendorServiceAdmin)
admin.site.register(ServiceCatalog, _ServiceTypeAdmin)
admin.site.register(ServiceSet, _ServiceSetAdmin)
