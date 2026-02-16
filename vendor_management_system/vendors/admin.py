# Aggiornamenti per vendor_management_system/vendors/admin.py

# Imports (aggiorna le imports esistenti)
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Category, Competence, VendorCompetence, VendorService,
    Address, QualificationType, ServiceType, EvaluationCriterion,
    VendorEvaluation, Vendor
)
# Import Document and DocumentType from documents app
from vendor_management_system.documents.models import Document, DocumentType


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
        fields = ('id', 'requirement_type', 'code', 'name', 'description', 'competence_category',
                  'requires_certification', 'requires_renewal', 'renewal_period_months',
                  'is_mandatory', 'is_active', 'sort_order')
        export_order = fields
        import_id_fields = ['code']


# Competence Admin
@admin.register(Competence)
class CompetenceAdmin(ImportExportModelAdmin):
    resource_class = CompetenceResource
    list_display = ['code', 'name', 'competence_category', 'is_mandatory', 'requires_certification', 'requires_renewal', 'is_active']
    list_filter = ['requirement_type', 'competence_category', 'is_mandatory', 'requires_certification', 'requires_renewal', 'is_active']
    search_fields = ['code', 'requirement_type', 'name', 'description']
    ordering = ['competence_category', 'sort_order', 'name']
    list_editable = ['is_active', 'is_mandatory']
    filter_horizontal = ['applicable_categories']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('requirement_type', 'code', 'name', 'description', 'competence_category')
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
    fields = ['competence', 'requirement_type_display', 'has_certification', 'certification_number', 'issue_date', 'expiry_date', 'verified', 'expiry_status_display']
    readonly_fields = ['requirement_type_display', 'expiry_status_display', 'created_at', 'updated_at']
    autocomplete_fields = ['competence']
    
    def requirement_type_display(self, obj):
        if obj.pk and obj.competence:
            req_type = obj.competence.requirement_type
            labels = {
                'competenza': 'Competenza',
                'qualifica': 'Qualifica',
                'iscrizione_albo': 'Iscr. Albo'
            }
            return labels.get(req_type, req_type or '-')
        return '-'
    requirement_type_display.short_description = _('Tipo Requisito')
    
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
    fields = ['service_type', 'is_primary', 'start_date', 'end_date', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "service_type":
            # Mostra solo i servizi specifici (con parent), non le categorie principali
            kwargs["queryset"] = ServiceType.objects.filter(is_active=True, parent__isnull=False).order_by('parent__name', 'name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# VendorService Admin
@admin.register(VendorService)
class VendorServiceAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'service_type', 'is_primary', 'start_date', 'end_date', 'is_active_display']
    list_filter = ['is_primary', 'service_type__parent', 'start_date', 'end_date']
    search_fields = ['vendor__name', 'service_type__name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at', 'is_active']
    autocomplete_fields = ['vendor', 'service_type']
    
    fieldsets = (
        (_('Relazione'), {
            'fields': ('vendor', 'service_type', 'is_primary')
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
    list_display = ['vendor', 'competence', 'has_competence', 'has_certification', 'issue_date', 'expiry_date', 'verified', 'expiry_status_badge']
    list_filter = ['has_competence', 'has_certification', 'verified', 'competence__competence_category', 'expiry_date']
    search_fields = ['vendor__name', 'competence__name', 'certification_number']
    date_hierarchy = 'expiry_date'
    readonly_fields = ['created_at', 'updated_at', 'is_expired', 'days_to_expiry', 'expiry_status']
    autocomplete_fields = ['vendor', 'competence']
    
    fieldsets = (
        (_('Relazione'), {
            'fields': ('vendor', 'competence', 'has_competence')
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


# VendorEvaluation Inline
class VendorEvaluationInline(admin.TabularInline):
    model = VendorEvaluation
    extra = 1
    fields = ['criterion', 'score', 'notes', 'evaluated_at']
    readonly_fields = ['evaluated_at']
    autocomplete_fields = ['criterion']
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'notes':
            kwargs['widget'] = admin.widgets.AdminTextareaWidget(attrs={'rows': 2, 'cols': 40, 'style': 'width: 300px;'})
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
    list_display = ['vendor', 'criterion', 'score', 'score_display', 'evaluated_at']
    list_filter = ['score', 'criterion__category', 'evaluated_at']
    search_fields = ['vendor__name', 'criterion__name', 'notes']
    date_hierarchy = 'evaluated_at'
    autocomplete_fields = ['vendor', 'criterion']
    
    def score_display(self, obj):
        return obj.get_score_display()
    score_display.short_description = _('Valutazione')


# Vendor Admin (Enhanced)
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        'vendor_code', 'name', 'category', 'qualification_status', 'risk_level',
        'is_qualified_display', 'is_active', 'qualification_score'
    ]
    list_filter = [
        'qualification_status', 'risk_level', 'is_active', 'category',
        'vendor_type', 'contractual_status', 'vendor_final_evaluation'
    ]
    search_fields = ['vendor_code', 'name', 'vat_number', 'fiscal_code', 'email']
    readonly_fields = [
        'vendor_code', 'is_qualified', 'audit_overdue', 'is_documentation_complete',
        'active_competences', 'expired_competences', 'expiring_competences',
        'missing_mandatory_competences', 'valid_documents', 'expired_documents',
        'expiring_documents', 'missing_mandatory_documents', 'primary_service', 'active_services'
    ]
    autocomplete_fields = ['address', 'category', 'qualification_type', 'user_account']
    inlines = [VendorServiceInline, VendorCompetenceInline, DocumentInline, VendorEvaluationInline]
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': (
                'vendor_code', 'old_code', 'name', 'vendor_type',
                'vat_number', 'fiscal_code', 'qualification_type', 'category', 'risk_level',
                'vendor_final_evaluation', 'is_active'
            )
        }),
        (_('Contatti'), {
            'fields': ('email', 'phone', 'reference_contact', 'website', 'address', 'contact_details')
        }),
        (_('Stato Contrattuale'), {
            'fields': (
                'contractual_status', 'contractual_start_date', 'contractual_end_date',
                'contractual_terms', 'reference_person'
            )
        }),
        (_('Gestione/Altro'), {
            'fields': ('competences_zone', 'vendor_management_update','vendor_task_description', 'is_ico_consultant','cluster_corso', 'albo_zucchetti')
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
        (_('Performance'), {
            'fields': (
                'on_time_delivery_rate', 'quality_rating_avg',
                'average_response_time', 'fulfillment_rate'
            )
        }),
        (_('Qualifica e Audit'), {
            'fields': (
                'qualification_status', 'qualification_score', 'qualification_date',
                'qualification_expiry', 'last_audit_date', 'next_audit_due',
                'is_qualified', 'audit_overdue', 'review_notes'
            )
        }),
        (_('Account Utente'), {
            'fields': ('user_account',),
            'classes': ('collapse',)
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

