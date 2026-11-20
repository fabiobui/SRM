# Aggiornamenti per vendor_management_system/vendors/admin.py

# Imports (aggiorna le imports esistenti)
import io
import json
import os
import re
import zipfile

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db.models import Q, TextField
from django.forms import modelform_factory
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# Import Document and DocumentCatalog from documents app
from vendor_management_system.documents.date_extraction import suggested_dates
from vendor_management_system.documents.models import (
    VALIDITY_STATUS_META,
    Document,
    DocumentCatalog,
    DocumentSet,
)
from vendor_management_system.subcontractors.admin import (
    EquipmentInline,
    TechnicianInline,
)
from vendor_management_system.users.portal_access import (
    PortalAccessError,
    create_portal_user,
    invite_and_notify,
    pending_invite,
    portal_users,
    reset_portal_credentials,
)

from . import fabric_hub
from .admin_filters import (
    CompetenceCountryFilter,
    CompetenceProvinceFilter,
    CompetenceRegionFilter,
)
from .admin_sections import (
    FINAL_EVALUATION_COLORS,
    STATUS_COLORS,
    SectionChangeList,
    SectionEditableMixin,
    SectionInlineMixin,
    VendorCompanyInline,
    current_section,
    section_badges,
    section_editable,
    section_url,
    sections_url,
    user_can_add_section,
)
from .competence import (
    current_selection,
    set_vendor_competence,
)
from .models import (
    COMMON_SECTION,
    Address,
    Category,
    Company,
    Competence,
    CompetenceSet,
    Contract,
    Country,
    EvaluationCriterion,
    EvaluationFrequency,
    Evaluator,
    ExpiryReminderLog,
    Province,
    QualificationType,
    Region,
    ServiceSet,
    ServiceType,
    Vendor,
    VendorCompetence,
    VendorEvaluation,
    VendorOperationalAttributes,
    VendorService,
    oggi_locale,
    vendor_category_scope_ids,
)
from .sections import (
    SECTION_PARAM,
    can_edit_section,
    create_section_with_accounts,
    duplicates_in_other_sections,
    find_registered_vendor,
    resolve_section,
    subcontractor_section,
    vendor_sections,
)
from .widgets import CompetenceAreaField

# ============================================================================
# Admin Geografici (Nazione, Regione, Provincia)
# ============================================================================


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "sort_order", "region_count"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]
    ordering = ["sort_order", "name"]
    list_editable = ["is_active", "sort_order"]

    def region_count(self, obj):
        return obj.regions.count()

    region_count.short_description = _("N. Regioni")


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "country",
        "is_active",
        "sort_order",
        "province_count",
    ]
    list_filter = ["is_active", "country"]
    search_fields = ["code", "name"]
    ordering = ["country__name", "sort_order", "name"]
    list_editable = ["is_active", "sort_order"]
    autocomplete_fields = ["country"]

    def province_count(self, obj):
        return obj.provinces.count()

    province_count.short_description = _("N. Province")


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "region",
        "region_country",
        "is_active",
        "sort_order",
    ]
    list_filter = ["is_active", "region__country", "region"]
    search_fields = ["code", "name"]
    ordering = ["region__country__name", "region__name", "sort_order", "name"]
    list_editable = ["is_active", "sort_order"]
    autocomplete_fields = ["region"]

    def region_country(self, obj):
        return obj.region.country.name

    region_country.short_description = _("Nazione")


# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "parent",
        "is_active",
        "sort_order",
        "vendor_count",
        "color_badge",
    ]
    list_filter = [
        "is_active",
        "requires_certification",
        "default_risk_level",
        "parent",
    ]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order", "name"]
    list_editable = ["is_active", "sort_order"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "full_name",
        "level",
        "vendor_count",
        "total_vendor_count",
    ]

    fieldsets = (
        (
            _("Informazioni Base"),
            {"fields": ("code", "name", "description", "parent")},
        ),
        (
            _("Classificazione"),
            {"fields": ("is_active", "sort_order", "color_code")},
        ),
        (
            _("Regole di Business"),
            {"fields": ("requires_certification", "default_risk_level")},
        ),
        (
            _("Statistiche"),
            {
                "fields": (
                    "full_name",
                    "level",
                    "vendor_count",
                    "total_vendor_count",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def color_badge(self, obj):
        if obj.color_code:
            return format_html(
                '<span style="background-color: {}; padding: 5px 10px; '
                'border-radius: 3px; color: white;">{}</span>',
                obj.color_code,
                obj.color_code,
            )
        return "-"

    color_badge.short_description = _("Colore")


# Competence Resource for import/export
class CompetenceResource(resources.ModelResource):
    class Meta:
        model = Competence
        fields = (
            "id",
            "code",
            "name",
            "description",
            "competence_category",
            "requires_certification",
            "requires_renewal",
            "validity_period_days",
            "reminder_days_before",
            "is_mandatory",
            "is_active",
            "sort_order",
        )
        export_order = fields
        import_id_fields = ["code"]


# Competence Admin
@admin.register(Competence)
class CompetenceAdmin(ImportExportModelAdmin):
    resource_class = CompetenceResource
    list_display = [
        "code",
        "name",
        "competence_category",
        "is_mandatory",
        "requires_certification",
        "requires_renewal",
        "is_active",
    ]
    list_filter = [
        "competence_category",
        "is_mandatory",
        "requires_certification",
        "requires_renewal",
        "is_active",
    ]
    search_fields = ["code", "name", "description"]
    ordering = ["competence_category", "sort_order", "name"]
    list_editable = ["is_active", "is_mandatory"]
    filter_horizontal = ["applicable_categories"]
    readonly_fields = ["created_at", "updated_at"]

    class Media:
        js = ("admin/js/renewal_fields_toggle.js",)

    fieldsets = (
        (
            _("Informazioni Base"),
            {"fields": ("code", "name", "description", "competence_category")},
        ),
        (
            _("Requisiti"),
            {
                "fields": (
                    "requires_certification",
                    "requires_renewal",
                    "validity_period_days",
                    "reminder_days_before",
                )
            },
        ),
        (
            _("Configurazione"),
            {"fields": ("is_mandatory", "is_active", "sort_order")},
        ),
        (_("Categorie Applicabili"), {"fields": ("applicable_categories",)}),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# VendorCompetence Inline
class VendorCompetenceInline(SectionInlineMixin, admin.TabularInline):
    model = VendorCompetence
    extra = 1
    template = "admin/vendors/inline/abilitazioni.html"
    verbose_name_plural = _("Abilitazioni e Requisiti Professionali")
    fields = [
        "competence",
        "is_competenza",
        "is_qualifica",
        "is_iscrizione_albo",
        "has_certification",
        "certification_number",
        "issue_date",
        "expiry_date",
        "expiry_status_display",
        "document_file",
        "document_link",
    ]
    # "Verificata" resta a DB ma non compare in admin.
    readonly_fields = [
        "expiry_status_display",
        "document_link",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["competence"]

    def document_link(self, obj):
        """Link per visualizzare/scaricare il file caricato dal fornitore."""
        if obj and obj.pk and obj.document_file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">{}</a>',
                obj.document_file.url,
                _("Visualizza"),
            )
        return _("Nessun file")

    document_link.short_description = _("File Caricato")

    def expiry_status_display(self, obj):
        if obj._state.adding:
            return "-"
        label, color = VALIDITY_STATUS_META.get(
            obj.validity_status, (obj.validity_status, "gray")
        )
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label,
        )

    expiry_status_display.short_description = _("Stato validità")


# VendorService Inline
class VendorServiceInline(SectionInlineMixin, admin.TabularInline):
    model = VendorService
    extra = 1
    fields = [
        "service_type",
        "is_primary",
        "hourly_rate",
        "start_date",
        "end_date",
        "contract",
        "notes",
    ]
    readonly_fields = ["created_at", "updated_at"]
    formfield_overrides = {
        TextField: {"widget": forms.Textarea(attrs={"rows": 1, "cols": 30})},
    }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "service_type":
            # Mostra solo i servizi specifici (con parent), non le
            # categorie principali
            # select_related: ServiceType.__str__ legge il parent, senza
            # sarebbe una query per opzione (per ogni riga dell'inline).
            kwargs["queryset"] = (
                ServiceType.objects.filter(
                    is_active=True, parent__isnull=False
                )
                .select_related("parent")
                .order_by("parent__name", "name")
            )
        if db_field.name == "contract":
            # Mostra solo i contratti del vendor corrente
            vendor_id = None
            if hasattr(request, "_obj_") and request._obj_:
                vendor_id = request._obj_.vendor_code
            if vendor_id:
                contracts = Contract.objects.filter(
                    vendor__vendor_code=vendor_id
                )
                # Contratti della sezione aperta o della Comune.
                section = current_section(request)
                if section is not None:
                    contracts = contracts.filter(
                        company_id__in=[COMMON_SECTION, section.code]
                    )
                kwargs["queryset"] = contracts
            else:
                kwargs["queryset"] = Contract.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# VendorService Admin
@admin.register(VendorService)
class VendorServiceAdmin(admin.ModelAdmin):
    list_display = [
        "vendor",
        "service_type",
        "is_primary",
        "hourly_rate",
        "start_date",
        "end_date",
        "is_active_display",
    ]
    list_filter = [
        "is_primary",
        "service_type__parent",
        "start_date",
        "end_date",
    ]
    search_fields = ["vendor__name", "service_type__name"]
    date_hierarchy = "start_date"
    readonly_fields = ["created_at", "updated_at", "is_active"]
    autocomplete_fields = ["vendor", "service_type"]

    fieldsets = (
        (_("Relazione"), {"fields": ("vendor", "service_type", "is_primary")}),
        (_("Tariffa"), {"fields": ("hourly_rate",)}),
        (
            _("Periodo Erogazione"),
            {"fields": ("start_date", "end_date", "is_active")},
        ),
        (_("Note"), {"fields": ("notes",)}),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def is_active_display(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">'
                "✓ Attivo</span>"
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Terminato</span>'
        )

    is_active_display.short_description = _("Stato")


# VendorCompetence Admin
@admin.register(VendorCompetence)
class VendorCompetenceAdmin(admin.ModelAdmin):
    list_display = [
        "vendor",
        "competence",
        "has_competence",
        "is_competenza",
        "is_qualifica",
        "is_iscrizione_albo",
        "has_certification",
        "issue_date",
        "expiry_date",
        "expiry_status_badge",
    ]
    list_filter = [
        "has_competence",
        "is_competenza",
        "is_qualifica",
        "is_iscrizione_albo",
        "has_certification",
        "competence__competence_category",
        "expiry_date",
    ]
    search_fields = [
        "vendor__name",
        "competence__name",
        "certification_number",
    ]
    date_hierarchy = "expiry_date"
    readonly_fields = [
        "created_at",
        "updated_at",
        "is_expired",
        "days_to_expiry",
        "validity_status",
        "verified_by",
        "verified_date",
    ]
    autocomplete_fields = ["vendor", "competence"]

    fieldsets = (
        (
            _("Relazione"),
            {"fields": ("vendor", "competence", "has_competence")},
        ),
        (
            _("Tipo Requisito"),
            {
                "fields": (
                    "is_competenza",
                    "is_qualifica",
                    "is_iscrizione_albo",
                    "has_certification",
                )
            },
        ),
        (
            _("Dettagli Certificazione"),
            {
                "fields": (
                    "certification_number",
                    "certification_body",
                    "issue_date",
                    "expiry_date",
                )
            },
        ),
        (
            _("Verifica"),
            {"fields": ("verified_by", "verified_date")},
        ),
        (_("Documentazione"), {"fields": ("document_file", "notes")}),
        (
            _("Stato validità"),
            {
                "fields": ("is_expired", "days_to_expiry", "validity_status"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def expiry_status_badge(self, obj):
        label, color = VALIDITY_STATUS_META.get(
            obj.validity_status, (obj.validity_status, "gray")
        )
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; '
            'border-radius: 3px; color: white;">{}</span>',
            color,
            label,
        )

    expiry_status_badge.short_description = _("Stato validità")


# Document Inline
class DocumentInline(SectionInlineMixin, admin.TabularInline):
    model = Document
    extra = 1
    template = "admin/vendors/inline/documenti.html"
    verbose_name_plural = _("Documenti Contrattuali")
    fields = [
        "document_type",
        "issue_date",
        "expiry_date",
        "expiry_status_display",
        "file",
        "file_link",
    ]
    readonly_fields = ["expiry_status_display", "file_link", "uploaded_at"]
    autocomplete_fields = ["document_type"]

    def file_link(self, obj):
        """Link per visualizzare/scaricare il file caricato dal fornitore."""
        if obj and obj.pk and obj.file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener">{}</a>',
                obj.file.url,
                _("Visualizza"),
            )
        return _("Nessun file")

    file_link.short_description = _("File Caricato")

    def expiry_status_display(self, obj):
        if not obj or not obj.pk:
            return "-"
        # Fonte unica: Document.validity_status.
        label, color = VALIDITY_STATUS_META.get(
            obj.validity_status, (obj.validity_status, "gray")
        )
        return format_html(
            '<span class="doc-validity-status" style="color: {}; '
            'font-weight: bold;">{}</span>',
            color,
            label,
        )

    expiry_status_display.short_description = _("Stato validità")


# Address Admin
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        "short_address",
        "city",
        "postal_code",
        "country",
        "address_type",
        "is_active",
    ]
    list_filter = ["address_type", "is_active", "country", "city"]
    search_fields = ["street_address", "city", "postal_code", "country"]
    readonly_fields = ["created_at", "updated_at", "full_address"]

    fieldsets = (
        (
            _("Indirizzo"),
            {
                "fields": (
                    "street_address",
                    "street_address_2",
                    "city",
                    "state_province",
                    "region",
                    "postal_code",
                    "country",
                )
            },
        ),
        (
            _("Coordinate Geografiche"),
            {"fields": ("latitude", "longitude"), "classes": ("collapse",)},
        ),
        (
            _("Informazioni Aggiuntive"),
            {"fields": ("address_type", "is_active", "full_address")},
        ),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# QualificationType Admin
@admin.register(QualificationType)
class QualificationTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "level", "is_active", "sort_order"]
    list_filter = ["is_active", "level"]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order", "name"]
    list_editable = ["is_active", "sort_order"]


# ServiceType Admin
@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "parent",
        "is_active",
        "sort_order",
        "is_category",
    ]
    list_filter = ["is_active", "parent"]
    search_fields = ["code", "name", "description"]
    ordering = ["sort_order", "name"]
    list_editable = ["is_active", "sort_order"]

    def is_category(self, obj):
        return obj.is_category

    is_category.boolean = True
    is_category.short_description = _("È Categoria")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Personalizza il campo parent per mostrare solo le categorie"""
        if db_field.name == "parent":
            # Mostra solo i ServiceType che sono categorie (parent=None)
            kwargs["queryset"] = ServiceType.objects.filter(
                parent__isnull=True
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# EvaluationCriterion Admin
@admin.register(EvaluationCriterion)
class EvaluationCriterionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["code", "name", "description"]
    ordering = ["category", "code"]
    list_editable = ["is_active"]


# EvaluationFrequency Admin
@admin.register(EvaluationFrequency)
class EvaluationFrequencyAdmin(admin.ModelAdmin):
    list_display = ["name", "months", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["months"]


# Evaluator Admin
@admin.register(Evaluator)
class EvaluatorAdmin(admin.ModelAdmin):
    list_display = [
        "last_name",
        "first_name",
        "email",
        "role",
        "department",
        "is_active",
    ]
    list_filter = ["is_active", "department"]
    search_fields = ["first_name", "last_name", "email", "role", "department"]
    ordering = ["last_name", "first_name"]


@admin.register(ExpiryReminderLog)
class ExpiryReminderLogAdmin(admin.ModelAdmin):
    """Storico in sola lettura dei promemoria scadenza inviati: le righe le
    scrive solo il job giornaliero."""

    list_display = [
        "sent_at",
        "vendor",
        "item_kind",
        "item_label",
        "expiry_date",
        "stage",
        "recipients",
    ]
    list_filter = ["item_kind", "stage", "sent_at"]
    search_fields = ["vendor__name", "vendor__vendor_code", "item_label"]
    list_select_related = ["vendor"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# VendorEvaluation Inline
class VendorEvaluationInline(SectionInlineMixin, admin.TabularInline):
    model = VendorEvaluation
    extra = 1
    fields = [
        "criterion",
        "score",
        "evaluator",
        "evaluation_frequency",
        "notes",
        "evaluated_at",
    ]
    readonly_fields = ["evaluated_at"]
    autocomplete_fields = ["criterion", "evaluator", "evaluation_frequency"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "notes":
            kwargs["widget"] = admin.widgets.AdminTextareaWidget(
                attrs={"rows": 2, "cols": 40, "style": "width: 300px;"}
            )
        if db_field.name == "evaluation_frequency":
            try:
                kwargs["initial"] = EvaluationFrequency.objects.get(
                    months=12
                ).pk
            except EvaluationFrequency.DoesNotExist:
                pass
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def expiry_status_display(self, obj):
        if obj._state.adding:
            return "-"
        label, color = VALIDITY_STATUS_META.get(
            obj.validity_status, (obj.validity_status, "gray")
        )
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            label,
        )

    expiry_status_display.short_description = _("Stato validità")


# VendorEvaluation Admin
@admin.register(VendorEvaluation)
class VendorEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "vendor",
        "criterion",
        "score",
        "score_display",
        "evaluator",
        "evaluated_at",
    ]
    list_filter = ["score", "criterion__category", "evaluator", "evaluated_at"]
    search_fields = [
        "vendor__name",
        "criterion__name",
        "notes",
        "evaluator__last_name",
        "evaluator__first_name",
    ]
    date_hierarchy = "evaluated_at"
    autocomplete_fields = ["vendor", "criterion", "evaluator"]

    def score_display(self, obj):
        return obj.get_score_display()

    score_display.short_description = _("Valutazione")


# Contract Inline
class ContractInline(SectionInlineMixin, admin.StackedInline):
    model = Contract
    extra = 0
    fields = [
        "contract_number",
        "title",
        "contract_type",
        "reference_person",
        "status",
        "start_date",
        "end_date",
        "amount",
        "notes",
    ]


# Contract Admin (standalone)
@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        "contract_number",
        "title",
        "vendor",
        "contract_type",
        "status",
        "start_date",
        "end_date",
        "amount",
    ]
    list_filter = ["status", "contract_type", "start_date"]
    search_fields = [
        "contract_number",
        "title",
        "vendor__name",
        "vendor__vendor_code",
        "reference_person",
    ]
    autocomplete_fields = ["vendor"]
    date_hierarchy = "start_date"
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "contract_number",
                    "title",
                    "vendor",
                    "contract_type",
                    "reference_person",
                    "status",
                )
            },
        ),
        (
            _("Date e Importo"),
            {"fields": ("start_date", "end_date", "amount")},
        ),
        (
            _("Note e Metadati"),
            {
                "fields": ("notes", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


# ============================================================================
# Set predefiniti (Requisiti Professionali / Servizi)
# ============================================================================


@admin.register(CompetenceSet)
class CompetenceSetAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "competences_count",
        "is_active",
        "sort_order",
    ]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "description"]
    list_editable = ["is_active", "sort_order"]
    filter_horizontal = ["competences"]
    ordering = ["sort_order", "name"]

    fieldsets = (
        (
            _("Informazioni Base"),
            {"fields": ("name", "description", "category")},
        ),
        (_("Requisiti del set"), {"fields": ("competences",)}),
        (_("Configurazione"), {"fields": ("is_active", "sort_order")}),
    )

    def competences_count(self, obj):
        return obj.competences.count()

    competences_count.short_description = _("N. Requisiti")


@admin.register(ServiceSet)
class ServiceSetAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "service_types_count",
        "is_active",
        "sort_order",
    ]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "description"]
    list_editable = ["is_active", "sort_order"]
    filter_horizontal = ["service_types"]
    ordering = ["sort_order", "name"]

    fieldsets = (
        (
            _("Informazioni Base"),
            {"fields": ("name", "description", "category")},
        ),
        (_("Servizi del set"), {"fields": ("service_types",)}),
        (_("Configurazione"), {"fields": ("is_active", "sort_order")}),
    )

    def service_types_count(self, obj):
        return obj.service_types.count()

    service_types_count.short_description = _("N. Servizi")


class VendorOperationalAttributesInlineForm(forms.ModelForm):
    """Form dell'inline Attributi Operativi: textarea più basse per le
    note libere."""

    class Meta:
        model = VendorOperationalAttributes
        fields = "__all__"
        widgets = {
            "aerial_platforms_notes": forms.Textarea(attrs={"rows": 2}),
            "mobile_scaffolding_notes": forms.Textarea(attrs={"rows": 2}),
            "lifting_equipment_notes": forms.Textarea(attrs={"rows": 2}),
        }


class VendorOperationalAttributesInline(
    SectionEditableMixin, admin.StackedInline
):
    model = VendorOperationalAttributes
    form = VendorOperationalAttributesInlineForm
    verbose_name = _("Attributi Operativi")
    verbose_name_plural = _("Attributi Operativi")
    fieldsets = (
        (_("Capacità Operativa"), {"fields": ("total_operators",)}),
        (
            _("Mezzi e Attrezzature Proprie"),
            {
                "fields": (
                    "equipped_vans",
                    ("aerial_platforms", "aerial_platforms_notes"),
                    ("mobile_scaffolding", "mobile_scaffolding_notes"),
                    "equipped_vehicle_for_inspections",
                    ("lifting_equipment", "lifting_equipment_notes"),
                    "atex_equipment",
                )
            },
        ),
        (
            _("Condizioni Economiche"),
            {
                "fields": (
                    "standard_hourly_labor_cost",
                    "travel_cost",
                    ("mileage_reimbursement", "mileage_reimbursement_value"),
                    "consumable_materials_supply",
                    "specialist_materials_supply",
                )
            },
        ),
        (
            _("Disponibilità Operative"),
            {"fields": ("site_survey_availability", "travel_availability")},
        ),
        (
            _("Disponibilità Attività in Fermata Impianto/Weekend"),
            {
                "fields": (
                    "weekend_holiday_shutdown_availability",
                    "night_shutdown_availability",
                )
            },
        ),
        (
            _("Disponibilità Commissioning/Avviamenti"),
            {"fields": ("commissioning_support_availability",)},
        ),
        (_("Livello Autonomia"), {"fields": ("autonomy_category",)}),
        (
            _("Esperienza Settori Specifici"),
            {
                "fields": (
                    "experience_logistics",
                    "experience_data_center",
                    "experience_industry_manufacturing",
                    "experience_tertiary_offices_hospitality",
                    "experience_food_pharma",
                    "experience_healthcare",
                    "experience_retail",
                    "experience_oil_gas",
                    "experience_public_administration",
                )
            },
        ),
    )


class VendorAdminForm(forms.ModelForm):
    """ModelForm del VendorAdmin con controllo duplicati su Codice Embyon,
    Partita IVA e Codice Fiscale (AIDEV-21).

    Impedisce di salvare un fornitore che ripete Codice Embyon o Codice
    Fiscale già usati da un'altra anagrafica, indirizzando l'utente (via
    link) al Codice Fornitore esistente. La Partita IVA duplicata invece
    solo avvisa (AIDEV-173): più anagrafiche possono condividerla.
    Il controllo resta a livello di form admin: non introduce vincoli a
    livello di modello/DB, per non impattare gli script di
    ``data_migration_scripts/`` che scrivono direttamente sul modello.

    Ospita anche il selettore territoriale delle zone di competenza:
    un campo composito che rimpiazza i due M2M reali nel form.
    """

    competence_areas = CompetenceAreaField(
        label=_("Zone di competenza"),
        required=False,
        help_text=_(
            "Province italiane coperte e/o nazioni estere in cui il "
            "fornitore opera. Una regione risulta coperta per intero "
            "quando lo sono tutte le sue province."
        ),
    )

    # Solo in creazione: società della prima sezione (oltre alla Comune) e
    # conti Embyon scelti dalla ricerca "lente" (JSON).
    initial_company = forms.ModelChoiceField(
        label=_("Società"),
        queryset=Company.objects.real().filter(is_active=True),
        required=False,
        help_text=_(
            "Società per cui si censisce il fornitore: oltre alla sezione "
            "Comune viene creata la sezione di questa società."
        ),
    )
    sage_accounts = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Vendor
        # I due M2M territoriali sono esclusi perche' li gestisce il campo
        # composito `competence_areas`: lasciandoli, Django renderizzerebbe
        # anche i loro widget di default accanto al selettore.
        exclude = ("competence_provinces", "competence_countries")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["competence_areas"].initial = current_selection(
                self.instance
            )

    def _save_m2m(self):
        # Hook corretto per l'admin: `save(commit=False)` + `save_model()`
        # + `save_related()` finiscono qui passando da `form.save_m2m()`.
        super()._save_m2m()
        # Le zone si modificano solo nella sezione Comune: altrove il campo
        # non è mostrato e azzererebbe la selezione.
        if getattr(self, "section_code", COMMON_SECTION) != COMMON_SECTION:
            return
        selezione = self.cleaned_data.get("competence_areas") or {}
        set_vendor_competence(
            self.instance,
            province_codes=selezione.get("provinces", []),
            country_codes=selezione.get("countries", []),
        )

    def _check_manager_domain(self, user):
        domain = settings.VENDOR_MANAGER_EMAIL_DOMAIN.lower()
        if user and not (user.email or "").lower().endswith(f"@{domain}"):
            raise forms.ValidationError(
                _("L'utente %(user)s non ha un'email @%(domain)s."),
                params={"user": user, "domain": domain},
            )

    def clean_managed_by(self):
        user = self.cleaned_data.get("managed_by")
        self._check_manager_domain(user)
        return user

    def clean_secondary_managers(self):
        users = self.cleaned_data.get("secondary_managers")
        for user in users or []:
            self._check_manager_domain(user)
        return users

    def clean(self):
        cleaned = super().clean()
        primary = cleaned.get("managed_by")
        if primary and primary in (cleaned.get("secondary_managers") or []):
            self.add_error(
                "secondary_managers",
                _("L'utente primario non può essere anche secondario."),
            )
        category = cleaned.get("category")
        if category and category in (
            cleaned.get("additional_categories") or []
        ):
            self.add_error(
                "additional_categories",
                _(
                    "La classificazione principale non può essere anche "
                    "aggiuntiva."
                ),
            )
        return cleaned

    def _duplicate_message(self, value, label, lookup):

        if not value:
            return None
        other = Vendor.objects.filter(**{lookup: value})
        if self.instance.pk:
            other = other.exclude(pk=self.instance.pk)
        other = other.first()
        if not other:
            return None
        url = reverse("admin:vendors_vendor_change", args=[other.pk])
        return format_html(
            "{} già usato dal fornitore <strong>{}</strong> "
            '(<a href="{}" target="_blank" rel="noopener">'
            "Codice Fornitore {}</a>).",
            label,
            other.name or other.vendor_code,
            url,
            other.pk,
        )

    def _check_duplicate(self, value, label, lookup):
        message = self._duplicate_message(value, label, lookup)
        if message:
            raise forms.ValidationError(message)
        return value

    def clean_old_code(self):
        value = self.cleaned_data.get("old_code")
        return self._check_duplicate(value, _("Codice Embyon"), "old_code")

    def clean_sage_code(self):
        value = (self.cleaned_data.get("sage_code") or "").strip() or None
        if not value:
            return value
        other = Vendor.objects.filter(sage_code=value)
        if self.instance.pk:
            other = other.exclude(pk=self.instance.pk)
        other = other.first()
        if other:
            # Fornitore già censito: non si crea un doppione, si aggiunge
            # la sezione della società dalla sua pagina sezioni.
            raise forms.ValidationError(
                format_html(
                    "Fornitore già censito con codice SAGE {}: "
                    "<strong>{}</strong>. "
                    '<a href="{}">Apri il fornitore e aggiungi la sezione '
                    "della tua società</a>.",
                    value,
                    other.name or other.vendor_code,
                    sections_url(other.pk),
                )
            )
        return value

    def clean_sage_accounts(self):
        raw = self.cleaned_data.get("sage_accounts") or ""
        if not raw:
            return []
        try:
            data = json.loads(raw)
        except ValueError:
            return []
        return [row for row in data if isinstance(row, dict)]

    def clean_vat_number(self):
        value = self.cleaned_data.get("vat_number")
        if value:
            value = value.strip()
        # Una P.IVA può ripetersi (es. Gruppo IVA): non blocca il salvataggio,
        # l'avviso viene mostrato da VendorAdmin.save_model.
        self.vat_duplicate_warning = self._duplicate_message(
            value, _("Partita IVA"), "vat_number__iexact"
        )
        return value

    def clean_fiscal_code(self):
        value = self.cleaned_data.get("fiscal_code")
        if value:
            value = value.strip()
        return self._check_duplicate(
            value, _("Codice Fiscale"), "fiscal_code__iexact"
        )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """Società del gruppo: alias LDAP per riconoscere la società degli
    utenti. La riga "Comune" è la sezione condivisa dei fornitori."""

    list_display = [
        "code",
        "label",
        "sage_company",
        "ldap_aliases",
        "is_active",
    ]
    readonly_fields = ["code", "is_common"]
    fields = [
        "code",
        "label",
        "is_common",
        "sage_company",
        "embyon_company",
        "ldap_aliases",
        "sort_order",
        "is_active",
    ]

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False


class SectionTechnicianInline(SectionEditableMixin, TechnicianInline):
    pass


class SectionEquipmentInline(SectionEditableMixin, EquipmentInline):
    pass


# Vendor Admin (Enhanced)
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    form = VendorAdminForm
    list_display = [
        "vendor_code",
        "sage_code",
        "old_code",
        "sections_display",
        "name",
        "category",
        "qualification_status",
        "embyon_active",
        "final_evaluation_badge",
        "portal_activated",
    ]
    list_filter = [
        "qualification_status",
        "is_active",
        "category",
        "vendor_type",
        "vendor_final_evaluation",
        ("company_sections__company", admin.RelatedOnlyFieldListFilter),
        "embyon_active",
        "managed_by",
        "secondary_managers",
        # Zone di competenza, a cascata: la Regione mostra solo quelle
        # della Nazione scelta, la Provincia solo quelle della Regione
        # scelta.
        CompetenceCountryFilter,
        CompetenceRegionFilter,
        CompetenceProvinceFilter,
    ]
    # Mancava: `list_display` include `category`, quindi senza questo la
    # changelist faceva una query per riga.
    list_select_related = ("category", "managed_by")

    def get_queryset(self, request):
        # Per le colonne "Portale attivato" e "Sezioni" (evita una query
        # per riga).
        return (
            super()
            .get_queryset(request)
            .prefetch_related("users", "company_sections__company")
        )

    search_fields = [
        "vendor_code",
        "sage_code",
        "old_code",
        "company_sections__accounts__account_code",
        "name",
        "vat_number",
        "fiscal_code",
        "email",
    ]
    readonly_fields = [
        "vendor_code",
        "accounts_summary",
        "final_evaluation_badge",
        "is_qualified",
        "audit_overdue",
        "is_documentation_complete",
        "active_competences",
        "expired_competences",
        "expiring_competences",
        "missing_mandatory_competences",
        "valid_documents",
        "expired_documents",
        "expiring_documents",
        "missing_mandatory_documents",
        "primary_service",
        "active_services",
    ]
    autocomplete_fields = [
        "address",
        "category",
        "additional_categories",
        "qualification_type",
        "managed_by",
        "secondary_managers",
    ]
    inlines = [
        VendorCompanyInline,
        VendorServiceInline,
        VendorCompetenceInline,
        DocumentInline,
        ContractInline,
        VendorEvaluationInline,
        VendorOperationalAttributesInline,
        SectionTechnicianInline,
        SectionEquipmentInline,
    ]
    # Questa tupla definisce l'ordine dei tab
    jazzmin_section_order = (
        _("Informazioni Base"),
        _("Contatti"),
        _("Documenti Contrattuali"),
        _("Contratti"),
        _("Servizi Erogati"),
        _("Abilitazioni e Requisiti Professionali"),
        _("Qualifica e Audit"),
        _("Valutazioni"),
        _("Attributi Operativi"),
        _("Tecnici"),
        _("Mezzi/dotazioni"),
    )

    def get_changelist(self, request, **kwargs):
        return SectionChangeList

    def _initial_company(self, request, form):
        """Società della prima sezione di un fornitore nuovo: per chi ha una
        società è sempre la sua."""
        user = getattr(request, "user", None)
        user_company = getattr(user, "company", None)
        if user_company and not user.is_superuser:
            return user_company
        chosen = form.cleaned_data.get("initial_company") if form else None
        return chosen or user_company

    def save_model(self, request, obj, form, change):
        # Un fornitore nuovo parte sempre "In attesa", qualunque valore
        # sia stato scelto nel form.
        company = None
        if not change:
            obj.qualification_status = "PENDING"
            # Chi censisce il fornitore ne diventa il primo utente di
            # gestione, se non ne è già stato indicato uno.
            user = getattr(request, "user", None)
            if not obj.managed_by_id and getattr(user, "role", None) in (
                "admin",
                "bo_user",
                "buyer",
            ):
                obj.managed_by = user
            company = self._initial_company(request, form)
            if company is not None:
                obj.embyon_company = company.embyon_company or None
        super().save_model(request, obj, form, change)
        if company is not None:
            accounts = form.cleaned_data.get("sage_accounts") if form else []
            create_section_with_accounts(obj, company, accounts or [])
        warning = getattr(form, "vat_duplicate_warning", None)
        if warning:
            self.message_user(request, warning, messages.WARNING)
        if change and "email" in getattr(form, "changed_data", ()):
            stale = [
                u.email
                for u in portal_users(obj)
                if u.email.lower() != (obj.email or "").lower()
            ]
            if stale:
                self.message_user(
                    request,
                    f"L'accesso al portale usa ancora {', '.join(stale)}: da "
                    '"Accesso portale" puoi aggiornarlo e reinviare le '
                    "credenziali.",
                    messages.WARNING,
                )

    def get_form(self, request, obj=None, **kwargs):
        # Salva l'oggetto corrente per usarlo negli inline
        request._obj_ = obj
        form = super().get_form(request, obj, **kwargs)
        section = current_section(request)
        form.section_code = section.code if section else COMMON_SECTION
        company = getattr(request.user, "company", None)
        if obj is None and company and not request.user.is_superuser:
            # Chi ha una società censisce i fornitori per la sua società.
            base_init = form.__init__

            def __init__(self, *args, **kw):
                base_init(self, *args, **kw)
                field = self.fields["initial_company"]
                field.initial = company.pk
                field.disabled = True

            form = type(form.__name__, (form,), {"__init__": __init__})
        return form

    def _company_section_open(self, request):
        section = current_section(request)
        return section is not None and not section.is_common

    def has_change_permission(self, request, obj=None):
        # Sezione di un'altra società: tutta la scheda in sola lettura.
        if obj is not None and not section_editable(request):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not section_editable(request):
            return False
        return super().has_delete_permission(request, obj)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            base, contacts = self.fieldsets[0], self.fieldsets[1]
            fields = ("initial_company", "sage_accounts", *base[1]["fields"])
            return ((base[0], {"fields": fields}), contacts)
        if self._company_section_open(request):
            return (
                (
                    _("Informazioni Base"),
                    {
                        "fields": (
                            "vendor_code",
                            "sage_code",
                            "name",
                            "vat_number",
                            "fiscal_code",
                        )
                    },
                ),
            )
        if obj.has_company_sections:
            # La qualifica si gestisce nelle sezioni delle società.
            return self.fieldsets[:2]
        return self.fieldsets

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None and not request.user.is_superuser:
            fields.append("sage_code")
        if obj is not None and self._company_section_open(request):
            fields += ["sage_code", "name", "vat_number", "fiscal_code"]
        return fields

    def get_inline_instances(self, request, obj=None):
        # In creazione niente inline: dopo il salvataggio si sceglie la
        # sezione. Nella sezione di una società: qualifica della società più
        # gli elementi della sezione; nella Comune gli elementi comuni.
        # Attributi operativi, tecnici e mezzi solo per i subappaltatori e
        # solo nella sezione Sicura (Comune per i fornitori senza società).
        if obj is None:
            return []
        instances = super().get_inline_instances(request, obj)
        subcontractor_inlines = (
            VendorOperationalAttributesInline,
            SectionTechnicianInline,
            SectionEquipmentInline,
        )
        section = current_section(request)
        code = section.code if section else COMMON_SECTION
        show_subcontractor = (
            obj.is_subappaltatore and subcontractor_section(obj) == code
        )
        excluded = (
            ()
            if self._company_section_open(request)
            else (VendorCompanyInline,)
        )
        if not show_subcontractor:
            excluded += subcontractor_inlines
        return [
            inline for inline in instances if not isinstance(inline, excluded)
        ]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "document-sets/",
                self.admin_site.admin_view(self.document_sets_view),
                name="vendors_vendor_document_sets",
            ),
            path(
                "competence-sets/",
                self.admin_site.admin_view(self.competence_sets_view),
                name="vendors_vendor_competence_sets",
            ),
            path(
                "service-sets/",
                self.admin_site.admin_view(self.service_sets_view),
                name="vendors_vendor_service_sets",
            ),
            path(
                "document-type-validity/",
                self.admin_site.admin_view(self.document_type_validity_view),
                name="vendors_vendor_document_type_validity",
            ),
            path(
                "competence-validity/",
                self.admin_site.admin_view(self.competence_validity_view),
                name="vendors_vendor_competence_validity",
            ),
            path(
                "extract-dates/",
                self.admin_site.admin_view(self.extract_dates_view),
                name="vendors_vendor_extract_dates",
            ),
            path(
                "embyon-search/",
                self.admin_site.admin_view(self.embyon_search_view),
                name="vendors_vendor_embyon_search",
            ),
            path(
                "duplicate-check/",
                self.admin_site.admin_view(self.duplicate_check_view),
                name="vendors_vendor_duplicate_check",
            ),
            path(
                "link-sage/",
                self.admin_site.admin_view(self.link_sage_view),
                name="vendors_vendor_link_sage",
            ),
            path(
                "<path:object_id>/sezioni/",
                self.admin_site.admin_view(self.sections_view),
                name="vendors_vendor_sections",
            ),
            path(
                "<path:object_id>/sezioni/aggiungi/",
                self.admin_site.admin_view(self.add_section_view),
                name="vendors_vendor_add_section",
            ),
            path(
                "<path:object_id>/duplicati-sezione/",
                self.admin_site.admin_view(self.section_duplicates_view),
                name="vendors_vendor_section_duplicates",
            ),
            path(
                "<path:object_id>/salva-contratto/",
                self.admin_site.admin_view(self.contract_quick_save_view),
                name="vendors_vendor_contract_save",
            ),
            path(
                "<path:object_id>/accesso-portale/",
                self.admin_site.admin_view(self.portal_access_view),
                name="vendors_vendor_portal_access",
            ),
            path(
                "<path:object_id>/zip/<str:section>/",
                self.admin_site.admin_view(self.download_zip_view),
                name="vendors_vendor_download_zip",
            ),
        ]
        return custom + urls

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save_and_continue"] = False
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        # Stato dell'accesso al portale, per l'etichetta del pulsante
        # "Crea/Gestisci accesso portale".
        extra_context = extra_context or {}
        extra_context["show_save_and_continue"] = False
        obj = self.get_object(request, unquote(object_id))
        if obj is not None:
            code = request.GET.get(SECTION_PARAM, "")
            if not code:
                if request.method == "GET" and IS_POPUP_VAR not in request.GET:
                    return redirect(sections_url(obj.pk))
                code = COMMON_SECTION
            section = resolve_section(obj, code)
            if section is None:
                raise Http404(_("Sezione non presente per questo fornitore"))
            request._section_ = section
            request._section_editable_ = can_edit_section(
                request.user, section.code
            )
            extra_context.update(
                {
                    "has_portal_users": portal_users(obj).exists(),
                    "current_section": section,
                    "section_editable": request._section_editable_,
                    "sections_url": sections_url(obj.pk),
                    "vendor_sections": vendor_sections(obj),
                    "section_param": SECTION_PARAM,
                }
            )
        return super().change_view(request, object_id, form_url, extra_context)

    def sections_view(self, request, object_id):
        """Pagina di scelta della sezione del fornitore: Comune e una card
        per ogni società, con stato di qualifica e permessi dell'utente."""
        vendor = self.get_object(request, unquote(object_id))
        if vendor is None:
            raise Http404
        if not self.has_view_permission(request, vendor):
            raise PermissionDenied
        sections = list(
            vendor.company_sections.select_related("company").prefetch_related(
                "accounts"
            )
        )
        user = request.user
        cards = [
            {
                "code": COMMON_SECTION,
                "label": _("Comune"),
                "common": True,
                "editable": can_edit_section(user, COMMON_SECTION),
                "url": section_url(vendor.pk, COMMON_SECTION),
            }
        ]
        for section in sections:
            cards.append(
                {
                    "code": section.company_id,
                    "label": section.company.label,
                    "common": False,
                    "editable": can_edit_section(user, section.company_id),
                    "url": section_url(vendor.pk, section.company_id),
                    "section": section,
                    "accounts": section.account_codes(),
                    "badge_class": STATUS_COLORS.get(
                        section.qualification_status, "secondary"
                    ),
                    "final_color": FINAL_EVALUATION_COLORS.get(
                        section.vendor_final_evaluation, "#6c757d"
                    ),
                }
            )
        present = {s.company_id for s in sections}
        addable = [
            company
            for company in Company.objects.real().filter(is_active=True)
            if company.code not in present
            and can_edit_section(user, company.code)
        ]
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": vendor,
            "title": _("Scegli la sezione del fornitore"),
            "cards": cards,
            "addable": addable,
            "user_company": getattr(user, "company", None),
        }
        return TemplateResponse(
            request, "admin/vendors/vendor/section_select.html", context
        )

    def add_section_view(self, request, object_id):
        """POST: aggiunge al fornitore la sezione di una società (di norma
        quella dell'utente) e apre la nuova sezione."""
        vendor = self.get_object(request, unquote(object_id))
        if vendor is None:
            raise Http404
        if request.method != "POST":
            return redirect(sections_url(vendor.pk))
        code = (request.POST.get("company") or "").upper()
        if not user_can_add_section(request.user, vendor, code):
            raise PermissionDenied
        company = Company.objects.get(pk=code)
        create_section_with_accounts(vendor, company, [])
        self.message_user(
            request,
            _("Sezione %(company)s aggiunta al fornitore.")
            % {"company": company.label},
            messages.SUCCESS,
        )
        return redirect(section_url(vendor.pk, code))

    def section_duplicates_view(self, request, object_id):
        """JSON: elementi dello stesso tipo già presenti in ALTRE sezioni del
        fornitore (documento o requisito), per la modale di avviso prima del
        caricamento. Non blocca nulla."""
        vendor = self.get_object(request, unquote(object_id))
        if vendor is None:
            raise Http404
        kind = request.GET.get("kind", "")
        type_id = request.GET.get("type", "")
        code = (request.GET.get(SECTION_PARAM) or COMMON_SECTION).upper()
        if not type_id or kind not in ("document", "competence"):
            return JsonResponse({"matches": [], "scope": None})
        if kind == "document":
            catalog = DocumentCatalog.objects.filter(pk=type_id).first()
            qs = Document.objects.filter(vendor=vendor, document_type=catalog)
        else:
            catalog = Competence.objects.filter(pk=type_id).first()
            qs = VendorCompetence.objects.filter(
                vendor=vendor, competence=catalog
            )
        if catalog is None:
            return JsonResponse({"matches": [], "scope": None})
        matches = [
            {
                "company": item.company_id,
                "label": item.company.label,
                "status": item.get_status_display()
                if kind == "document"
                else VALIDITY_STATUS_META.get(
                    item.validity_status, (item.validity_status,)
                )[0],
                "expiry": item.expiry_date.strftime("%d/%m/%Y")
                if item.expiry_date
                else "",
            }
            for item in duplicates_in_other_sections(qs, code)
        ]
        return JsonResponse(
            {
                "matches": matches,
                "scope": catalog.scope,
                "name": catalog.name,
                "section": code,
            }
        )

    def link_sage_view(self, request):
        """POST dalla lente su un fornitore già censito: collega il codice
        SAGE e aggiunge la sezione della società scelta (se l'utente può),
        con i suoi conti. Non crea mai un fornitore nuovo."""
        if request.method != "POST":
            return JsonResponse({"error": "POST richiesto"}, status=405)
        vendor = Vendor.objects.filter(
            pk=request.POST.get("vendor", "")
        ).first()
        sage = (request.POST.get("sage_code") or "").strip()
        code = (request.POST.get("company") or "").upper()
        if vendor is None or not sage:
            return JsonResponse({"error": "Dati mancanti"}, status=400)
        if vendor.sage_code and vendor.sage_code != sage:
            return JsonResponse(
                {"error": "Il fornitore ha già un altro codice SAGE"},
                status=409,
            )
        if not vendor.sage_code:
            Vendor.objects.filter(pk=vendor.pk).update(sage_code=sage)
        if code and user_can_add_section(request.user, vendor, code):
            try:
                accounts = json.loads(request.POST.get("accounts") or "[]")
            except ValueError:
                accounts = []
            create_section_with_accounts(
                vendor, Company.objects.get(pk=code), accounts
            )
            return JsonResponse({"url": section_url(vendor.pk, code)})
        return JsonResponse({"url": sections_url(vendor.pk)})

    def _keep_section_in_redirect(self, request, response):
        section = current_section(request)
        location = getattr(response, "url", None)
        if section is None or not location or SECTION_PARAM in location:
            return response
        separator = "&" if "?" in location else "?"
        response["Location"] = (
            f"{location}{separator}{SECTION_PARAM}={section.code}"
        )
        return response

    def _salva_resta_sulla_scheda(self, request):
        # "Salva" si comporta come "Salva e continua": si resta sulla scheda
        # corrente. Il pulsante "Salva e continua" non è più mostrato.
        if "_save" in request.POST:
            post = request.POST.copy()
            post["_continue"] = "1"
            request.POST = post

    def response_add(self, request, obj, post_url_continue=None):
        self._salva_resta_sulla_scheda(request)
        response = super().response_add(request, obj, post_url_continue)
        if IS_POPUP_VAR in request.POST:
            return response
        # Fornitore creato: si sceglie la sezione su cui lavorare.
        return redirect(sections_url(obj.pk))

    def response_change(self, request, obj):
        self._salva_resta_sulla_scheda(request)
        response = super().response_change(request, obj)
        return self._keep_section_in_redirect(request, response)

    def _zip_entries(self, vendor, section, company=None):
        """File allegati alla sezione, come coppie (etichetta, FieldFile).
        Con `company` solo quelli di quella sezione del fornitore."""
        if section == "documenti":
            documents = vendor.documents.select_related("document_type")
            if company:
                documents = documents.filter(company_id=company)
            return [
                (doc.document_type.name, doc.file)
                for doc in documents.exclude(file="").exclude(
                    file__isnull=True
                )
            ]
        if section == "abilitazioni":
            assignments = vendor.vendor_competences.select_related(
                "competence"
            )
            if company:
                assignments = assignments.filter(company_id=company)
            return [
                (assignment.competence.name, assignment.document_file)
                for assignment in assignments.exclude(
                    document_file=""
                ).exclude(document_file__isnull=True)
            ]
        raise Http404

    def download_zip_view(self, request, object_id, section):
        """Scarica in un .zip i file allegati a una sezione del fornitore.

        Se un file non è leggibile dallo storage il download non parte: lo zip
        sarebbe incompleto senza che l'operatore se ne accorga.
        """
        vendor = self.get_object(request, unquote(object_id))
        if vendor is None:
            raise Http404
        if not self.has_view_permission(request, vendor):
            raise PermissionDenied
        entries = self._zip_entries(
            vendor, section, request.GET.get(SECTION_PARAM, "").upper()
        )

        buffer = io.BytesIO()
        unreadable = []
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for index, (label, field) in enumerate(entries, start=1):
                name = re.sub(
                    r'[\\/:*?"<>|]',
                    "_",
                    f"{index:02d} - {label} - {os.path.basename(field.name)}",
                )
                try:
                    with field.open("rb") as stored:
                        archive.writestr(name, stored.read())
                except OSError:
                    unreadable.append(field.name)

        if unreadable:
            self.message_user(
                request,
                "Download non riuscito: file non leggibili: "
                + ", ".join(unreadable),
                messages.ERROR,
            )
            code = request.GET.get(SECTION_PARAM, "").upper()
            return redirect(section_url(vendor.pk, code or COMMON_SECTION))

        response = HttpResponse(
            buffer.getvalue(), content_type="application/zip"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{vendor.vendor_code}_{section}.zip"'
        )
        return response

    def portal_access_view(self, request, object_id):
        """Crea l'utenza portale del fornitore e invia l'invito.

        GET mostra la pagina di conferma (la toolbar della scheda sta dentro
        il form principale, quindi non può ospitare un secondo form POST);
        POST `action=create` crea l'utente con l'email dell'anagrafica e
        invia il link "imposta password", `action=resend` reinvia l'invito a
        un utente che non ha ancora impostato la password.
        """
        vendor = self.get_object(request, unquote(object_id))
        if vendor is None:
            raise Http404
        if not self.has_change_permission(request, vendor):
            raise PermissionDenied
        can_add_user = request.user.has_perm("users.add_user")
        # L'accesso al portale riguarda l'anagrafica: si torna alla Comune.
        change_url = section_url(vendor.pk, COMMON_SECTION)

        if request.method == "POST":
            action = request.POST.get("action")
            if action == "create":
                if not can_add_user:
                    raise PermissionDenied
                try:
                    user = create_portal_user(vendor)
                except PortalAccessError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
                    return redirect(request.path)
                invite_and_notify(self, request, user, created=True)
                return redirect(change_url)
            if action == "resend":
                user = (
                    portal_users(vendor)
                    .filter(pk=request.POST.get("user"))
                    .first()
                )
                if user is None or not pending_invite(user):
                    self.message_user(
                        request,
                        "Reinvio non possibile: l'utente non esiste o ha "
                        "già impostato la password.",
                        messages.ERROR,
                    )
                    return redirect(request.path)
                invite_and_notify(self, request, user, created=False)
                return redirect(change_url)
            if action == "reset":
                if not request.user.has_perm("users.change_user"):
                    raise PermissionDenied
                user = (
                    portal_users(vendor)
                    .filter(pk=request.POST.get("user"), is_active=True)
                    .first()
                )
                if user is None or user.is_ldap_user:
                    self.message_user(
                        request,
                        "Reinvio non possibile: utente non trovato, "
                        "disattivato o autenticato via LDAP.",
                        messages.ERROR,
                    )
                    return redirect(request.path)
                try:
                    old_email = reset_portal_credentials(user, vendor.email)
                except PortalAccessError as exc:
                    self.message_user(request, str(exc), messages.ERROR)
                    return redirect(request.path)
                if old_email.lower() != user.email.lower():
                    self.message_user(
                        request,
                        f"Email di accesso aggiornata da {old_email} a "
                        f"{user.email}: la vecchia non può più accedere.",
                        messages.SUCCESS,
                    )
                invite_and_notify(self, request, user, created=False)
                return redirect(change_url)
            return HttpResponseNotAllowed(["GET", "POST"])

        users = []
        for user in portal_users(vendor):
            pending = pending_invite(user)
            email_differs = bool(
                vendor.email and user.email.lower() != vendor.email.lower()
            )
            # Reset (nuova password + email allineata): per chi ha già una
            # password, o per un invito in attesa verso una vecchia email.
            can_reset = bool(
                user.is_active
                and vendor.email
                and not user.is_ldap_user
                and (not pending or email_differs)
            )
            users.append((user, pending, email_differs, can_reset))
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": vendor,
            "title": _("Accesso al portale fornitori"),
            "portal_users": users,
            "can_create": can_add_user and not users,
            "change_url": change_url,
            "email_redirect_to": settings.EMAIL_REDIRECT_TO,
            "invite_days": settings.PORTAL_INVITE_TIMEOUT_DAYS,
        }
        return TemplateResponse(
            request, "admin/vendors/vendor/portal_access.html", context
        )

    def duplicate_check_view(self, request):
        """Controllo live (AJAX) di duplicati su Codice Embyon, Partita IVA
        o Codice Fiscale rispetto ai fornitori già presenti in anagrafica
        locale (AIDEV-21).

        Usato dal tab "Informazioni Base" per segnalare un doppione appena
        l'utente esce dal campo, senza attendere il salvataggio. La stessa
        validazione è comunque applicata (obbligatoriamente) anche lato
        server in ``VendorAdminForm``, per restare valida anche a JS
        disattivato.

        Accetta come filtri (GET): ``field`` (uno tra old_code, vat_number,
        fiscal_code), ``value`` e, in modifica, ``pk`` (Codice Fornitore
        corrente, escluso dal confronto).
        """

        field = request.GET.get("field", "").strip()
        value = request.GET.get("value", "").strip()
        current_pk = request.GET.get("pk", "").strip()

        lookups = {
            "old_code": "old_code",
            "sage_code": "sage_code",
            "vat_number": "vat_number__iexact",
            "fiscal_code": "fiscal_code__iexact",
        }
        if field not in lookups or not value:
            return JsonResponse({"duplicate": False})

        qs = Vendor.objects.filter(**{lookups[field]: value})
        if current_pk:
            qs = qs.exclude(pk=current_pk)
        other = qs.first()
        sage_code = ""
        if (
            not other
            and not current_pk
            and field in ("vat_number", "fiscal_code")
        ):
            other, sage_code = self._registered_by_sage(field, value)
        if not other:
            return JsonResponse({"duplicate": False})

        return JsonResponse(
            {
                "duplicate": True,
                "sage": bool(sage_code or field == "sage_code"),
                "sage_code": sage_code or other.sage_code or "",
                "vendor_code": other.pk,
                "vendor_name": other.name or other.pk,
                "change_url": sections_url(other.pk),
            }
        )

    def _registered_by_sage(self, field, value):
        """Nuovo fornitore: P.IVA/C.F. -> codice SAGE (viste FABRIC_HUB) ->
        fornitore già censito con quel codice o con un suo conto."""
        criteria = {"vat": value} if field == "vat_number" else {}
        if field == "fiscal_code":
            criteria = {"fiscal_code": value}
        try:
            rows = fabric_hub.search_shared_suppliers(limit=5, **criteria)
        except Exception:  # pragma: no cover - dipende dal servizio esterno
            return None, ""
        for row in rows:
            vendor = find_registered_vendor(row)
            if vendor:
                return vendor, row["sage_code"]
        return None, ""

    def embyon_search_view(self, request):
        """Ricerca fornitori nelle viste FABRIC_HUB dei fornitori condivisi
        (``v_suppliers`` / ``v_supplier_companies``, vedi ``fabric_hub.py``).

        Usata dal modal "lente" nel tab Informazioni Base. Filtri (GET), uno
        solo per volta: name, account_code (codice Embyon), sage_code,
        vat_number, fiscal_code. Ogni risultato riporta i conti per società
        e, se il fornitore è già censito (per codice SAGE o per conto), il
        fornitore esistente: in quel caso non se ne crea un altro.
        """
        params = {
            key: request.GET.get(key, "").strip()
            for key in (
                "name",
                "account_code",
                "sage_code",
                "vat_number",
                "fiscal_code",
            )
        }
        # Compatibilità con il vecchio parametro del codice Embyon.
        params["account_code"] = params["account_code"] or (
            request.GET.get("old_code", "").strip()
        )
        if params["name"] and len(params["name"]) < 3:
            return JsonResponse(
                {
                    "results": [],
                    "error": str(
                        _(
                            "Inserisci almeno 3 caratteri per la "
                            "ragione sociale."
                        )
                    ),
                }
            )
        if not any(params.values()):
            return JsonResponse(
                {
                    "results": [],
                    "error": str(
                        _(
                            "Imposta un criterio di ricerca: ragione sociale, "
                            "codice Embyon, codice SAGE, partita IVA o codice "
                            "fiscale."
                        )
                    ),
                }
            )

        try:
            results = fabric_hub.search_shared_suppliers(
                name=params["name"],
                account_code=params["account_code"],
                sage_code=params["sage_code"],
                vat=params["vat_number"],
                fiscal_code=params["fiscal_code"],
            )
        except Exception as exc:  # pragma: no cover - dipende dal DB esterno
            return JsonResponse(
                {
                    "results": [],
                    "error": str(_("Errore nella ricerca fornitori: %s"))
                    % exc,
                },
                status=500,
            )

        for row in results:
            vendor = find_registered_vendor(row)
            row["existing_vendor"] = (
                {
                    "pk": vendor.pk,
                    "name": vendor.name,
                    "sections": list(
                        vendor.company_sections.values_list(
                            "company_id", flat=True
                        )
                    ),
                }
                if vendor
                else None
            )
        return JsonResponse(
            {
                "results": results,
                "user_company": getattr(request.user, "company_id", None)
                or "",
            }
        )

    def extract_dates_view(self, request):
        """POST di un file → date di rilascio/scadenza lette con OCR, per
        pre-compilare le righe Documenti e Abilitazioni. Non salva nulla."""
        if request.method != "POST":
            return JsonResponse({"error": "POST richiesto"}, status=405)
        return JsonResponse(suggested_dates(request.FILES.get("file")))

    def contract_quick_save_view(self, request, object_id):
        """POST dei campi di una riga contratto nuova → la crea subito per il
        fornitore, senza attendere il salvataggio dell'intera scheda. Il JS
        poi toglie la riga dal formset, così il submit finale non la
        duplica (contract_number è unique)."""
        if request.method != "POST":
            return JsonResponse({"error": "POST richiesto"}, status=405)
        vendor = self.get_object(request, unquote(object_id))
        if vendor is None:
            return JsonResponse({"error": "Fornitore non trovato"}, status=404)
        code = (request.GET.get(SECTION_PARAM) or COMMON_SECTION).upper()
        if not (
            self.has_change_permission(request, vendor)
            and request.user.has_perm("vendors.add_contract")
            and resolve_section(vendor, code) is not None
            and can_edit_section(request.user, code)
        ):
            return JsonResponse({"error": "Permesso negato"}, status=403)
        form = modelform_factory(Contract, fields=ContractInline.fields)(
            request.POST
        )
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)
        contract = form.save(commit=False)
        contract.vendor = vendor
        contract.company_id = code
        contract.save()
        return JsonResponse(
            {
                "id": str(contract.pk),
                "contract_number": contract.contract_number,
                "title": contract.title,
            }
        )

    def document_type_validity_view(self, request):
        """Restituisce, per ogni tipo di documento attivo, la durata di
        validità in giorni (validity_period_days). Usato dal JS che
        calcola in automatico la Data di Scadenza a partire dalla Data di
        Emissione nel tab Documenti."""
        types = {
            dt.pk: {
                "days": dt.validity_period_days,
                "requires_renewal": dt.requires_renewal,
                "reminder": dt.reminder_days_before,
            }
            for dt in DocumentCatalog.objects.filter(is_active=True).only(
                "pk",
                "validity_period_days",
                "requires_renewal",
                "reminder_days_before",
            )
        }
        return JsonResponse({"types": types})

    def competence_validity_view(self, request):
        """Come document_type_validity_view, per i requisiti professionali:
        serve al JS che calcola la Data Scadenza dalla Data Rilascio nel tab
        Abilitazioni e Requisiti."""
        types = {
            str(c.pk): {
                "days": c.validity_period_days,
                "requires_renewal": c.requires_renewal,
            }
            for c in Competence.objects.filter(is_active=True).only(
                "pk", "validity_period_days", "requires_renewal"
            )
        }
        return JsonResponse({"types": types})

    def document_sets_view(self, request):
        """Restituisce i set documentali attivi (filtrati per la
        Classificazione del fornitore, se nota) con i relativi tipi di
        documento. Usato dal dropdown 'Set Documentale' nel tab
        Documenti."""
        qs = DocumentSet.objects.filter(is_active=True).prefetch_related(
            "document_types"
        )

        category_ids = []
        vendor_id = request.GET.get("vendor")
        if vendor_id:
            vendor = Vendor.objects.filter(pk=vendor_id).first()
            if vendor:
                if vendor.category_id:
                    category_ids.append(vendor.category_id)
                category_ids.extend(
                    vendor.additional_categories.values_list("pk", flat=True)
                )

        # Con classificazione nota (principale e/o aggiuntive): set
        # universali (category nullo) + set di quelle classificazioni.
        # Senza classificazione (o in creazione): tutti i set attivi.
        if category_ids:
            qs = qs.filter(
                Q(category__isnull=True) | Q(category_id__in=category_ids)
            )

        sets = [
            {
                "id": s.pk,
                "name": s.name,
                "default_status": s.default_status,
                "document_types": [
                    {"id": dt.pk, "text": str(dt)}
                    for dt in s.document_types.all()
                ],
            }
            for s in qs
        ]
        return JsonResponse({"sets": sets})

    def _vendor_category_scope(self, request):
        """Classificazioni del fornitore in URL (principale e aggiuntive), con
        i loro antenati.
        Restituisce None quando il fornitore non è noto (form di
        creazione) o è privo di classificazione: in quel caso vanno
        mostrati tutti i set attivi."""
        vendor_id = request.GET.get("vendor")
        if not vendor_id:
            return None
        vendor = (
            Vendor.objects.filter(pk=vendor_id)
            .select_related("category")
            .first()
        )
        if not vendor:
            return None
        return vendor_category_scope_ids(vendor) or None

    def competence_sets_view(self, request):
        """Restituisce i set di requisiti professionali attivi (filtrati per la
        Classificazione del fornitore, se nota) con i relativi requisiti. Usato
        dal dropdown 'Set Requisiti' nel tab Requisiti Professionali."""
        qs = CompetenceSet.objects.filter(is_active=True).prefetch_related(
            "competences"
        )

        scope = self._vendor_category_scope(request)
        if scope:
            qs = qs.filter(Q(category__isnull=True) | Q(category_id__in=scope))

        sets = [
            {
                "id": s.pk,
                "name": s.name,
                "items": [
                    {"id": str(c.pk), "text": str(c)}
                    for c in s.competences.filter(is_active=True)
                ],
            }
            for s in qs
        ]
        return JsonResponse({"sets": sets})

    def service_sets_view(self, request):
        """Restituisce i set di servizi attivi (filtrati per la Classificazione
        del fornitore, se nota) con i relativi servizi. Usato dal dropdown
        'Set Servizi' nel tab Servizi.

        Le categorie di servizio (ServiceType senza parent) sono escluse: come
        nell'inline Servizi si assegnano solo i servizi specifici."""
        qs = ServiceSet.objects.filter(is_active=True).prefetch_related(
            "service_types"
        )

        scope = self._vendor_category_scope(request)
        if scope:
            qs = qs.filter(Q(category__isnull=True) | Q(category_id__in=scope))

        sets = [
            {
                "id": s.pk,
                "name": s.name,
                "items": [
                    {"id": str(st.pk), "text": str(st)}
                    for st in s.service_types.filter(
                        is_active=True, parent__isnull=False
                    )
                ],
            }
            for s in qs
        ]
        return JsonResponse({"sets": sets})

    class Media:
        js = (
            "admin/js/vendor_form_guard.js",
            "admin/js/vendor_inline_trash.js",
            "admin/js/contract_quick_save.js",
            "admin/js/set_applier_base.js",
            "admin/js/document_set_applier.js",
            "admin/js/competence_set_applier.js",
            "admin/js/service_set_applier.js",
            "admin/js/document_expiry_calc.js",
            "admin/js/ocr_dates_admin.js",
            "admin/js/embyon_search.js",
            "admin/js/vendor_duplicate_check.js",
            "admin/js/section_duplicate_warning.js",
        )
        css = {
            "all": (
                "admin/css/vendor_operational_attributes.css",
                "admin/css/vendor_managers.css",
                "admin/css/vendor_inline_scroll.css",
            )
        }

    fieldsets = (
        (
            _("Informazioni Base"),
            {
                "fields": (
                    "vendor_code",
                    "sage_code",
                    ("managed_by", "secondary_managers"),
                    "name",
                    "vendor_type",
                    "vat_number",
                    "fiscal_code",
                    "qualification_type",
                    "category",
                    "additional_categories",
                    "competence_areas",
                    "first_supply_date",
                    "risk_level",
                    "embyon_active",
                    "is_active",
                )
            },
        ),
        (
            _("Contatti"),
            {
                "fields": (
                    "email",
                    "expiry_notifications_enabled",
                    "phone",
                    "reference_contact",
                    "pec",
                    "website",
                    "address",
                    "contact_details",
                )
            },
        ),
        # remove this section if not needed
        #        (_('Performance'), {
        #            'fields': (
        #                'on_time_delivery_rate', 'quality_rating_avg',
        #                'average_response_time', 'fulfillment_rate'
        #            )
        #        }),
        (
            _("Qualifica e Audit"),
            {
                "fields": (
                    "qualification_status",
                    "final_evaluation_badge",
                    "qualification_score",
                    "qualification_date",
                    "qualification_expiry",
                    "last_audit_date",
                    "next_audit_due",
                    "is_qualified",
                    "audit_overdue",
                    "review_notes",
                )
            },
        ),
    )

    def is_qualified_display(self, obj):
        if obj.is_qualified:
            return format_html(
                '<span style="color: green; font-weight: bold;">'
                "✓ Qualificato</span>"
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">'
            "✗ Non Qualificato</span>"
        )

    is_qualified_display.short_description = _("Qualificato")

    FINAL_EVALUATION_COLORS = {
        "POSITIVO": "#28a745",
        "NEGATIVO": "#dc3545",
        "DA VALUTARE": "#6c757d",
    }

    def final_evaluation_badge(self, obj):
        value = obj.vendor_final_evaluation or "DA VALUTARE"
        return format_html(
            '<span style="color: {}; font-weight: bold;">&#9679; {}</span>',
            self.FINAL_EVALUATION_COLORS.get(value, "#6c757d"),
            obj.get_vendor_final_evaluation_display() or value,
        )

    final_evaluation_badge.short_description = _(
        "Valutazione Finale del Fornitore"
    )
    final_evaluation_badge.admin_order_field = "vendor_final_evaluation"

    @admin.display(description=_("Sezioni società"))
    def sections_display(self, obj):
        return section_badges(obj)

    @admin.display(description=_("Conti Embyon per società"))
    def accounts_summary(self, obj):
        rows = [
            (section.company.label, section.account_codes() or "-")
            for section in obj.company_sections.select_related(
                "company"
            ).prefetch_related("accounts")
        ]
        if not rows:
            return "-"
        return format_html_join(
            mark_safe("<br>"), "<strong>{}</strong>: {}", rows
        )

    @admin.display(description=_("Portale attivato"), boolean=True)
    def portal_activated(self, obj):
        """Vero se un utente del portale ha già impostato le credenziali
        (invito accettato). Usa gli utenti prefetchati: nessuna query per
        riga."""
        return any(
            u.role == "vendor" and (u.is_ldap_user or u.has_usable_password())
            for u in obj.users.all()
        )

    actions = ["approve_vendors", "reject_vendors", "mark_for_audit"]

    def _action_holders(self, request, queryset):
        """Per le azioni di qualifica: la sezione della società dell'utente
        (o quella filtrata nel changelist, per il superuser) oppure il
        fornitore stesso se non ha sezioni. Restano fuori i fornitori senza
        quella sezione."""
        user = getattr(request, "user", None)
        code = getattr(user, "company_id", None)
        if getattr(user, "is_superuser", False):
            code = (
                request.GET.get("company_sections__company__code__exact")
                or code
            )
        holders, skipped = [], []
        for vendor in queryset:
            if not vendor.has_company_sections:
                holders.append(vendor)
                continue
            section = vendor.company_sections.filter(company_id=code).first()
            if section is None:
                skipped.append(vendor.name)
            else:
                holders.append(section)
        if skipped:
            self.message_user(
                request,
                _("Senza sezione della tua società, non modificati: %s")
                % ", ".join(skipped),
                "warning",
            )
        return holders

    def approve_vendors(self, request, queryset):
        # Approva solo i fornitori con documenti e requisiti obbligatori in
        # regola (caricati, verificati, non scaduti).
        approved = 0
        for holder in self._action_holders(request, queryset):
            vendor = getattr(holder, "vendor", holder)
            blockers = holder.qualification_blockers
            if blockers:
                self.message_user(
                    request,
                    f"{vendor.name} non approvato, in sospeso: "
                    f"{'; '.join(blockers)}.",
                    "warning",
                )
                continue
            holder.qualification_status = "APPROVED"
            holder.save()
            approved += 1
        self.message_user(
            request, f"{approved} fornitori approvati.", "success"
        )

    approve_vendors.short_description = _("Approva fornitori selezionati")

    def reject_vendors(self, request, queryset):
        updated = 0
        for holder in self._action_holders(request, queryset):
            if holder.qualification_status == "REJECTED":
                continue
            holder.qualification_status = "REJECTED"
            holder.qualification_date = oggi_locale()
            holder.save()
            updated += 1
        self.message_user(request, f"{updated} fornitori respinti.", "warning")

    reject_vendors.short_description = _("Respingi fornitori selezionati")

    def mark_for_audit(self, request, queryset):
        from datetime import timedelta

        next_audit = timezone.now().date() + timedelta(days=30)
        updated = queryset.update(next_audit_due=next_audit)
        self.message_user(
            request,
            f"{updated} fornitori marcati per audit tra 30 giorni.",
            "info",
        )

    mark_for_audit.short_description = _("Programma audit (30 giorni)")
