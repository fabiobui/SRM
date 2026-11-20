"""Back office: validazione di tecnici, mezzi/dotazioni e dei loro documenti.

I fornitori subappaltatori li caricano dal portale; il back office li valida
o li respinge (con nota). Valgono le sezioni del fornitore: tecnici e mezzi
appartengono alla sezione Sicura (Comune per i fornitori senza società),
quindi li rivede chi può rivedere quella sezione.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from vendor_management_system.core.permissions import BackOfficeRequiredMixin
from vendor_management_system.subcontractors.models import (
    PENDING,
    REJECTED,
    VALIDATED,
    VALIDATION_CHOICES,
    Equipment,
    EquipmentDocument,
    Technician,
    TechnicianDocument,
)
from vendor_management_system.vendors.models import COMMON_SECTION
from vendor_management_system.vendors.sections import (
    SUBCONTRACTOR_SECTION,
    can_review_subcontractor,
)

# kind -> (modello, percorso del fornitore, etichetta)
KINDS = {
    "technician": (Technician, "vendor", "Tecnico"),
    "equipment": (Equipment, "vendor", "Mezzo/dotazione"),
    "technician_document": (
        TechnicianDocument,
        "technician__vendor",
        "Documento tecnico",
    ),
    "equipment_document": (
        EquipmentDocument,
        "equipment__vendor",
        "Documento mezzo",
    ),
}


def reviewable_vendor_filter(user, vendor_path):
    """Fornitori di cui l'utente può validare tecnici e mezzi: quelli senza
    sezioni (Comune) e, per chi è di Sicura, quelli con la sezione Sicura."""
    if user.is_superuser:
        return Q()
    condition = Q(**{f"{vendor_path}__company_sections__isnull": True})
    if getattr(user, "company_id", None) == SUBCONTRACTOR_SECTION:
        condition |= Q(
            **{
                f"{vendor_path}__company_sections__company_id": (
                    SUBCONTRACTOR_SECTION
                )
            }
        )
    return condition


class BoSubcontractorListView(BackOfficeRequiredMixin, TemplateView):
    """Tecnici, mezzi e documenti da validare (default: in attesa)."""

    template_name = "portal/backoffice/subcontractors_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status = self.request.GET.get("status", PENDING)
        if status not in dict(VALIDATION_CHOICES):
            status = PENDING
        user = self.request.user
        groups = []
        for kind, (model, vendor_path, label) in KINDS.items():
            related = [vendor_path]
            if "__" in vendor_path:
                related.append(vendor_path.split("__")[0])
            items = (
                model.objects.filter(validation_status=status)
                .filter(reviewable_vendor_filter(user, vendor_path))
                .select_related(*related)
                .distinct()
            )
            groups.append({"kind": kind, "label": label, "items": items})
        ctx.update(
            {
                "groups": groups,
                "status_filter": status,
                "status_choices": VALIDATION_CHOICES,
                "common_section": COMMON_SECTION,
            }
        )
        return ctx


def _vendor_of(item, vendor_path):
    obj = item
    for part in vendor_path.split("__"):
        obj = getattr(obj, part)
    return obj


class BoSubcontractorReviewView(BackOfficeRequiredMixin, View):
    """POST: valida o respinge un tecnico, un mezzo o un loro documento."""

    http_method_names = ["post"]

    def post(self, request, kind, pk, *args, **kwargs):
        if kind not in KINDS:
            raise PermissionDenied
        model, vendor_path, label = KINDS[kind]
        item = get_object_or_404(model, pk=pk)
        if not can_review_subcontractor(
            request.user, _vendor_of(item, vendor_path)
        ):
            raise PermissionDenied
        action = request.POST.get("action")
        note = (request.POST.get("note") or "").strip()
        if action == "approve":
            item.validation_status = VALIDATED
            item.rejection_note = ""
            messages.success(request, f"{label} validato: {item}.")
        elif action == "reject":
            if not note:
                messages.error(request, "Indica il motivo del respingimento.")
                return redirect("portal:bo-subcontractors")
            item.validation_status = REJECTED
            item.rejection_note = note
            messages.warning(request, f"{label} respinto: {item}.")
        else:
            messages.error(request, "Azione non valida.")
            return redirect("portal:bo-subcontractors")
        item.save()
        return redirect("portal:bo-subcontractors")
