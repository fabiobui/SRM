# Aggiornamenti per vendor_management_system/vendors/admin.py

# Imports (aggiorna le imports esistenti)
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Category, Competence, VendorCompetence, DocumentType, VendorDocument,
    Address, QualificationType, ServiceType, EvaluationCriterion,
    VendorEvaluation, Vendor
)


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


# Competence Admin
@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
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
    fields = ['competence', 'has_competence', 'certification_number', 'issue_date', 'expiry_date', 'verified', 'expiry_status_display']
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


# VendorCompetence Admin
@admin.register(VendorCompetence)
class VendorCompetenceAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'competence', 'has_competence', 'issue_date', 'expiry_date', 'verified', 'expiry_status_badge']
    list_filter = ['has_competence', 'verified', 'competence__competence_category', 'expiry_date']
    search_fields = ['vendor__name', 'competence__name', 'certification_number']
    date_hierarchy = 'expiry_date'
    readonly_fields = ['created_at', 'updated_at', 'is_expired', 'days_to_expiry', 'expiry_status']
    autocomplete_fields = ['vendor', 'competence']
    
    fieldsets = (
        (_('Relazione'), {
            'fields': ('vendor', 'competence', 'has_competence')
        }),
        (_('Dettagli Certificazione'), {
            'fields': ('certification_number', 'certification_body', 'issue_date', 'expiry_date')
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


# DocumentType Admin
@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'document_category', 'is_mandatory', 'requires_renewal', 'default_validity_days', 'is_active']
    list_filter = ['document_category', 'is_mandatory', 'requires_renewal', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['document_category', 'sort_order', 'name']
    list_editable = ['is_active', 'is_mandatory']
    filter_horizontal = ['applicable_categories']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('code', 'name', 'description', 'document_category')
        }),
        (_('Requisiti'), {
            'fields': ('is_mandatory', 'requires_renewal', 'default_validity_days', 'alert_days_before_expiry')
        }),
        (_('Configurazione'), {
            'fields': ('is_active', 'sort_order')
        }),
        (_('Categorie Applicabili'), {
            'fields': ('applicable_categories',)
        }),
        (_('Template e Istruzioni'), {
            'fields': ('template_file', 'instructions')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# VendorDocument Inline
class VendorDocumentInline(admin.TabularInline):
    model = VendorDocument
    extra = 1
    fields = ['document_type', 'status', 'issue_date', 'expiry_date', 'verified', 'expiry_status_display']
    readonly_fields = ['expiry_status_display', 'created_at', 'updated_at']
    autocomplete_fields = ['document_type']
    
    def expiry_status_display(self, obj):
        if obj.pk:
            status = obj.expiry_status
            colors = {
                'EXPIRED': 'red',
                'EXPIRING_SOON': 'orange',
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


# VendorDocument Admin
@admin.register(VendorDocument)
class VendorDocumentAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'document_type', 'status', 'issue_date', 'expiry_date', 'verified', 'expiry_status_badge']
    list_filter = ['status', 'verified', 'document_type__document_category', 'expiry_date']
    search_fields = ['vendor__name', 'document_type__name', 'document_number']
    date_hierarchy = 'expiry_date'
    readonly_fields = ['created_at', 'updated_at', 'is_expired', 'days_to_expiry', 'expiry_status', 'is_valid']
    autocomplete_fields = ['vendor', 'document_type']
    
    fieldsets = (
        (_('Relazione'), {
            'fields': ('vendor', 'document_type')
        }),
        (_('Dettagli Documento'), {
            'fields': ('document_number', 'issue_date', 'expiry_date', 'status')
        }),
        (_('Verifica'), {
            'fields': ('verified', 'verified_by', 'verified_date')
        }),
        (_('File e Note'), {
            'fields': ('document_file', 'notes', 'rejection_reason', 'uploaded_by')
        }),
        (_('Stato Validità'), {
            'fields': ('is_expired', 'days_to_expiry', 'expiry_status', 'is_valid'),
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
            'VALID': 'green',
            'NO_EXPIRY': 'gray'
        }
        return format_html(
            '<span style="background-color: {}; padding: 3px 8px; border-radius: 3px; color: white;">{}</span>',
            colors.get(status, 'black'),
            status
        )
    expiry_status_badge.short_description = _('Stato')
    
    actions = ['mark_as_approved', 'mark_as_verified']
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(status='APPROVED')
        self.message_user(request, f'{updated} documenti approvati.')
    mark_as_approved.short_description = _('Approva documenti selezionati')
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(verified=True, verified_date=timezone.now().date())
        self.message_user(request, f'{updated} documenti verificati.')
    mark_as_verified.short_description = _('Verifica documenti selezionati')


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
        'expiring_documents', 'missing_mandatory_documents'
    ]
    autocomplete_fields = ['address', 'category', 'qualification_type', 'service_type', 'user_account']
    inlines = [VendorCompetenceInline, VendorDocumentInline, VendorEvaluationInline]
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('vendor_code', 'name', 'vendor_type', 'vat_number', 'fiscal_code', 
                      'category', 'risk_level', 'vendor_final_evaluation', 'is_active')
        }),
        (_('Contatti'), {
            'fields': ('email', 'phone', 'reference_contact', 'website', 'address')
        }),
        (_('Stato Contrattuale'), {
            'fields': ('contractual_status', 'contractual_start_date', 'contractual_end_date', 
                      'contractual_terms', 'reference_person')
        }),
        (_('Servizi'), {
            'fields': ('qualification_type', 'service_type', 'cluster_cost', 
                      'begin_experience_date', 'vendor_task_description')
        }),
        (_('Servizi Medici'), {
            'fields': ('mobile_device', 'ambulatory_service', 'laboratory_service', 
                      'licensed_physician_year', 'other_medical_service', 
                      'doctor_registration', 'doctor_cv', 'doctor_cv2'),
            'classes': ('collapse',)
        }),
        (_('Performance'), {
            'fields': ('on_time_delivery_rate', 'quality_rating_avg', 
                      'average_response_time', 'fulfillment_rate')
        }),
        (_('Qualifica e Audit'), {
            'fields': ('qualification_status', 'qualification_score', 'qualification_date', 
                      'qualification_expiry', 'last_audit_date', 'next_audit_due', 
                      'audit_overdue', 'review_notes')
        }),
        (_('Stato Documentazione e Competenze'), {
            'fields': ('is_qualified', 'is_documentation_complete',
                      'active_competences', 'expired_competences', 'expiring_competences',
                      'missing_mandatory_competences', 'valid_documents', 'expired_documents',
                      'expiring_documents', 'missing_mandatory_documents'),
            'classes': ('collapse',)
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
    
    class Media:
        css = {
            'all': ('admin/css/vendor_admin.css',)
        }