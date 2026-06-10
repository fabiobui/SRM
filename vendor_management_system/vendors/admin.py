# Aggiornamenti per vendor_management_system/vendors/admin.py

# Imports (aggiorna le imports esistenti)
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Category, Competence, VendorCompetence, VendorService,
    Address, QualificationType, ServiceType, EvaluationCriterion,
    EvaluationFrequency, VendorEvaluation, Vendor, Contract, Evaluator,
    Country, Region, Province, CompetenceZone, CompetenceZoneRule
)
# Import Document and DocumentType from documents app
from vendor_management_system.documents.models import Document, DocumentType, DocumentSet


# ============================================================================
# Admin Geografici (Nazione, Regione, Provincia)
# ============================================================================

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active', 'sort_order', 'region_count']
    list_filter = ['is_active']
    search_fields = ['code', 'name']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']

    def region_count(self, obj):
        return obj.regions.count()
    region_count.short_description = _('N. Regioni')


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'country', 'is_active', 'sort_order', 'province_count']
    list_filter = ['is_active', 'country']
    search_fields = ['code', 'name']
    ordering = ['country__name', 'sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    autocomplete_fields = ['country']

    def province_count(self, obj):
        return obj.provinces.count()
    province_count.short_description = _('N. Province')


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'region', 'region_country', 'is_active', 'sort_order']
    list_filter = ['is_active', 'region__country', 'region']
    search_fields = ['code', 'name']
    ordering = ['region__country__name', 'region__name', 'sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    autocomplete_fields = ['region']

    def region_country(self, obj):
        return obj.region.country.name
    region_country.short_description = _('Nazione')


# ============================================================================
# Admin Zone di Competenza
# ============================================================================

class CompetenceZoneRuleInline(admin.TabularInline):
    model = CompetenceZoneRule
    extra = 1
    fields = ['rule_type', 'country', 'region', 'province']
    autocomplete_fields = ['country', 'region', 'province']


@admin.register(CompetenceZone)
class CompetenceZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'rules_summary', 'is_active', 'vendor_count', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'rules_summary']
    inlines = [CompetenceZoneRuleInline]

    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('Riepilogo'), {
            'fields': ('rules_summary',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def vendor_count(self, obj):
        return obj.vendors.count()
    vendor_count.short_description = _('N. Fornitori')


@admin.register(CompetenceZoneRule)
class CompetenceZoneRuleAdmin(admin.ModelAdmin):
    list_display = ['zone', 'rule_type', 'geographic_target', 'level']
    list_filter = ['rule_type', 'zone']
    search_fields = ['zone__name', 'country__name', 'region__name', 'province__name']
    autocomplete_fields = ['zone', 'country', 'region', 'province']


# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent', 'is_active', 'sort_order', 'vendor_count', 'color_badge']
    list_filter = ['is_active', 'requires_certification', 'default_risk_level', 'parent']
    search_fields = ['code', 'name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    readonly_fields = ['created_at', 'updated_at', 'full_name', 'level', 'vendor_count', 'total_vendor_count']
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('code', 'name', 'description', 'parent')
        }),
        (_('Classificazione'), {
            'fields': ('is_active', 'sort_order', 'color_code')
        }),
        (_('Regole di Business'), {
            'fields': ('requires_certification', 'default_risk_level')
        }),
        (_('Statistiche'), {
            'fields': ('full_name', 'level', 'vendor_count', 'total_vendor_count'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_badge(self, obj):
        if obj.color_code:
            return format_html(
                '<span style="background-color: {}; padding: 5px 10px; border-radius: 3px; color: white;">{}</span>',
                obj.color_code,
                obj.color_code
            )
        return '-'
    color_badge.short_description = _('Colore')


# Competence Resource for import/export
class CompetenceResource(resources.ModelResource):
    class Meta:
        model = Competence
        fields = ('id', 'code', 'name', 'description', 'competence_category',
                  'requires_certification', 'requires_renewal', 'renewal_period_months',
                  'is_mandatory', 'is_active', 'sort_order')
        export_order = fields
        import_id_fields = ['code']


# Competence Admin
@admin.register(Competence)
class CompetenceAdmin(ImportExportModelAdmin):
    resource_class = CompetenceResource
    list_display = ['code', 'name', 'competence_category', 'is_mandatory', 'requires_certification', 'requires_renewal', 'is_active']
    list_filter = ['competence_category', 'is_mandatory', 'requires_certification', 'requires_renewal', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['competence_category', 'sort_order', 'name']
    list_editable = ['is_active', 'is_mandatory']
    filter_horizontal = ['applicable_categories']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('code', 'name', 'description', 'competence_category')
        }),
        (_('Requisiti'), {
            'fields': ('requires_certification', 'requires_renewal', 'renewal_period_months')
        }),
        (_('Configurazione'), {
            'fields': ('is_mandatory', 'is_active', 'sort_order')
        }),
        (_('Categorie Applicabili'), {
            'fields': ('applicable_categories',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# VendorCompetence Inline
class VendorCompetenceInline(admin.TabularInline):
    model = VendorCompetence
    extra = 1
    fields = ['competence', 'is_competenza', 'is_qualifica', 'is_iscrizione_albo', 'has_certification', 'certification_number', 'issue_date', 'expiry_date', 'verified', 'expiry_status_display']
    readonly_fields = ['expiry_status_display', 'created_at', 'updated_at']
    autocomplete_fields = ['competence']
    
    def expiry_status_display(self, obj):
        if obj.pk:
            status = obj.expiry_status
            colors = {
                'EXPIRED': 'red',
                'EXPIRING_SOON': 'orange',
                'EXPIRING': 'yellow',
                'VALID': 'green',
                'NO_EXPIRY': 'gray'
            }
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                colors.get(status, 'black'),
                status
            )
        return '-'
    expiry_status_display.short_description = _('Stato Scadenza')


# VendorService Inline
class VendorServiceInline(admin.TabularInline):
    model = VendorService
    extra = 1
    fields = ['service_type', 'is_primary', 'hourly_rate', 'start_date', 'end_date', 'contract', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "service_type":
            # Mostra solo i servizi specifici (con parent), non le categorie principali
            kwargs["queryset"] = ServiceType.objects.filter(is_active=True, parent__isnull=False).order_by('parent__name', 'name')
        if db_field.name == "contract":
            # Mostra solo i contratti del vendor corrente
            vendor_id = None
            if hasattr(request, '_obj_') and request._obj_:
                vendor_id = request._obj_.vendor_code
            if vendor_id:
                kwargs["queryset"] = Contract.objects.filter(vendor__vendor_code=vendor_id)
            else:
                kwargs["queryset"] = Contract.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# VendorService Admin
@admin.register(VendorService)
class VendorServiceAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'service_type', 'is_primary', 'hourly_rate', 'start_date', 'end_date', 'is_active_display']
    list_filter = ['is_primary', 'service_type__parent', 'start_date', 'end_date']
    search_fields = ['vendor__name', 'service_type__name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at', 'is_active']
    autocomplete_fields = ['vendor', 'service_type']
    
    fieldsets = (
        (_('Relazione'), {
            'fields': ('vendor', 'service_type', 'is_primary')
        }),
        (_('Tariffa'), {
            'fields': ('hourly_rate',)
        }),
        (_('Periodo Erogazione'), {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        (_('Note'), {
            'fields': ('notes',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green; font-weight: bold;">✓ Attivo</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Terminato</span>')
    is_active_display.short_description = _('Stato')


# VendorCompetence Admin
@admin.register(VendorCompetence)
class VendorCompetenceAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'competence', 'is_competenza', 'is_qualifica', 'is_iscrizione_albo', 'has_competence', 'has_certification', 'issue_date', 'expiry_date', 'verified', 'expiry_status_badge']
    list_filter = ['is_competenza', 'is_qualifica', 'is_iscrizione_albo', 'has_competence', 'has_certification', 'verified', 'competence__competence_category', 'expiry_date']
    search_fields = ['vendor__name', 'competence__name', 'certification_number']
    date_hierarchy = 'expiry_date'
    readonly_fields = ['created_at', 'updated_at', 'is_expired', 'days_to_expiry', 'expiry_status']
    autocomplete_fields = ['vendor', 'competence']
    
    fieldsets = (
        (_('Relazione'), {
            'fields': ('vendor', 'competence', 'has_competence')
        }),
        (_('Tipo Requisito'), {
            'fields': ('is_competenza', 'is_qualifica', 'is_iscrizione_albo')
        }),
        (_('Dettagli Certificazione'), {
            'fields': ('has_certification', 'certification_number', 'certification_body', 'issue_date', 'expiry_date')
        }),
        (_('Verifica'), {
            'fields': ('verified', 'verified_by', 'verified_date')
        }),
        (_('Documentazione'), {
            'fields': ('document_file', 'notes')
        }),
        (_('Stato Scadenza'), {
            'fields': ('is_expired', 'days_to_expiry', 'expiry_status'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def expiry_status_badge(self, obj):
        status = obj.expiry_status
        colors = {
            'EXPIRED': 'red',
            'EXPIRING_SOON': 'orange',
            'EXPIRING': 'yellow',
            'VALID': 'green',
            'NO_EXPIRY': 'gray'
        }
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: white;">{}</span>',
            colors.get(status, 'black'),
            status
        )
    expiry_status_badge.short_description = _('Stato')


# Document Inline
class DocumentInline(admin.TabularInline):
    model = Document
    extra = 1
    fields = ['document_type', 'status', 'issue_date', 'expiry_date', 'expiry_status_display']
    readonly_fields = ['expiry_status_display', 'uploaded_at']
    autocomplete_fields = ['document_type']
    
    def expiry_status_display(self, obj):
        if obj.pk:
            if obj.is_expired:
                status = 'EXPIRED'
                color = 'red'
            elif obj.is_expiring_soon:
                status = 'EXPIRING_SOON'
                color = 'orange'
            else:
                status = 'VALID'
                color = 'green'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                status
            )
        return '-'
    expiry_status_display.short_description = _('Stato Scadenza')


# Address Admin
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['short_address', 'city', 'postal_code', 'country', 'address_type', 'is_active']
    list_filter = ['address_type', 'is_active', 'country', 'city']
    search_fields = ['street_address', 'city', 'postal_code', 'country']
    readonly_fields = ['created_at', 'updated_at', 'full_address']
    
    fieldsets = (
        (_('Indirizzo'), {
            'fields': ('street_address', 'street_address_2', 'city', 'state_province', 'region', 'postal_code', 'country')
        }),
        (_('Coordinate Geografiche'), {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        (_('Informazioni Aggiuntive'), {
            'fields': ('address_type', 'is_active', 'full_address')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# QualificationType Admin
@admin.register(QualificationType)
class QualificationTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'level', 'is_active', 'sort_order']
    list_filter = ['is_active', 'level']
    search_fields = ['code', 'name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']


# ServiceType Admin
@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'parent', 'is_active', 'sort_order', 'is_category']
    list_filter = ['is_active', 'parent']
    search_fields = ['code', 'name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    
    def is_category(self, obj):
        return obj.is_category
    is_category.boolean = True
    is_category.short_description = _('È Categoria')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Personalizza il campo parent per mostrare solo le categorie"""
        if db_field.name == "parent":
            # Mostra solo i ServiceType che sono categorie (parent=None)
            kwargs["queryset"] = ServiceType.objects.filter(parent__isnull=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# EvaluationCriterion Admin
@admin.register(EvaluationCriterion)
class EvaluationCriterionAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['category', 'code']
    list_editable = ['is_active']


# EvaluationFrequency Admin
@admin.register(EvaluationFrequency)
class EvaluationFrequencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'months', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    ordering = ['months']


# Evaluator Admin
@admin.register(Evaluator)
class EvaluatorAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'email', 'role', 'department', 'is_active']
    list_filter = ['is_active', 'department']
    search_fields = ['first_name', 'last_name', 'email', 'role', 'department']
    ordering = ['last_name', 'first_name']


# VendorEvaluation Inline
class VendorEvaluationInline(admin.TabularInline):
    model = VendorEvaluation
    extra = 1
    fields = ['criterion', 'score', 'evaluator', 'evaluation_frequency', 'notes', 'evaluated_at']
    readonly_fields = ['evaluated_at']
    autocomplete_fields = ['criterion', 'evaluator', 'evaluation_frequency']
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'notes':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(attrs={'rows': 2, 'cols': 40, 'style': 'width: 300px;'})
        if db_field.name == 'evaluation_frequency':
            try:
                kwargs['initial'] = EvaluationFrequency.objects.get(months=12).pk
            except EvaluationFrequency.DoesNotExist:
                pass
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    def expiry_status_display(self, obj):
        if obj.pk:
            status = obj.expiry_status
            colors = {
                'EXPIRED': 'red',
                'EXPIRING_SOON': 'orange',
                'EXPIRING': 'yellow',
                'VALID': 'green',
                'NO_EXPIRY': 'gray'
            }
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                colors.get(status, 'black'),
                status
            )
        return '-'
    expiry_status_display.short_description = _('Stato Scadenza')


# VendorEvaluation Admin
@admin.register(VendorEvaluation)
class VendorEvaluationAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'criterion', 'score', 'score_display', 'evaluator', 'evaluated_at']
    list_filter = ['score', 'criterion__category', 'evaluator', 'evaluated_at']
    search_fields = ['vendor__name', 'criterion__name', 'notes', 'evaluator__last_name', 'evaluator__first_name']
    date_hierarchy = 'evaluated_at'
    autocomplete_fields = ['vendor', 'criterion', 'evaluator']
    
    def score_display(self, obj):
        return obj.get_score_display()
    score_display.short_description = _('Valutazione')


# Contract Inline
class ContractInline(admin.StackedInline):
    model = Contract
    extra = 0
    fields = [
        'contract_number', 'title', 'contract_type', 'reference_person',
        'status', 'start_date', 'end_date', 'amount', 'notes'
    ]


# Contract Admin (standalone)
@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ['contract_number', 'title', 'vendor', 'contract_type', 'status', 'start_date', 'end_date', 'amount']
    list_filter = ['status', 'contract_type', 'start_date']
    search_fields = ['contract_number', 'title', 'vendor__name', 'vendor__vendor_code', 'reference_person']
    autocomplete_fields = ['vendor']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {
            'fields': ('contract_number', 'title', 'vendor', 'contract_type', 'reference_person', 'status')
        }),
        (_('Date e Importo'), {
            'fields': ('start_date', 'end_date', 'amount')
        }),
        (_('Note e Metadati'), {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Vendor Admin (Enhanced)
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        'old_code', 'name', 'category', 'qualification_status', 'vendor_final_evaluation',
        'embyon_active', 'qualification_score'
    ]
    list_filter = [
        'qualification_status', 'is_active', 'category',
        'vendor_type', 'vendor_final_evaluation', 'embyon_active'
    ]
    search_fields = ['vendor_code', 'old_code', 'name', 'vat_number', 'fiscal_code', 'email']
    readonly_fields = [
        'vendor_code', 'is_qualified', 'audit_overdue', 'is_documentation_complete',
        'active_competences', 'expired_competences', 'expiring_competences',
        'missing_mandatory_competences', 'valid_documents', 'expired_documents',
        'expiring_documents', 'missing_mandatory_documents', 'primary_service', 'active_services'
    ]
    autocomplete_fields = ['address', 'category', 'qualification_type', 'managed_by', 'competence_zones']
    inlines = [VendorServiceInline, VendorCompetenceInline, DocumentInline, ContractInline, VendorEvaluationInline]

    def get_form(self, request, obj=None, **kwargs):
        # Salva l'oggetto corrente per usarlo negli inline
        request._obj_ = obj
        return super().get_form(request, obj, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'document-sets/',
                self.admin_site.admin_view(self.document_sets_view),
                name='vendors_vendor_document_sets',
            ),
        ]
        return custom + urls

    def document_sets_view(self, request):
        """Restituisce i set documentali attivi (filtrati per la Classificazione
        del fornitore, se nota) con i relativi tipi di documento. Usato dal
        dropdown 'Set Documentale' nel tab Documenti."""
        qs = DocumentSet.objects.filter(is_active=True).prefetch_related('document_types')

        category_id = None
        vendor_id = request.GET.get('vendor')
        if vendor_id:
            vendor = Vendor.objects.filter(pk=vendor_id).only('category').first()
            if vendor:
                category_id = vendor.category_id

        # Con classificazione nota: set universali (category nullo) + set della classificazione.
        # Senza classificazione (o in creazione): tutti i set attivi.
        if category_id:
            qs = qs.filter(Q(category__isnull=True) | Q(category_id=category_id))

        sets = [
            {
                'id': s.pk,
                'name': s.name,
                'default_status': s.default_status,
                'document_types': [
                    {'id': dt.pk, 'text': str(dt)} for dt in s.document_types.all()
                ],
            }
            for s in qs
        ]
        return JsonResponse({'sets': sets})

    class Media:
        js = (
            'admin/js/vendor_form_guard.js',
            'admin/js/document_set_applier.js',
        )
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': (
                'vendor_code', 'old_code', 'managed_by', 'name', 'vendor_type',
                'vat_number', 'fiscal_code', 'qualification_type', 'category',
                'competence_zones', 'vendor_final_evaluation', 'risk_level',
                'embyon_active', 'is_active'
            )
        }),
        (_('Contatti'), {
            'fields': ('email', 'phone', 'reference_contact', 'website', 'address', 'contact_details')
        }),
        (_('Servizi Medici'), {
            'fields': (
                'vendor_medical_service', 'mobile_device', 'ambulatory_service',
                'laboratory_service', 'laboratory_independent',
                'licensed_physician_year', 'date_of_establishment',
                'other_medical_service', 'doctor_registration',
                'doctor_cv', 'doctor_cv2'
            ),
            'classes': ('collapse',)
        }),
# remove this section if not needed      
#        (_('Performance'), {
#            'fields': (
#                'on_time_delivery_rate', 'quality_rating_avg',
#                'average_response_time', 'fulfillment_rate'
#            )
#        }),
        (_('Qualifica e Audit'), {
            'fields': (
                'qualification_status', 'qualification_score', 'qualification_date',
                'qualification_expiry', 'last_audit_date', 'next_audit_due',
                'is_qualified', 'audit_overdue', 'review_notes'
            )
        }),
    )
        
    def is_qualified_display(self, obj):
        if obj.is_qualified:
            return format_html('<span style="color: green; font-weight: bold;">✓ Qualificato</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Non Qualificato</span>')
    is_qualified_display.short_description = _('Qualificato')
    
    actions = ['approve_vendors', 'reject_vendors', 'mark_for_audit']
    
    def approve_vendors(self, request, queryset):
        updated = queryset.update(qualification_status='APPROVED')
        self.message_user(request, f'{updated} fornitori approvati.', 'success')
    approve_vendors.short_description = _('Approva fornitori selezionati')
    
    def reject_vendors(self, request, queryset):
        updated = queryset.update(qualification_status='REJECTED')
        self.message_user(request, f'{updated} fornitori respinti.', 'warning')
    reject_vendors.short_description = _('Respingi fornitori selezionati')
    
    def mark_for_audit(self, request, queryset):
        from datetime import timedelta
        next_audit = timezone.now().date() + timedelta(days=30)
        updated = queryset.update(next_audit_due=next_audit)
        self.message_user(request, f'{updated} fornitori marcati per audit tra 30 giorni.', 'info')
    mark_for_audit.short_description = _('Programma audit (30 giorni)')

