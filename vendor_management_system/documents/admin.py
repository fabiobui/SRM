from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from vendor_management_system.documents.models import DocumentType, Document

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'document_category', 'is_required', 'requires_renewal', 'validity_period_days', 'is_active']
    list_filter = ['document_category', 'is_required', 'requires_renewal', 'is_active']
    search_fields = ['code', 'name', 'description']
    ordering = ['document_category', 'sort_order', 'name']
    list_editable = ['is_active', 'is_required']
    filter_horizontal = ['applicable_categories']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('code', 'name', 'description', 'document_category')
        }),
        (_('Requisiti'), {
            'fields': ('is_required', 'requires_renewal', 'validity_period_days', 'reminder_days_before')
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

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'document_type', 'status', 'issue_date', 'expiry_date', 'uploaded_at']
    list_filter = ['status', 'document_type', 'uploaded_at']
    search_fields = ['vendor__name', 'document_type__name']
    ordering = ['-uploaded_at']
    readonly_fields = ['id', 'uploaded_at']
    
    fieldsets = (
        (None, {
            'fields': ('vendor', 'document_type', 'file', 'status')
        }),
        ('Dates', {
            'fields': ('issue_date', 'expiry_date', 'uploaded_at')
        }),
        ('Review', {
            'fields': ('reviewed_by', 'reviewed_at', 'notes')
        }),
    )
