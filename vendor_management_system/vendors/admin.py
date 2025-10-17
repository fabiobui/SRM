# Imports
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from vendor_management_system.vendors.models import Vendor


# Register Vendor model in admin
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        "vendor_code",
        "name",
        "email",
        "phone",
        "category",
        "qualification_status_display",
        "risk_level_display",
        "is_qualified_display",
        "audit_overdue_display"
    ]
    
    list_filter = [
        "qualification_status",
        "risk_level",
        "category",
        "country",
        "qualification_date",
        "next_audit_due",
    ]
    
    search_fields = [
        "name",
        "vendor_code",
        "email",
        "vat_number",
        "fiscal_code",
        "reference_contact",
    ]
    
    ordering = ["name"]
    
    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": (
                    "vendor_code",
                    "name",
                    "contact_details",
                    "address",
                )
            },
        ),
        (
            _("Contact & Legal Information"),
            {
                "fields": (
                    "vat_number",
                    "fiscal_code",
                    "email",
                    "reference_contact",
                    "phone",
                    "website",
                )
            },
        ),
        (
            _("Business Classification"),
            {
                "fields": (
                    "category",
                    "country",
                    "risk_level",
                )
            },
        ),
        (
            _("Qualification & Compliance"),
            {
                "fields": (
                    "qualification_status",
                    "qualification_score",
                    "qualification_date",
                    "qualification_expiry",
                    "iso_certifications",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Performance Metrics"),
            {
                "fields": (
                    "on_time_delivery_rate",
                    "quality_rating_avg",
                    "average_response_time",
                    "fulfillment_rate",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit & Management"),
            {
                "fields": (
                    "last_audit_date",
                    "next_audit_due",
                    "review_notes",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    
    readonly_fields = [
        "vendor_code",
    ]
    
    # Custom display methods
    def qualification_status_display(self, obj):
        colors = {
            'PENDING': '#ffc107',  # warning/yellow
            'APPROVED': '#28a745',  # success/green
            'REJECTED': '#dc3545',  # danger/red
        }
        color = colors.get(obj.qualification_status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_qualification_status_display()
        )
    qualification_status_display.short_description = _('Qualification Status')
    
    def risk_level_display(self, obj):
        colors = {
            'LOW': '#28a745',    # green
            'MEDIUM': '#ffc107', # yellow
            'HIGH': '#dc3545',   # red
        }
        color = colors.get(obj.risk_level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_risk_level_display()
        )
    risk_level_display.short_description = _('Risk Level')
    
    def is_qualified_display(self, obj):
        if obj.is_qualified:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ {}</span>',
                _('Qualified')
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">✗ {}</span>',
                _('Not Qualified')
            )
    is_qualified_display.short_description = _('Qualified')
    
    def audit_overdue_display(self, obj):
        if obj.audit_overdue:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ {}</span>',
                _('Overdue')
            )
        elif obj.next_audit_due:
            return format_html(
                '<span style="color: #28a745;">✓ {}</span>',
                _('Scheduled')
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">- {}</span>',
                _('Not Scheduled')
            )
    audit_overdue_display.short_description = _('Audit Status')
    
    # Add custom actions
    actions = ['mark_as_approved', 'mark_as_pending', 'mark_as_rejected']
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(qualification_status='APPROVED')
        self.message_user(
            request,
            f'{updated} vendor(s) marked as approved.'
        )
    mark_as_approved.short_description = _('Mark selected vendors as approved')
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(qualification_status='PENDING')
        self.message_user(
            request,
            f'{updated} vendor(s) marked as pending.'
        )
    mark_as_pending.short_description = _('Mark selected vendors as pending')
    
    def mark_as_rejected(self, request, queryset):
        updated = queryset.update(qualification_status='REJECTED')
        self.message_user(
            request,
            f'{updated} vendor(s) marked as rejected.'
        )
    mark_as_rejected.short_description = _('Mark selected vendors as rejected')
    
    # Custom save method for admin
    def save_model(self, request, obj, form, change):
        if not change:  # This is a new object
            # Auto-set qualification date if status is approved and no date is set
            if obj.qualification_status == 'APPROVED' and not obj.qualification_date:
                from django.utils import timezone
                obj.qualification_date = timezone.now().date()
                
        super().save_model(request, obj, form, change)