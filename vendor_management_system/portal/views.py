"""View del portale fornitore (area /portale/) e gestione BO delle richieste anagrafica.

Convenzioni:
- Tutte le view "fornitore" filtrano sempre i queryset su `request.user.vendor`.
- Per le DetailView/UpdateView dei singoli oggetti del fornitore si usa
  `VendorOwnerRequiredMixin` per impedire IDOR.
- Le view BO ricavano i permessi da `BackOfficeRequiredMixin`.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
)

from vendor_management_system.core.permissions import (
    BackOfficeRequiredMixin,
    VendorRequiredMixin,
)
from vendor_management_system.documents.models import Document

from .forms import (
    DocumentUploadForm,
    VendorChangeReviewForm,
    VendorProfileChangeForm,
)
from .models import VendorChangeRequest


# --- helper -----------------------------------------------------------------

def _vendor_documents_qs(vendor):
    """Queryset documenti del vendor, con select_related per evitare N+1.

    I `Document` sono pre-creati dal back-office tramite il `DocumentInline` di
    VendorAdmin. L'elenco di "documenti che il fornitore deve caricare" è
    dunque l'insieme dei `Document` con stato `PENDING`. Il fornitore non sceglie
    i tipi: lavora solo sui record già esistenti per il proprio vendor.
    """
    return Document.objects.filter(vendor=vendor).select_related("document_type")


# --- area fornitore ---------------------------------------------------------

class PortalDashboardView(VendorRequiredMixin, TemplateView):
    """Home del portale fornitore: KPI sintetici e link rapidi alle aree."""

    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor
        documents = _vendor_documents_qs(vendor)

        # "Da caricare": Document con status PENDING (pre-creati dal BO, file vuoto).
        to_upload_count = documents.filter(status="PENDING").count()

        expiring_count = sum(
            1
            for d in documents.filter(status__in=["APPROVED", "UPLOADED"])
            if d.is_expiring_soon and not d.is_expired
        )
        expired_count = documents.filter(status="EXPIRED").count()
        pending_review_count = documents.filter(status="UPLOADED").count()
        approved_count = documents.filter(status="APPROVED").count()
        rejected_count = documents.filter(status="REJECTED").count()

        pending_change_requests = VendorChangeRequest.objects.filter(
            vendor=vendor, status=VendorChangeRequest.STATUS_PENDING
        ).count()

        ctx.update(
            {
                "vendor": vendor,
                "to_upload_count": to_upload_count,
                "expiring_count": expiring_count,
                "expired_count": expired_count,
                "pending_review_count": pending_review_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "pending_change_requests": pending_change_requests,
                "total_documents": documents.count(),
            }
        )
        return ctx


class MyDocumentsView(VendorRequiredMixin, ListView):
    """Lista dei documenti pre-definiti dal BO per il proprio fornitore.

    Visualizza tutti i `Document` collegati al vendor; il template mette in
    cima i `PENDING` (= "da caricare"). Niente "tipi mancanti" perché qui non
    si creano nuovi documenti: il fornitore lavora solo su quelli già
    pre-creati dal back-office (`DocumentInline` in VendorAdmin).
    """

    template_name = "portal/documents/list.html"
    context_object_name = "documents"

    def get_queryset(self):
        # I PENDING (da caricare) appaiono per primi; poi UPLOADED, REJECTED,
        # APPROVED, EXPIRED nell'ordine alfabetico Postgres-friendly del campo.
        return _vendor_documents_qs(self.request.user.vendor).order_by(
            "status", "document_type__name"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor
        documents = self.get_queryset()

        pending_docs = [d for d in documents if d.status == "PENDING"]
        submitted_docs = [d for d in documents if d.status != "PENDING"]
        expiring_docs = [
            d
            for d in submitted_docs
            if d.status in ("APPROVED", "UPLOADED")
            and d.is_expiring_soon
            and not d.is_expired
        ]

        ctx.update(
            {
                "vendor": vendor,
                "pending_docs": pending_docs,
                "submitted_docs": submitted_docs,
                "expiring_docs": expiring_docs,
            }
        )
        return ctx


class MyDocumentUploadView(VendorRequiredMixin, View):
    """POST upload/aggiornamento di un singolo Document già esistente.

    L'URL contiene `pk` del Document. La view filtra su `vendor=request.user.vendor`
    per evitare IDOR: un fornitore non può caricare file su documenti di altri
    fornitori cambiando l'ID nell'URL.

    Stato risultante: il documento passa sempre a `UPLOADED`, anche se prima
    era REJECTED o EXPIRED, perché il fornitore ha riproposto il file. Eventuali
    revisioni precedenti vengono resettate (`reviewed_by`/`reviewed_at` a None).
    """

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        document = get_object_or_404(
            Document, pk=pk, vendor=request.user.vendor
        )
        form = DocumentUploadForm(request.POST, request.FILES, instance=document)
        if not form.is_valid():
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}")
            return redirect("portal:my-document-detail", pk=document.pk)

        document = form.save(commit=False)
        document.status = "UPLOADED"
        document.reviewed_by = None
        document.reviewed_at = None
        document.save()

        messages.success(
            request,
            f"Documento '{document.document_type.name}' caricato correttamente.",
        )
        return redirect("portal:my-document-detail", pk=document.pk)


class MyDocumentDetailView(VendorRequiredMixin, DetailView):
    """Dettaglio di un singolo documento del proprio vendor.

    Filtro queryset su `vendor=request.user.vendor` per evitare IDOR: un fornitore
    non può accedere a documenti di altri fornitori cambiando l'ID nell'URL.
    """

    template_name = "portal/documents/detail.html"
    context_object_name = "document"

    def get_queryset(self):
        return _vendor_documents_qs(self.request.user.vendor)


# --- anagrafica & qualifica (Fase 2) ---------------------------------------

class MyVendorProfileView(VendorRequiredMixin, TemplateView):
    """Visualizzazione anagrafica del proprio fornitore (sola lettura)."""

    template_name = "portal/profile/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor
        pending = VendorChangeRequest.objects.filter(
            vendor=vendor, status=VendorChangeRequest.STATUS_PENDING
        ).first()
        ctx.update({"vendor": vendor, "pending_change_request": pending})
        return ctx


class VendorChangeRequestCreateView(VendorRequiredMixin, View):
    """Form modifica anagrafica → genera VendorChangeRequest in stato PENDING.

    Vincolo: una sola richiesta pendente alla volta per ciascun fornitore.
    """

    template_name = "portal/profile/change_form.html"

    def _has_pending(self, vendor):
        return VendorChangeRequest.objects.filter(
            vendor=vendor, status=VendorChangeRequest.STATUS_PENDING
        ).exists()

    def get(self, request, *args, **kwargs):
        vendor = request.user.vendor
        if self._has_pending(vendor):
            messages.warning(
                request,
                "Hai già una richiesta di modifica in attesa di approvazione. "
                "Attendi l'esito prima di inviarne un'altra.",
            )
            return redirect("portal:my-profile")
        form = VendorProfileChangeForm(instance=vendor)
        from django.shortcuts import render

        return render(request, self.template_name, {"form": form, "vendor": vendor})

    def post(self, request, *args, **kwargs):
        vendor = request.user.vendor
        if self._has_pending(vendor):
            messages.warning(request, "Hai già una richiesta in attesa.")
            return redirect("portal:my-profile")

        form = VendorProfileChangeForm(request.POST, instance=vendor)
        if not form.is_valid():
            from django.shortcuts import render

            return render(
                request, self.template_name, {"form": form, "vendor": vendor}
            )

        diff = form.compute_diff()
        if not diff:
            messages.info(request, "Nessuna modifica rilevata.")
            return redirect("portal:my-profile")

        VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=request.user,
            changes=diff,
        )
        messages.success(
            request,
            "Richiesta di modifica inviata. Il back-office la valuterà a breve.",
        )
        return redirect("portal:my-change-requests")


class VendorChangeRequestListView(VendorRequiredMixin, ListView):
    """Storico richieste di modifica anagrafica del proprio fornitore."""

    template_name = "portal/profile/change_requests_list.html"
    context_object_name = "requests"
    paginate_by = 20

    def get_queryset(self):
        return VendorChangeRequest.objects.filter(
            vendor=self.request.user.vendor
        ).select_related("reviewed_by", "requested_by")


class MyQualificationView(VendorRequiredMixin, TemplateView):
    """Stato qualifica del fornitore (sola lettura)."""

    template_name = "portal/qualification/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vendor"] = self.request.user.vendor
        return ctx


# --- area BO (gestione richieste anagrafica) -------------------------------

class BoChangeRequestListView(BackOfficeRequiredMixin, ListView):
    """Lista richieste anagrafica per il back-office, default solo PENDING."""

    template_name = "portal/backoffice/change_requests_list.html"
    context_object_name = "requests"
    paginate_by = 25

    def get_queryset(self):
        qs = VendorChangeRequest.objects.select_related(
            "vendor", "requested_by", "reviewed_by"
        )
        status = self.request.GET.get("status", VendorChangeRequest.STATUS_PENDING)
        if status in dict(VendorChangeRequest.STATUS_CHOICES):
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"] = self.request.GET.get(
            "status", VendorChangeRequest.STATUS_PENDING
        )
        ctx["status_choices"] = VendorChangeRequest.STATUS_CHOICES
        return ctx


class BoChangeRequestDetailView(BackOfficeRequiredMixin, DetailView):
    """Dettaglio richiesta + form approvazione/rifiuto."""

    template_name = "portal/backoffice/change_request_detail.html"
    context_object_name = "change_request"
    model = VendorChangeRequest

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = VendorChangeReviewForm()
        return ctx


class BoChangeRequestReviewView(BackOfficeRequiredMixin, View):
    """POST: approva o rifiuta una richiesta. Action e note arrivano dal form."""

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        change_request = get_object_or_404(VendorChangeRequest, pk=pk)
        if not change_request.is_pending:
            messages.warning(request, "La richiesta non è più in stato 'in attesa'.")
            return redirect("portal:bo-change-request-detail", pk=pk)

        form = VendorChangeReviewForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Form non valido.")
            return redirect("portal:bo-change-request-detail", pk=pk)

        action = form.cleaned_data["action"]
        notes = form.cleaned_data.get("review_notes", "")

        if action == "approve":
            change_request.apply_to_vendor(reviewer=request.user, notes=notes)
            messages.success(
                request,
                f"Modifiche applicate al fornitore {change_request.vendor.name}.",
            )
        else:
            change_request.reject(reviewer=request.user, notes=notes)
            messages.warning(
                request,
                f"Richiesta rifiutata per {change_request.vendor.name}.",
            )
        return redirect("portal:bo-change-requests")


# --- retro-compatibilità ----------------------------------------------------

class LegacyPortalRedirectView(View):
    """Redirect 301 da /documents/portal/ alla nuova dashboard /portale/."""

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse("portal:dashboard"))
