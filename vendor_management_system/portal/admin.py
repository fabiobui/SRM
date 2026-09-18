from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import VendorChangeRequest

# Registrato ma nascosto dal menu (JAZZMIN_SETTINGS["hide_models"] in
# config/settings.py): senza almeno un modello registrato, Django non
# costruisce affatto la sezione app "portal" in /admin, quindi il
# custom_link "Dashboard" (verso /portale/backoffice/dashboard/, la vera
# area di gestione delle richieste di modifica anagrafica) non avrebbe
# nessuna sezione a cui aggrapparsi. Stesso pattern già usato per i
# modelli "vendors" spostati in Services/Competences.


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
    # "vendor__managed_by" filtra per l'utente BO/Admin responsabile del
    # fornitore (Vendor.managed_by), non per chi ha revisionato la
    # richiesta (reviewed_by): permette di isolare le richieste dei
    # fornitori seguiti da un certo referente back-office.
    list_filter = ("status", "created_at", "vendor__managed_by")
    search_fields = (
        "vendor__name",
        "vendor__vendor_code",
        "requested_by__email",
    )
    readonly_fields = ("id", "created_at", "changes_pretty")
    fieldsets = (
        (None, {"fields": ("id", "vendor", "requested_by", "created_at")}),
        ("Modifiche proposte", {"fields": ("changes_pretty",)}),
        (
            "Revisione",
            {
                "fields": (
                    "status",
                    "reviewed_by",
                    "reviewed_at",
                    "review_notes",
                )
            },
        ),
    )

    def status_badge(self, obj):
        colors = {
            "PENDING": "#ffc107",
            "APPROVED": "#198754",
            "REJECTED": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:3px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Stato"

    def changes_pretty(self, obj):
        if not obj.changes:
            return "—"
        rows_args = []
        for field, payload in obj.changes.items():
            old = payload.get("old", "") if isinstance(payload, dict) else ""
            new = (
                payload.get("new", "")
                if isinstance(payload, dict)
                else payload
            )
            rows_args.append((field, old or "—", new or "—"))
        rows_html = format_html_join(
            "",
            "<tr><td><code>{}</code></td>"
            "<td style='color:#888;text-decoration:line-through'>{}</td>"
            "<td><strong>{}</strong></td></tr>",
            rows_args,
        )
        return format_html(
            "<table style='border-collapse:collapse'>"
            "<tr><th>Campo</th><th>Vecchio</th><th>Nuovo</th></tr>{}</table>",
            rows_html,
        )

    changes_pretty.short_description = "Diff"

    def save_model(self, request, obj, form, change):
        """Applica la richiesta quando lo Stato passa a Approvata/Respinta
        da qui, non solo dalla vista BO del portale: `apply_to_vendor()`/
        `reject()` sono gli unici metodi che scrivono su Vendor/
        VendorService e impostano reviewed_by/reviewed_at — un
        salvataggio diretto del model admin li ignorerebbe.
        """
        was_pending = (
            change
            and form.initial.get("status")
            == VendorChangeRequest.STATUS_PENDING
        )
        if was_pending and obj.status == VendorChangeRequest.STATUS_APPROVED:
            obj.status = VendorChangeRequest.STATUS_PENDING
            obj.apply_to_vendor(reviewer=request.user, notes=obj.review_notes)
            return
        if was_pending and obj.status == VendorChangeRequest.STATUS_REJECTED:
            obj.status = VendorChangeRequest.STATUS_PENDING
            obj.reject(reviewer=request.user, notes=obj.review_notes)
            return
        super().save_model(request, obj, form, change)
