"""Viste della dashboard fornitori che non servono ai grafici: scheda del
fornitore in sola lettura e creazione di un fornitore prospetto.

Accessibili anche al Buyer, che non entra in /admin/ (vedi
`core.permissions.dashboard_api_required`).
"""

from django.core.exceptions import FieldDoesNotExist
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from vendor_management_system.core.permissions import dashboard_api_required
from vendor_management_system.vendors import competence
from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.prospect import (
    ProspectVendorForm,
    create_prospect,
)

EMPTY = "—"

BASE_FIELDS = (
    "vendor_code",
    "old_code",
    "embyon_company",
    "name",
    "vendor_type",
    "vat_number",
    "fiscal_code",
    "qualification_type",
    "category",
    "first_supply_date",
    "risk_level",
    "embyon_active",
    "is_active",
)
CONTACT_FIELDS = (
    "email",
    "phone",
    "reference_contact",
    "pec",
    "website",
    "address",
    "contact_details",
)
QUALIFICATION_FIELDS = (
    "qualification_status",
    "vendor_final_evaluation",
    "qualification_score",
    "qualification_date",
    "qualification_expiry",
    "last_audit_date",
    "next_audit_due",
    "review_notes",
)


def _display(instance, name):
    """Valore di un campo come testo da mostrare, senza mai esporre file."""
    field = instance._meta.get_field(name)
    value = getattr(instance, name)
    if value in (None, ""):
        return EMPTY
    if field.choices:
        return getattr(instance, f"get_{name}_display")()
    if isinstance(value, bool):
        return "Sì" if value else "No"
    if hasattr(value, "tzinfo"):
        return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _label(instance, name):
    return str(instance._meta.get_field(name).verbose_name)


def _rows(instance, names):
    rows = []
    for name in names:
        try:
            rows.append((_label(instance, name), _display(instance, name)))
        except FieldDoesNotExist:
            continue
    return rows


def _table(headers, rows):
    return {"headers": headers, "rows": rows}


def _text(value):
    return EMPTY if value in (None, "") else str(value)


def _yes_no(value):
    return "Sì" if value else "No"


def _date(value):
    return value.strftime("%d/%m/%Y") if value else EMPTY


def _operational_rows(vendor):
    """Attributi operativi valorizzati: si omettono quelli vuoti o falsi,
    che sono la gran parte e renderebbero la scheda illeggibile."""
    attrs = getattr(vendor, "operational_attributes", None)
    if attrs is None:
        return []
    rows = []
    for field in attrs._meta.concrete_fields:
        if field.primary_key or field.name == "vendor":
            continue
        value = getattr(attrs, field.name)
        if value in (None, "", False):
            continue
        rows.append((str(field.verbose_name), _display(attrs, field.name)))
    return rows


def _base_rows(vendor):
    rows = _rows(vendor, BASE_FIELDS)
    managers = [vendor.managed_by] + list(vendor.secondary_managers.all())
    rows.append(
        (
            "Utenti gestione fornitore",
            ", ".join(u.email for u in managers if u) or EMPTY,
        )
    )
    rows.append(
        (
            "Classificazioni aggiuntive",
            ", ".join(c.name for c in vendor.additional_categories.all())
            or EMPTY,
        )
    )
    rows.append(
        ("Zone di competenza", competence.competence_summary(vendor) or EMPTY)
    )
    return rows


