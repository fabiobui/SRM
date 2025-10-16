from django.contrib import admin
from vendor_management_system.documents.models import DocumentType, Document

@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_required', 'validity_period_days', 'reminder_days_before']
    list_filter = ['is_required']
    search_fields = ['name', 'description']
    ordering = ['name']

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
