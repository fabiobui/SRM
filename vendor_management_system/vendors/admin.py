# Aggiornamenti per vendor_management_system/vendors/admin.py

# Imports (aggiorna le imports esistenti)
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.db.models import Count

from vendor_management_system.vendors.models import Vendor, Address, Category


# Inline per subcategories
class SubcategoryInline(admin.TabularInline):
    model = Category
    fk_name = 'parent'
    extra = 0
    fields = ['code', 'name', 'is_active', 'sort_order', 'default_risk_level']
    readonly_fields = []


# Register Category model in admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "code",
        "name",
        "parent_category_display",
        "level_display",
        "vendor_count_display",
        "color_display",
        "requires_certification",
        "default_risk_level_display",
        "is_active",
        "sort_order",
    ]
    
    list_filter = [
        "is_active",
        "requires_certification",
        "default_risk_level",
        "parent",
        "created_at",
    ]
    
    search_fields = [
        "code",
        "name",
        "description",
        "parent__name",
    ]
    
    ordering = ["sort_order", "name"]
    
    fieldsets = (
        (
            _("Informazioni principali"),
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "parent",
                )
            },
        ),
        (
            _("Configurazione"),
            {
                "fields": (
                    ("is_active", "sort_order"),
                    ("requires_certification", "default_risk_level"),
                    "color_code",
                )
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]
    
    inlines = [SubcategoryInline]
    
    # Custom queryset per ottimizzare le query
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('parent').annotate(
            vendor_count=Count('vendors', distinct=True)
        )
    
    # Custom display methods
    def parent_category_display(self, obj):
        if obj.parent:
            return format_html(
                '<span style="color: #007cba;">{}</span>',
                obj.parent.name
            )
        else:
            return format_html(
                '<span style="color: #6c757d; font-style: italic;">Root</span>'
            )
    parent_category_display.short_description = _('Parent Category')
    
    def level_display(self, obj):
        level = obj.level
        indent = "━" * level if level > 0 else ""
        return format_html(
            '<span style="color: #6c757d;">{}{}</span>',
            indent,
            f"Level {level}"
        )
    level_display.short_description = _('Level')
    
    def vendor_count_display(self, obj):
        count = getattr(obj, 'vendor_count', 0)
        if count > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{}</span>',
                count
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">0</span>'
            )
    vendor_count_display.short_description = _('Vendors')
    vendor_count_display.admin_order_field = 'vendor_count'
    
    def color_display(self, obj):
        if obj.color_code:
            return format_html(
                '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; border-radius: 3px; display: inline-block;"></div> {}',
                obj.color_code,
                obj.color_code
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">Nessun colore</span>'
            )
    color_display.short_description = _('Color')
    
    def default_risk_level_display(self, obj):
        colors = {
            'LOW': '#28a745',    # green
            'MEDIUM': '#ffc107', # yellow
            'HIGH': '#dc3545',   # red
        }
        color = colors.get(obj.default_risk_level, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_default_risk_level_display()
        )
    default_risk_level_display.short_description = _('Default Risk')
    
    # Custom actions
    actions = ['activate_categories', 'deactivate_categories', 'reset_sort_order']
    
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} categoria/e attivata/e.'
        )
    activate_categories.short_description = _('Activate selected categories')
    
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} categoria/e disattivata/e.'
        )
    deactivate_categories.short_description = _('Deactivate selected categories')
    
    def reset_sort_order(self, request, queryset):
        for i, category in enumerate(queryset.order_by('name'), start=1):
            category.sort_order = i * 10
            category.save()
        self.message_user(
            request,
            f'Ordine di visualizzazione reimpostato per {queryset.count()} categoria/e.'
        )
    reset_sort_order.short_description = _('Reset sort order')