def vendor_detail_sections(vendor):
    """Sezioni della scheda fornitore, nello stesso ordine dell'admin."""
    services = vendor.vendor_services.select_related(
        "service_type", "service_type__parent"
    )
    requirements = vendor.vendor_competences.select_related("competence")
    documents = vendor.documents.select_related("document_type")
    contracts = vendor.contracts.all()
    evaluations = vendor.evaluations.select_related(
        "criterion", "evaluator", "evaluation_frequency"
    )

    return [
        {"title": "Informazioni base", "rows": _base_rows(vendor)},
        {"title": "Contatti", "rows": _rows(vendor, CONTACT_FIELDS)},
        {
            "title": "Servizi erogati",
            "table": _table(
                ["Servizio", "Categoria", "Principale", "Dal", "Al", "Note"],
                [
                    [
                        s.service_type.name,
                        _text(
                            s.service_type.parent
                            and s.service_type.parent.name
                        ),
                        _yes_no(s.is_primary),
                        _date(s.start_date),
                        _date(s.end_date),
                        _text(s.notes),
                    ]
                    for s in services
                ],
            ),
        },
        {
            "title": "Abilitazioni e requisiti professionali",
            "table": _table(
                [
                    "Requisito",
                    "Competenza",
                    "Qualifica",
                    "Albo",
                    "Certificazione",
                    "N. certificazione",
                    "Emissione",
                    "Scadenza",
                ],
                [
                    [
                        r.competence.name,
                        _yes_no(r.is_competenza),
                        _yes_no(r.is_qualifica),
                        _yes_no(r.is_iscrizione_albo),
                        _yes_no(r.has_certification),
                        _text(r.certification_number),
                        _date(r.issue_date),
                        _date(r.expiry_date),
                    ]
                    for r in requirements
                ],
            ),
        },
        {
            "title": "Documenti contrattuali",
            "table": _table(
                ["Documento", "Stato", "Emissione", "Scadenza"],
                [
                    [
                        str(d.document_type),
                        d.get_status_display(),
                        _date(d.issue_date),
                        _date(d.expiry_date),
                    ]
                    for d in documents
                ],
            ),
        },
        {
            "title": "Contratti",
            "table": _table(
                [
                    "Numero",
                    "Titolo",
                    "Tipo",
                    "Stato",
                    "Dal",
                    "Al",
                    "Importo",
                ],
                [
                    [
                        c.contract_number,
                        _text(c.title),
                        c.get_contract_type_display(),
                        c.get_status_display(),
                        _date(c.start_date),
                        _date(c.end_date),
                        _text(c.amount),
                    ]
                    for c in contracts
                ],
            ),
        },
        {
            "title": "Qualifica e audit",
            "rows": _rows(vendor, QUALIFICATION_FIELDS),
        },
        {
            "title": "Valutazioni",
            "table": _table(
                ["Criterio", "Punteggio", "Valutatore", "Note"],
                [
                    [
                        str(e.criterion),
                        e.get_score_display(),
                        _text(e.evaluator),
                        _text(e.notes),
                    ]
                    for e in evaluations
                ],
            ),
        },
        {
            "title": "Attributi operativi",
            "rows": _operational_rows(vendor),
        },
    ]


@dashboard_api_required
def vendor_detail_view(request, vendor_code):
    """Frammento HTML con tutte le sezioni del fornitore, in sola lettura."""
    vendor = get_object_or_404(
        Vendor.objects.select_related(
            "category", "address", "managed_by", "qualification_type"
        ).prefetch_related("secondary_managers", "additional_categories"),
        pk=vendor_code,
    )
    return render(
        request,
        "vendors/_vendor_readonly_detail.html",
        {"vendor": vendor, "sections": vendor_detail_sections(vendor)},
    )


@require_POST
@dashboard_api_required
def prospect_create_view(request):
    """Crea un fornitore prospetto con l'accesso al portale."""
    form = ProspectVendorForm(request.POST)
    if not form.is_valid():
        return JsonResponse(
            {
                "errors": {
                    field: [str(e) for e in errors]
                    for field, errors in form.errors.items()
                }
            },
            status=400,
        )

    result = create_prospect(form.cleaned_data, request.user, request)
    return JsonResponse(
        {
            "vendor_code": result.vendor.pk,
            "name": result.vendor.name,
            "invite_sent_to": result.invite_sent_to,
            "warnings": result.warnings,
        },
        status=201,
    )
