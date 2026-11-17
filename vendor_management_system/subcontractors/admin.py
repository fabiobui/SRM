"""Admin di tecnici e mezzi dei subappaltatori.

Le sezioni sono inline sulla scheda del fornitore (visibili solo ai
Subappaltatori, vedi `VendorAdmin.get_inline_instances`). Ogni tecnico e ogni
mezzo ha anche una pagina propria con i documenti, raggiungibile dal link
"modifica" della riga inline: lì il back office valida o respinge i documenti.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    Equipment,
    EquipmentDocument,
    Technician,
    TechnicianDocument,
)


class TechnicianDocumentInline(admin.TabularInline):
    model = TechnicianDocument
    extra = 0
    fields = (
        "doc_type",
        "expiry_date",
        "file",
        "validation_status",
        "rejection_note",
    )
    readonly_fields = ()


class EquipmentDocumentInline(admin.TabularInline):
    model = EquipmentDocument
    extra = 0
    fields = (
        "doc_type",
        "expiry_date",
        "file",
        "validation_status",
        "rejection_note",
    )


class TechnicianInline(admin.TabularInline):
    model = Technician
    extra = 0
    show_change_link = True
    verbose_name = _("Tecnico")
    verbose_name_plural = _("Tecnici")
    fields = (
        "surname",
        "first_name",
        "role",
        "badge",
        "validation_status",
        "rejection_note",
    )


class EquipmentInline(admin.TabularInline):
    model = Equipment
    extra = 0
    show_change_link = True
    verbose_name = _("Mezzo/dotazione")
    verbose_name_plural = _("Mezzi/dotazioni")
    fields = (
        "equipment_type",
        "plate",
        "serial_code",
        "instrument",
        "validation_status",
        "rejection_note",
    )


@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ("surname", "first_name", "vendor", "validation_status")
    list_filter = ("validation_status",)
    search_fields = ("surname", "first_name", "vendor__name")
    inlines = [TechnicianDocumentInline]


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("equipment_type", "plate", "vendor", "validation_status")
    list_filter = ("validation_status",)
    search_fields = ("equipment_type", "plate", "vendor__name")
    inlines = [EquipmentDocumentInline]