# Register Address model in admin
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        "short_address_display",
        "city",
        "postal_code",
        "country",
        "address_type",
        "is_active",
        "vendors_count",
        "created_at",
    ]
    
    list_filter = [
        "address_type",
        "is_active",
        "country",
        "city",
        "created_at",
    ]
    
    search_fields = [
        "street_address",
        "street_address_2",
        "city",
        "postal_code",
        "country",
        "state_province",
    ]
    
    ordering = ["-created_at"]
    
    fieldsets = (
        (
            _("Informazioni principali"),
            {
                "fields": (
                    "street_address",
                    "street_address_2",
                    ("city", "state_province"),
                    ("postal_code", "country"),
                )
            },
        ),
        (
            _("Classificazione"),
            {
                "fields": (
                    "address_type",
                    "is_active",
                )
            },
        ),
        (
            _("Coordinate geografiche"),
            {
                "fields": (
                    ("latitude", "longitude"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Note e dettagli"),
            {
                "fields": (
                    "notes",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]
    
    # Custom display methods
    def short_address_display(self, obj):
        return obj.short_address
    short_address_display.short_description = _('Indirizzo')
    
    def vendors_count(self, obj):
        count = obj.vendors.count()
        if count > 0:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} vendor(s)</span>',
                count
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">Nessun vendor</span>'
            )
    vendors_count.short_description = _('Vendors collegati')


# VendorAdmin CORRETTO (senza AddressInline)
@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = [
        "vendor_code",
        "name",
        "email",
        "phone",
        "category_display",
        "address_display",
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
        "address__country",  # Filtro per paese dell'indirizzo
        "address__city",     # Filtro per città dell'indirizzo
    ]
    
    search_fields = [
        "name",
        "vendor_code",
        "email",
        "vat_number",
        "fiscal_code",
        "reference_contact",
        "address__street_address",
        "address__city",
        "address__postal_code",
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
                    "address",  # Campo address come ForeignKey
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
    
    # RIMOSSE le inlines perché Address non ha ForeignKey verso Vendor
    # inlines = [AddressInline]  # RIMOSSO
    
    actions = [
        'mark_as_approved', 
        'mark_as_pending', 
        'mark_as_rejected',
        'update_risk_from_category',
        'assign_category'
    ]
    
    def update_risk_from_category(self, request, queryset):
        updated = 0
        for vendor in queryset:
            if vendor.category:
                vendor.risk_level = vendor.category.default_risk_level
                vendor.save()
                updated += 1
        self.message_user(
            request,
            f'{updated} vendor(s) updated with category default risk level.'
        )
    update_risk_from_category.short_description = _('Update risk level from category default')

    def assign_category(self, request, queryset):
        # Questa action permetterà di assegnare una categoria ai vendor selezionati
        # Implementazione da fare se necessaria
        pass
    assign_category.short_description = _('Assign category to selected vendors')

    def category_display(self, obj):
        if obj.category:
            color_style = ""
            if obj.category.color_code:
                color_style = f"border-left: 4px solid {obj.category.color_code}; padding-left: 8px;"
            
            certification_badge = ""
            if obj.category.requires_certification:
                certification_badge = '<span style="color: #ffc107; font-size: 12px;"> 🏅</span>'
            
            category_text = obj.category.full_name if obj.category.parent else obj.category.name
            
            return format_html(
                '<span style="{}" title="{}">{}{}</span>',
                color_style,
                f"Codice: {obj.category.code}\nDescrizione: {obj.category.description or 'N/A'}\nRichiede certificazione: {'Sì' if obj.category.requires_certification else 'No'}",
                category_text,
                certification_badge
            )
        else:
            return format_html(
                '<span style="color: #dc3545; font-style: italic;">⚠ Nessuna categoria</span>'
            )
    category_display.short_description = _('Category')
    category_display.admin_order_field = 'category__name'
    
    def address_display(self, obj):
        if obj.address:
            return format_html(
                '<span title="{}">{}</span>',
                obj.address.full_address,
                obj.address.short_address
            )
        else:
            return format_html(
                '<span style="color: #dc3545;">⚠ Nessun indirizzo</span>'
            )
    address_display.short_description = _('Indirizzo')
    
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
            
            # Auto-set risk level from category if not specified
            if not obj.risk_level and obj.category:
                obj.risk_level = obj.category.default_risk_level
                
        super().save_model(request, obj, form, change)