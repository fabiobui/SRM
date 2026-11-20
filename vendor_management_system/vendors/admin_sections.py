"""Sezioni del fornitore nell'admin: Comune + una per società.

La scheda fornitore si apre sempre su una sezione (``?sezione=CODICE``):
gli inline mostrano solo gli elementi di quella sezione e assegnano la
sezione a quelli nuovi. Le sezioni di altre società sono in sola lettura.
"""

from django import forms
from django.contrib import admin
from django.contrib.admin.utils import quote
from django.contrib.admin.views.main import ChangeList
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from vendor_management_system.vendors.models import (
    COMMON_SECTION,
    Company,
    VendorCompany,
)
from vendor_management_system.vendors.sections import SECTION_PARAM

FINAL_EVALUATION_COLORS = {
    "POSITIVO": "#28a745",
    "NEGATIVO": "#dc3545",
    "DA VALUTARE": "#6c757d",
}
STATUS_COLORS = {
    "APPROVED": "success",
    "TO_REVIEW": "warning",
    "PENDING": "secondary",
    "REJECTED": "danger",
}


def current_section(request):
    """Company della sezione aperta nella scheda, se presente."""
    return getattr(request, "_section_", None)


def section_editable(request):
    return getattr(request, "_section_editable_", True)


def section_url(vendor_pk, code):
    url = reverse("admin:vendors_vendor_change", args=[quote(vendor_pk)])
    return f"{url}?{SECTION_PARAM}={code}"


def sections_url(vendor_pk):
    return reverse("admin:vendors_vendor_sections", args=[quote(vendor_pk)])


class SectionChangeList(ChangeList):
    """Dal changelist il click sul fornitore apre la scelta della sezione."""

    def url_for_result(self, result):
        return sections_url(result.pk)


class SectionInlineMixin:
    """Inline filtrato sulla sezione aperta. Il campo ``company`` è nel form
    (nascosto, disabilitato, valorizzato con la sezione) così la validazione
    dell'unicità (fornitore, sezione, tipo) avviene nel form."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        section = current_section(request)
        if section is not None:
            qs = qs.filter(company_id=section.code)
        return qs

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if current_section(request) is not None and "company" not in fields:
            fields.append("company")
        return fields

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        section = current_section(request)
        if db_field.name == "company" and section is not None:
            # Campo restituito direttamente: niente wrapper con i link
            # "aggiungi/modifica" dell'admin attorno all'input nascosto.
            return forms.ModelChoiceField(
                queryset=Company.objects.filter(pk=section.pk),
                initial=section.pk,
                disabled=True,
                required=False,
                widget=forms.HiddenInput,
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def _editable(self, request):
        return current_section(request) is None or section_editable(request)

    def has_add_permission(self, request, obj=None):
        return self._editable(request) and super().has_add_permission(
            request, obj
        )

    def has_change_permission(self, request, obj=None):
        return self._editable(request) and super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return self._editable(request) and super().has_delete_permission(
            request, obj
        )


class SectionEditableMixin:
    """Inline modificabile solo se la sezione aperta è dell'utente (per gli
    inline che non dipendono dalla sezione: tecnici, mezzi, attributi)."""

    def has_add_permission(self, request, obj=None):
        return section_editable(request) and super().has_add_permission(
            request, obj
        )

    def has_change_permission(self, request, obj=None):
        return section_editable(request) and super().has_change_permission(
            request, obj
        )

    def has_delete_permission(self, request, obj=None):
        return section_editable(request) and super().has_delete_permission(
            request, obj
        )


class VendorCompanyForm(forms.ModelForm):
    class Meta:
        model = VendorCompany
        fields = (
            "qualification_status",
            "qualification_score",
            "qualification_date",
            "qualification_expiry",
            "last_audit_date",
            "next_audit_due",
            "review_notes",
        )


class VendorCompanyInline(admin.StackedInline):
    """Qualifica e audit della società: visibile solo nella sua sezione."""

    model = VendorCompany
    form = VendorCompanyForm
    extra = 0
    max_num = 1
    can_delete = False
    verbose_name = _("Qualifica e Audit")
    verbose_name_plural = _("Qualifica e Audit")
    fields = (
        "qualification_status",
        "final_evaluation_badge",
        "qualification_blockers_display",
        "embyon_active",
        "accounts_display",
        "qualification_score",
        "qualification_date",
        "qualification_expiry",
        "last_audit_date",
        "next_audit_due",
        "review_notes",
    )
    readonly_fields = (
        "final_evaluation_badge",
        "qualification_blockers_display",
        "embyon_active",
        "accounts_display",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("company")
        section = current_section(request)
        if section is not None:
            qs = qs.filter(company_id=section.code)
        return qs

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return section_editable(request) and super().has_change_permission(
            request, obj
        )

    @admin.display(description=_("Valutazione Finale del Fornitore"))
    def final_evaluation_badge(self, obj):
        value = obj.vendor_final_evaluation or "DA VALUTARE"
        return format_html(
            '<span style="color: {}; font-weight: bold;">&#9679; {}</span>',
            FINAL_EVALUATION_COLORS.get(value, "#6c757d"),
            obj.get_vendor_final_evaluation_display() or value,
        )

    @admin.display(description=_("Elementi che bloccano la qualifica"))
    def qualification_blockers_display(self, obj):
        blockers = obj.qualification_blockers
        if not blockers:
            return _("Nessuno: documenti e requisiti obbligatori in regola")
        return format_html_join(", ", "{}", ((b,) for b in blockers))

    @admin.display(description=_("Conti Embyon"))
    def accounts_display(self, obj):
        accounts = list(obj.accounts.all())
        if not accounts:
            return "-"
        return format_html_join(
            ", ",
            "{} ({})",
            ((a.account_code, a.status or "-") for a in accounts),
        )


def section_badges(vendor):
    """Badge HTML "Società: stato" per changelist e riepiloghi."""
    sections = list(vendor.company_sections.all())
    if not sections:
        return "-"
    return format_html_join(
        " ",
        '<span class="badge badge-{}" title="{}">{}</span>',
        (
            (
                STATUS_COLORS.get(s.qualification_status, "secondary"),
                s.get_qualification_status_display(),
                s.company.label,
            )
            for s in sections
        ),
    )


def user_can_add_section(user, vendor, code):
    """Si può aggiungere la sezione `code`? Solo una società vera, non
    ancora presente, e modificabile dall'utente."""
    from vendor_management_system.vendors.sections import can_edit_section

    if not code or code == COMMON_SECTION:
        return False
    if not Company.objects.real().filter(pk=code, is_active=True).exists():
        return False
    if VendorCompany.objects.filter(vendor=vendor, company_id=code).exists():
        return False
    return can_edit_section(user, code)
