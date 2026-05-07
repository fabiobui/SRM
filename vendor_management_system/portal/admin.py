from django.contrib import admin
from django.utils.html import format_html

from .models import VendorChangeRequest


@admin.register(VendorChangeRequest)
class VendorChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "vendor",
        "status_badge",
        "requested_by",
        "created_at",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("vendor__name", "vendor__vendor_code", "requested_by__email")
    readonly_fields = ("id", "created_at", "changes_pretty")
    fieldsets = (
        (None, {"fields": ("id", "vendor", "requested_by", "status", "created_at")}),
        ("Modifiche proposte", {"fields": ("changes_pretty",)}),
        ("Revisione", {"fields": ("reviewed_by", "reviewed_at", "review_notes")}),
    )

    def status_badge(self, obj):
        colors = {"PENDING": "#ffc107", "APPROVED": "#198754", "REJECTED": "#dc3545"}
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Stato"

    def changes_pretty(self, obj):
        if not obj.changes:
            return "—"
        rows = []
        for field, payload in obj.changes.items():
            old = payload.get("old", "") if isinstance(payload, dict) else ""
            new = payload.get("new", "") if isinstance(payload, dict) else payload
            rows.append(
                f"<tr><td><code>{field}</code></td>"
                f"<td style='color:#888;text-decoration:line-through'>{old or '—'}</td>"
                f"<td><strong>{new or '—'}</strong></td></tr>"
            )
        return format_html(
            "<table style='border-collapse:collapse'>"
            "<tr><th>Campo</th><th>Vecchio</th><th>Nuovo</th></tr>{}</table>",
            "".join(rows),
        )

    changes_pretty.short_description = "Diff"
