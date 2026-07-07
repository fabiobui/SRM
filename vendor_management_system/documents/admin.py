from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from vendor_management_system.documents.models import (
    DocumentType, Document, DocumentSet, VALIDITY_STATUS_META,
)

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
    list_display = ['vendor', 'document_type', 'status', 'validity_badge', 'issue_date', 'expiry_date', 'uploaded_at']
    list_filter = ['status', 'document_type', 'uploaded_at']

    @admin.display(description=_('Stato validità'))
    def validity_badge(self, obj):
        """Stato di validità (NOT VALID se lo stato di lavorazione non è
        'Approvato'), coerente col tab Documenti del fornitore."""
        label, color = VALIDITY_STATUS_META.get(obj.validity_status, (obj.validity_status, 'gray'))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', color, label
        )
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


@admin.register(DocumentSet)
class DocumentSetAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'default_status', 'document_types_count', 'is_active', 'sort_order']
    list_filter = ['is_active', 'category', 'default_status']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'sort_order']
    filter_horizontal = ['document_types']
    ordering = ['sort_order', 'name']

    fieldsets = (
        (_('Informazioni Base'), {
            'fields': ('name', 'description', 'category')
        }),
        (_('Documenti del set'), {
            'fields': ('document_types', 'default_status')
        }),
        (_('Configurazione'), {
            'fields': ('is_active', 'sort_order')
        }),
    )

    def document_types_count(self, obj):
        return obj.document_types.count()
    document_types_count.short_description = _('N. Documenti')
