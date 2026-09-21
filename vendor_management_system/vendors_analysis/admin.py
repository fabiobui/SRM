from django.contrib import admin

from .models import VendorAnalysisSection

# Registrato ma nascosto dal menu (JAZZMIN_SETTINGS["hide_models"] in
# config/settings.py): senza almeno un modello registrato, Django non
# costruisce affatto la sezione app "vendors_analysis" in /admin, quindi il
# custom_link "Dashboard" (verso vendors/dashboard/) non avrebbe nessuna
# sezione a cui aggrapparsi. Stesso pattern già usato per "portal"
# (vedi vendor_management_system/portal/admin.py).
#
# has_module_permission sempre True: la sezione deve comparire per
# qualunque utente di staff, non solo per chi ha permessi specifici su
# questo modello "finto". Le altre permission restano bloccate (tranne la
# view, necessaria perché il modulo compaia nel menu) per evitare di
# esporre una seconda interfaccia di modifica sui fornitori, ridondante
# con /admin/vendors/vendor/.


@admin.register(VendorAnalysisSection)
class VendorAnalysisSectionAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
