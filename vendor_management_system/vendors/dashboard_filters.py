"""Filtri avanzati della dashboard fornitori, lato server.

Servono all'export Excel, che deve restituire gli stessi fornitori mostrati
in tabella. Dentro uno stesso campo i valori scelti sono in OR; tra campi
diversi vale l'AND (un `.filter()` per campo).
"""

from django.db.models import Q

from vendor_management_system.vendors import competence

# Parametro della querystring -> nome del campo del filtro.
DROPDOWN_PARAMS = {
    "dd_classifications": "classifications",
    "dd_vendor_types": "vendor_types",
    "dd_final_evaluations": "final_evaluations",
    "dd_services": "services",
    "dd_competenze": "competenze",
    "dd_qualifiche": "qualifiche",
    "dd_certifications": "certifications",
    "dd_countries": "countries",
    "dd_regions": "regions",
    "dd_provinces": "provinces",
}


def parse_csv(value):
    """Scompone un parametro CSV della querystring in lista di valori."""
    if not value:
        return []
    return [piece.strip() for piece in value.split(",") if piece.strip()]


def dropdown_selection(params):
    """Valori scelti per ogni filtro a tendina, ignorando quelli vuoti."""
    selection = {}
    for param, field in DROPDOWN_PARAMS.items():
        values = parse_csv(params.get(param))
        if values:
            selection[field] = values
    return selection


def _requirement_filter(queryset, names, **flags):
    # Un solo .filter(): flag e nome devono valere sulla stessa riga di
    # VendorCompetence, non su righe diverse dello stesso fornitore.
    return queryset.filter(
        vendor_competences__competence__name__in=names,
        **{f"vendor_competences__{flag}": True for flag in flags},
    )


def apply_dropdown_filters(queryset, params):
    selection = dropdown_selection(params)
    if not selection:
        return queryset

    if "classifications" in selection:
        names = selection["classifications"]
        queryset = queryset.filter(
            Q(category__name__in=names)
            | Q(additional_categories__name__in=names)
        )
    if "vendor_types" in selection:
        queryset = queryset.filter(vendor_type__in=selection["vendor_types"])
    if "final_evaluations" in selection:
        queryset = queryset.filter(
            vendor_final_evaluation__in=selection["final_evaluations"]
        )
    if "services" in selection:
        queryset = queryset.filter(
            vendor_services__service_type__name__in=selection["services"]
        )
    if "competenze" in selection:
        queryset = _requirement_filter(
            queryset,
            selection["competenze"],
            is_competenza=True,
            has_competence=True,
        )
    if "qualifiche" in selection:
        queryset = _requirement_filter(
            queryset,
            selection["qualifiche"],
            is_qualifica=True,
            has_competence=True,
        )
    if "certifications" in selection:
        queryset = _requirement_filter(
            queryset, selection["certifications"], has_certification=True
        )

    queryset = competence.filter_by_competence(
        queryset,
        countries=selection.get("countries"),
        regions=selection.get("regions"),
        provinces=selection.get("provinces"),
    )
    return queryset.distinct()


def apply_search(queryset, term):
    """Ricerca su codice Embyon, codice interno, ragione sociale, P.IVA e
    codice fiscale."""
    term = (term or "").strip()
    if not term:
        return queryset
    return queryset.filter(
        Q(old_code__icontains=term)
        | Q(vendor_code__icontains=term)
        | Q(name__icontains=term)
        | Q(vat_number__icontains=term)
        | Q(fiscal_code__icontains=term)
    )
