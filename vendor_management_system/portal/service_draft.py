"""Bozza delle richieste sui servizi del fornitore.

Aggiunte, modifiche ed eliminazioni non creano subito una
`VendorChangeRequest`: finiscono in una bozza in sessione, visibile in
anteprima su /portale/servizi/. "Conferma richieste" le invia tutte insieme,
con lo stesso `batch_id`, così il back-office le approva in un colpo solo.
"""

import uuid
from datetime import date

from django.db import transaction

from vendor_management_system.vendors.models import VendorService

from .forms import available_service_types_for_vendor
from .models import VendorChangeRequest

SESSION_KEY = "service_draft"
OP_ADD = "add"
OP_EDIT = "edit"
OP_DELETE = "delete"

FIELD_LABELS = {
    "is_primary": "Servizio principale",
    "start_date": "Data inizio",
    "end_date": "Data fine",
    "notes": "Note",
}

REQUEST_TYPES = {
    OP_ADD: VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
    OP_EDIT: VendorChangeRequest.REQUEST_TYPE_EDIT,
    OP_DELETE: VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE,
}


def get_draft(request):
    return list(request.session.get(SESSION_KEY, []))


def _store(request, operations):
    request.session[SESSION_KEY] = operations
    request.session.modified = True


def clear(request):
    request.session.pop(SESSION_KEY, None)


def remove_operation(request, index):
    operations = get_draft(request)
    if 0 <= index < len(operations):
        operations.pop(index)
        _store(request, operations)


def staged_add_type_ids(request):
    return [o["service_type"] for o in get_draft(request) if o["op"] == OP_ADD]


def stage_add(request, service_type_ids):
    operations = get_draft(request)
    present = set(staged_add_type_ids(request))
    for pk in service_type_ids:
        if str(pk) not in present:
            operations.append({"op": OP_ADD, "service_type": str(pk)})
    _store(request, operations)


def _stage_service_operation(request, entry):
    # Una sola operazione per servizio: l'ultima scelta sostituisce la prima
    operations = [
        o for o in get_draft(request) if o.get("service") != entry["service"]
    ]
    operations.append(entry)
    _store(request, operations)


def stage_edit(request, service, changes):
    _stage_service_operation(
        request,
        {"op": OP_EDIT, "service": str(service.pk), "changes": changes},
    )


def stage_delete(request, service):
    _stage_service_operation(
        request, {"op": OP_DELETE, "service": str(service.pk)}
    )


def _display(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Sì" if value else "No"
    try:
        return date.fromisoformat(value).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(value)


def build_operations(vendor, draft):
    """Risolve la bozza rispetto allo stato attuale del DB.

    Scarta le voci non più valide (servizio sparito o già con una richiesta
    in attesa, servizio del catalogo non più proponibile): vale sia per
    l'anteprima sia per l'invio. Ritorna le operazioni pronte, ciascuna con
    `index` (posizione nella bozza), `op`, `service`, `service_type`,
    `changes` e `details` per la visualizzazione.
    """
    services = {
        str(s.pk): s
        for s in VendorService.objects.filter(vendor=vendor).select_related(
            "service_type"
        )
    }
    locked = {
        str(pk)
        for pk in VendorChangeRequest.objects.filter(
            vendor_service__vendor=vendor,
            status=VendorChangeRequest.STATUS_PENDING,
        ).values_list("vendor_service_id", flat=True)
    }
    available = {
        str(t.pk): t for t in available_service_types_for_vendor(vendor)
    }

    operations = []
    for index, entry in enumerate(draft):
        op = entry.get("op")
        if op == OP_ADD:
            service_type = available.get(entry.get("service_type"))
            if service_type is None:
                continue
            operations.append(
                {
                    "index": index,
                    "op": op,
                    "service": None,
                    "service_type": service_type,
                    "name": service_type.name,
                    "changes": {},
                    "details": [],
                }
            )
            continue
        service = services.get(entry.get("service"))
        if op not in (OP_EDIT, OP_DELETE) or service is None:
            continue
        if entry["service"] in locked:
            continue
        if op == OP_DELETE:
            changes = {
                "service_type": {"old": str(service.service_type), "new": None}
            }
            details = []
        else:
            changes = entry.get("changes") or {}
            details = [
                {
                    "label": FIELD_LABELS.get(field, field),
                    "old": _display(payload.get("old")),
                    "new": _display(payload.get("new")),
                }
                for field, payload in changes.items()
            ]
        operations.append(
            {
                "index": index,
                "op": op,
                "service": service,
                "service_type": None,
                "name": service.service_type.name,
                "changes": changes,
                "details": details,
            }
        )
    return operations


def commit_draft(request, vendor, user):
    """Crea una `VendorChangeRequest` per ogni operazione valida della
    bozza, tutte con lo stesso `batch_id`. Ritorna quante ne ha create."""
    operations = build_operations(vendor, get_draft(request))
    if operations:
        batch_id = uuid.uuid4()
        with transaction.atomic():
            for operation in operations:
                VendorChangeRequest.objects.create(
                    vendor=vendor,
                    vendor_service=operation["service"],
                    service_type=operation["service_type"],
                    request_type=REQUEST_TYPES[operation["op"]],
                    requested_by=user,
                    changes=operation["changes"],
                    batch_id=batch_id,
                )
    clear(request)
    return len(operations)
