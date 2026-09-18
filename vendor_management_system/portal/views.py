"""View del portale fornitore (area /portale/) e gestione BO delle
richieste anagrafica/servizi.

Convenzioni:
- Tutte le view "fornitore" filtrano sempre i queryset su
  `request.user.vendor`.
- Per le DetailView/UpdateView dei singoli oggetti del fornitore si usa
  `VendorOwnerRequiredMixin` per impedire IDOR.
- Le view BO ricavano i permessi da `BackOfficeRequiredMixin`.
"""

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    DetailView,
    ListView,
    TemplateView,
)

from vendor_management_system.core.permissions import (
    BackOfficeRequiredMixin,
    VendorRequiredMixin,
)
from vendor_management_system.documents.models import Document
from vendor_management_system.vendors.models import (
    Vendor,
    VendorCompetence,
    VendorOperationalAttributes,
    VendorService,
)

from .forms import (
    CompetenceDocumentUploadForm,
    DocumentUploadForm,
    VendorChangeReviewForm,
    VendorOperationalAttributesForm,
    VendorProfileChangeForm,
    VendorServiceChangeForm,
)
from .models import VendorChangeRequest

# --- helper -----------------------------------------------------------------


def _vendor_documents_qs(vendor):
    """Queryset documenti del vendor, con select_related per evitare N+1.

    I `Document` sono pre-creati dal back-office tramite il
    `DocumentInline` di VendorAdmin. L'elenco di "documenti che il
    fornitore deve caricare" è dunque l'insieme dei `Document` con stato
    `PENDING`. Il fornitore non sceglie i tipi: lavora solo sui record già
    esistenti per il proprio vendor.
    """
    return Document.objects.filter(vendor=vendor).select_related(
        "document_type"
    )


# --- area fornitore ---------------------------------------------------------


class PortalDashboardView(VendorRequiredMixin, TemplateView):
    """Home del portale fornitore: KPI sintetici e link rapidi alle aree."""

    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor
        documents = _vendor_documents_qs(vendor)

        # "Da caricare": Document con status PENDING (pre-creati dal BO,
        # file vuoto).
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

        # Solo le richieste anagrafica (non quelle sui servizi): il badge
        # KPI vive sotto la card "Anagrafica" del dashboard.
        pending_change_requests = VendorChangeRequest.objects.filter(
            vendor=vendor,
            vendor_service__isnull=True,
            status=VendorChangeRequest.STATUS_PENDING,
        ).count()

        # Requisiti professionali assegnati senza documento caricato.
        requirements = _vendor_competences_qs(vendor)
        requirements_to_upload_count = requirements.filter(
            Q(document_file="") | Q(document_file__isnull=True)
        ).count()

        # Metriche divise per tipologia (AIDEV-44): prima le 4 card KPI in
        # cima mostravano solo i Document sotto un'etichetta generica, che
        # nascondeva i VendorCompetence (requisiti) nello stesso stato — es.
        # "in revisione" mostrava 2 anche quando c'erano altri 2 requisiti in
        # revisione. Ora ogni tipologia ha il proprio conteggio.
        doc_stats = {
            "to_upload": to_upload_count,
            "in_review": pending_review_count,
            "approved": approved_count,
            "expired": expired_count,
        }
        req_stats = {
            "to_upload": requirements_to_upload_count,
            "in_review": requirements.exclude(
                Q(document_file="") | Q(document_file__isnull=True)
            )
            .filter(verified=False)
            .count(),
            "approved": requirements.filter(verified=True).count(),
            "expired": requirements.filter(
                expiry_date__isnull=False,
                expiry_date__lt=timezone.now().date(),
            ).count(),
        }

        def _change_request_stats(vendor_service_isnull):
            counts = dict(
                VendorChangeRequest.objects.filter(
                    vendor=vendor, vendor_service__isnull=vendor_service_isnull
                )
                .values("status")
                .annotate(total=Count("id"))
                .values_list("status", "total")
            )
            return {
                "pending": counts.get(VendorChangeRequest.STATUS_PENDING, 0),
                "approved": counts.get(VendorChangeRequest.STATUS_APPROVED, 0),
                "rejected": counts.get(VendorChangeRequest.STATUS_REJECTED, 0),
            }

        anagrafica_stats = _change_request_stats(vendor_service_isnull=True)
        servizi_stats = _change_request_stats(vendor_service_isnull=False)

        ctx.update(
            {
                "vendor": vendor,
                "to_upload_count": to_upload_count,
                "requirements_to_upload_count": requirements_to_upload_count,
                "total_requirements": requirements.count(),
                "expiring_count": expiring_count,
                "expired_count": expired_count,
                "pending_review_count": pending_review_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "pending_change_requests": pending_change_requests,
                "total_documents": documents.count(),
                "doc_stats": doc_stats,
                "req_stats": req_stats,
                "anagrafica_stats": anagrafica_stats,
                "servizi_stats": servizi_stats,
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

    L'URL contiene `pk` del Document. La view filtra su
    `vendor=request.user.vendor` per evitare IDOR: un fornitore non può
    caricare file su documenti di altri fornitori cambiando l'ID nell'URL.

    Stato risultante: il documento passa sempre a `UPLOADED`, anche se
    prima era REJECTED o EXPIRED, perché il fornitore ha riproposto il
    file. Eventuali revisioni precedenti vengono resettate
    (`reviewed_by`/`reviewed_at` a None).
    """

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        document = get_object_or_404(
            Document, pk=pk, vendor=request.user.vendor
        )
        form = DocumentUploadForm(
            request.POST, request.FILES, instance=document
        )
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
            f"Documento '{document.document_type.name}' "
            "caricato correttamente.",
        )
        return redirect("portal:my-document-detail", pk=document.pk)


class MyDocumentDetailView(VendorRequiredMixin, DetailView):
    """Dettaglio di un singolo documento del proprio vendor.

    Filtro queryset su `vendor=request.user.vendor` per evitare IDOR: un
    fornitore non può accedere a documenti di altri fornitori cambiando
    l'ID nell'URL.
    """

    template_name = "portal/documents/detail.html"
    context_object_name = "document"

    def get_queryset(self):
        return _vendor_documents_qs(self.request.user.vendor)


# --- requisiti professionali ------------------------------------------------


def _vendor_competences_qs(vendor):
    """Queryset dei requisiti professionali assegnati al vendor.

    Le `VendorCompetence` sono pre-create dal back-office tramite il
    `VendorCompetenceInline` di VendorAdmin. Il fornitore non sceglie i
    requisiti: carica solo il file (`document_file`) sui record già esistenti
    per il proprio vendor.
    """
    return VendorCompetence.objects.filter(vendor=vendor).select_related(
        "competence"
    )


class MyRequirementsView(VendorRequiredMixin, ListView):
    """Lista dei requisiti professionali assegnati al proprio fornitore.

    Mostra tutti i `VendorCompetence` collegati al vendor; il template mette in
    cima quelli senza file (= "da caricare"). Niente creazione di nuovi
    requisiti: il fornitore lavora solo su quelli già assegnati dal back-office
    (`VendorCompetenceInline` in VendorAdmin).
    """

    template_name = "portal/requirements/list.html"
    context_object_name = "requirements"

    def get_queryset(self):
        return _vendor_competences_qs(self.request.user.vendor).order_by(
            "competence__name"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor
        requirements = list(self.get_queryset())

        pending = [r for r in requirements if not r.document_file]
        submitted = [r for r in requirements if r.document_file]
        expiring = [
            r
            for r in submitted
            if r.expiry_status in ("EXPIRING_SOON", "EXPIRING")
        ]

        ctx.update(
            {
                "vendor": vendor,
                "pending_reqs": pending,
                "submitted_reqs": submitted,
                "expiring_reqs": expiring,
            }
        )
        return ctx


class MyRequirementUploadView(VendorRequiredMixin, View):
    """POST upload/aggiornamento del documento di un requisito già assegnato.

    L'URL contiene `pk` della VendorCompetence. La view filtra su
    `vendor=request.user.vendor` per evitare IDOR: un fornitore non può
    caricare file su requisiti di altri fornitori cambiando l'ID nell'URL.

    Caricando un nuovo file la verifica precedente viene resettata
    (`verified=False`), perché il documento va rivalutato dal back-office.
    """

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        requirement = get_object_or_404(
            VendorCompetence, pk=pk, vendor=request.user.vendor
        )
        form = CompetenceDocumentUploadForm(
            request.POST, request.FILES, instance=requirement
        )
        if not form.is_valid():
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{field}: {err}")
            return redirect("portal:my-requirement-detail", pk=requirement.pk)

        requirement = form.save(commit=False)
        # Un nuovo file va rivalutato dal back-office: reset della verifica.
        requirement.verified = False
        requirement.verified_by = None
        requirement.verified_date = None
        requirement.save()

        messages.success(
            request,
            f"Documento del requisito '{requirement.competence.name}' "
            "caricato correttamente.",
        )
        return redirect("portal:my-requirement-detail", pk=requirement.pk)


class MyRequirementDetailView(VendorRequiredMixin, DetailView):
    """Dettaglio di un singolo requisito professionale del proprio vendor.

    Filtro queryset su `vendor=request.user.vendor` per evitare IDOR.
    """

    template_name = "portal/requirements/detail.html"
    context_object_name = "requirement"

    def get_queryset(self):
        return _vendor_competences_qs(self.request.user.vendor)


# --- servizi fornitori -------------------------------------------------------


def _vendor_services_qs(vendor):
    """Queryset dei servizi assegnati al vendor.

    I `VendorService` sono pre-creati dal back-office (singolarmente o in
    blocco tramite `ServiceSet`, vedi `vendors/admin.py`). Il fornitore non
    sceglie i servizi che eroga: può solo proporre modifiche ai campi
    descrittivi (vedi `EDITABLE_VENDOR_SERVICE_FIELDS`) sui record già
    assegnati al proprio vendor.
    """
    return VendorService.objects.filter(vendor=vendor).select_related(
        "service_type", "contract"
    )


class MyServicesView(VendorRequiredMixin, ListView):
    """Lista dei servizi assegnati al proprio fornitore.

    Prezzo orario e contratto collegato sono mostrati in sola lettura
    (badge "gestito dal back-office"): non sono mai esposti in scrittura al
    fornitore, vedi `VendorServiceChangeForm`.
    """

    template_name = "portal/services/list.html"
    context_object_name = "services"

    def get_queryset(self):
        return _vendor_services_qs(self.request.user.vendor).order_by(
            "-is_primary", "service_type__name"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["vendor"] = self.request.user.vendor
        ctx["pending_service_ids"] = set(
            VendorChangeRequest.objects.filter(
                vendor_service__vendor=self.request.user.vendor,
                status=VendorChangeRequest.STATUS_PENDING,
            ).values_list("vendor_service_id", flat=True)
        )
        return ctx


class VendorServiceChangeRequestCreateView(VendorRequiredMixin, View):
    """Form modifica di un servizio → genera VendorChangeRequest PENDING.

    Vincolo: una sola richiesta pendente alla volta per ciascun servizio
    (indipendente dalle richieste sugli altri servizi o sull'anagrafica).
    """

    template_name = "portal/services/change_form.html"

    def _get_service(self, request, pk):
        return get_object_or_404(
            VendorService, pk=pk, vendor=request.user.vendor
        )

    def _has_pending(self, vendor_service):
        return VendorChangeRequest.objects.filter(
            vendor_service=vendor_service,
            status=VendorChangeRequest.STATUS_PENDING,
        ).exists()

    def get(self, request, pk, *args, **kwargs):
        service = self._get_service(request, pk)
        if self._has_pending(service):
            messages.warning(
                request,
                "Hai già una richiesta di modifica in attesa per questo "
                "servizio. Attendi l'esito prima di inviarne un'altra.",
            )
            return redirect("portal:my-services")
        form = VendorServiceChangeForm(instance=service)
        from django.shortcuts import render

        return render(
            request, self.template_name, {"form": form, "service": service}
        )

    def post(self, request, pk, *args, **kwargs):
        service = self._get_service(request, pk)
        if self._has_pending(service):
            messages.warning(request, "Hai già una richiesta in attesa.")
            return redirect("portal:my-services")

        form = VendorServiceChangeForm(request.POST, instance=service)
        if not form.is_valid():
            from django.shortcuts import render

            return render(
                request,
                self.template_name,
                {"form": form, "service": service},
            )

        diff = form.compute_diff()
        if not diff:
            messages.info(request, "Nessuna modifica rilevata.")
            return redirect("portal:my-services")

        VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=request.user,
            changes=diff,
        )
        messages.success(
            request,
            "Richiesta di modifica inviata. "
            "Il back-office la valuterà a breve.",
        )
        return redirect("portal:my-change-requests")


# --- attributi operativi -----------------------------------------------------


class MyOperationalAttributesView(VendorRequiredMixin, View):
    """Attributi operativi del proprio fornitore: scrittura diretta.

    A differenza dell'anagrafica e dei servizi, qui non c'è approvazione
    BO: sono dati puramente descrittivi/operativi (capacità, mezzi,
    disponibilità), senza impatto su compliance/audit. Il record è un
    OneToOne col vendor e può non esistere ancora: viene creato al primo
    accesso (`get_or_create`).
    """

    template_name = "portal/operational_attributes/form.html"

    def get(self, request, *args, **kwargs):
        attributes, _created = (
            VendorOperationalAttributes.objects.get_or_create(
                vendor=request.user.vendor
            )
        )
        form = VendorOperationalAttributesForm(instance=attributes)
        from django.shortcuts import render

        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        attributes, _created = (
            VendorOperationalAttributes.objects.get_or_create(
                vendor=request.user.vendor
            )
        )
        form = VendorOperationalAttributesForm(
            request.POST, instance=attributes
        )
        if not form.is_valid():
            from django.shortcuts import render

            return render(request, self.template_name, {"form": form})

        form.save()
        messages.success(request, "Attributi operativi aggiornati.")
        return redirect("portal:my-operational-attributes")


# --- anagrafica & qualifica (Fase 2) ---------------------------------------


class MyVendorProfileView(VendorRequiredMixin, TemplateView):
    """Visualizzazione anagrafica del proprio fornitore (sola lettura)."""

    template_name = "portal/profile/detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        vendor = self.request.user.vendor
        pending = VendorChangeRequest.objects.filter(
            vendor=vendor,
            vendor_service__isnull=True,
            status=VendorChangeRequest.STATUS_PENDING,
        ).first()
        ctx.update({"vendor": vendor, "pending_change_request": pending})
        return ctx


class VendorChangeRequestCreateView(VendorRequiredMixin, View):
    """Form modifica anagrafica → genera VendorChangeRequest in stato PENDING.

    Vincolo: una sola richiesta anagrafica pendente alla volta per ciascun
    fornitore (indipendente da eventuali richieste pendenti sui servizi,
    che sono scoped sul singolo `VendorService` — vedi
    `VendorServiceChangeRequestCreateView._has_pending()`).
    """

    template_name = "portal/profile/change_form.html"

    def _has_pending(self, vendor):
        return VendorChangeRequest.objects.filter(
            vendor=vendor,
            vendor_service__isnull=True,
            status=VendorChangeRequest.STATUS_PENDING,
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

        return render(
            request, self.template_name, {"form": form, "vendor": vendor}
        )

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
            "Richiesta di modifica inviata. "
            "Il back-office la valuterà a breve.",
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
        status = self.request.GET.get(
            "status", VendorChangeRequest.STATUS_PENDING
        )
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
    """POST: approva o rifiuta una richiesta. Action/note dal form."""

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        change_request = get_object_or_404(VendorChangeRequest, pk=pk)
        if not change_request.is_pending:
            messages.warning(
                request, "La richiesta non è più in stato 'in attesa'."
            )
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
                f"Modifiche applicate al fornitore "
                f"{change_request.vendor.name}.",
            )
        else:
            change_request.reject(reviewer=request.user, notes=notes)
            messages.warning(
                request,
                f"Richiesta rifiutata per {change_request.vendor.name}.",
            )
        return redirect("portal:bo-change-requests")


# --- area BO (gestione requisiti professionali) -----------------------------


class BoRequirementListView(BackOfficeRequiredMixin, ListView):
    """Lista requisiti professionali con documento caricato, per il BO.

    Default: solo quelli con `document_file` presente e non ancora
    verificati (`verified=False`) — analogo al default "solo PENDING" di
    `BoChangeRequestListView`.
    """

    template_name = "portal/backoffice/requirements_list.html"
    context_object_name = "requirements"
    paginate_by = 25

    def get_queryset(self):
        verified = self.request.GET.get("verified", "false")
        if verified == "expired":
            # Data di scadenza superata, a prescindere da verified/
            # document_file: `VendorCompetence` non ha un campo di stato
            # (solo la property calcolata `expiry_status`), quindi il
            # filtro va fatto direttamente sulla data.
            return (
                VendorCompetence.objects.select_related("vendor", "competence")
                .filter(
                    expiry_date__isnull=False,
                    expiry_date__lt=timezone.now().date(),
                )
                .order_by("expiry_date")
            )
        qs = VendorCompetence.objects.select_related(
            "vendor", "competence"
        ).exclude(document_file="")
        if verified in ("true", "false"):
            qs = qs.filter(verified=(verified == "true"))
        return qs.order_by("-updated_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["verified_filter"] = self.request.GET.get("verified", "false")
        return ctx


class BoRequirementDetailView(BackOfficeRequiredMixin, DetailView):
    """Dettaglio requisito professionale + form approvazione/rifiuto."""

    template_name = "portal/backoffice/requirement_detail.html"
    context_object_name = "requirement"
    model = VendorCompetence

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = VendorChangeReviewForm()
        return ctx


class BoRequirementReviewView(BackOfficeRequiredMixin, View):
    """POST: verifica o rifiuta il documento di un requisito professionale."""

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        requirement = get_object_or_404(VendorCompetence, pk=pk)

        form = VendorChangeReviewForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Form non valido.")
            return redirect("portal:bo-requirement-detail", pk=pk)

        action = form.cleaned_data["action"]
        notes = form.cleaned_data.get("review_notes", "")

        requirement.verified = action == "approve"
        requirement.verified_by = request.user.name or request.user.email
        requirement.verified_date = timezone.now().date()
        if notes:
            requirement.notes = notes
        requirement.save()

        if action == "approve":
            messages.success(
                request,
                f"Requisito '{requirement.competence.name}' verificato per "
                f"{requirement.vendor.name}.",
            )
        else:
            messages.warning(
                request,
                f"Requisito '{requirement.competence.name}' rifiutato per "
                f"{requirement.vendor.name}.",
            )
        return redirect("portal:bo-requirements")


# --- area BO (gestione documenti) -------------------------------------------


class BoDocumentListView(BackOfficeRequiredMixin, ListView):
    """Lista documenti per il back-office, default solo `UPLOADED`
    ("da revisionare") — analogo al default "solo PENDING" di
    `BoChangeRequestListView`."""

    template_name = "portal/backoffice/documents_list.html"
    context_object_name = "documents"
    paginate_by = 25

    def get_queryset(self):
        qs = Document.objects.select_related("vendor", "document_type")
        status = self.request.GET.get("status", "UPLOADED")
        if status == "EXPIRED":
            # Data di scadenza superata, indipendentemente dallo stato
            # salvato (che si aggiorna solo al prossimo save() del
            # documento, non c'è un job periodico che lo tiene allineato).
            return qs.filter(
                expiry_date__isnull=False,
                expiry_date__lt=timezone.now().date(),
            ).order_by("expiry_date")
        if status in dict(Document.STATUS_CHOICES):
            qs = qs.filter(status=status)
        return qs.order_by("-uploaded_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_filter"] = self.request.GET.get("status", "UPLOADED")
        # "Scaduto" per primo nel filtro: è la priorità più alta da
        # revisionare, gli altri stati restano nell'ordine del modello.
        ctx["status_choices"] = [
            ("EXPIRED", dict(Document.STATUS_CHOICES)["EXPIRED"]),
            *[c for c in Document.STATUS_CHOICES if c[0] != "EXPIRED"],
        ]
        return ctx


class BoDocumentDetailView(BackOfficeRequiredMixin, DetailView):
    """Dettaglio documento + form approvazione/rifiuto."""

    template_name = "portal/backoffice/document_detail.html"
    context_object_name = "document"
    model = Document

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = VendorChangeReviewForm()
        return ctx


class BoDocumentReviewView(BackOfficeRequiredMixin, View):
    """POST: approva o rifiuta un documento caricato dal fornitore."""

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        document = get_object_or_404(Document, pk=pk)

        form = VendorChangeReviewForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Form non valido.")
            return redirect("portal:bo-document-detail", pk=pk)

        action = form.cleaned_data["action"]
        notes = form.cleaned_data.get("review_notes", "")

        document.status = "APPROVED" if action == "approve" else "REJECTED"
        document.reviewed_by = request.user
        document.reviewed_at = timezone.now()
        if notes:
            document.notes = notes
        document.save()

        if action == "approve":
            messages.success(
                request,
                f"Documento '{document.document_type.name}' approvato per "
                f"{document.vendor.name}.",
            )
        else:
            messages.warning(
                request,
                f"Documento '{document.document_type.name}' rifiutato per "
                f"{document.vendor.name}.",
            )
        return redirect("portal:bo-documents")


# --- area BO (dashboard consolidata) ----------------------------------------


class BoDashboardView(BackOfficeRequiredMixin, TemplateView):
    """Dashboard consolidata per il back-office.

    KPI globali di sistema in alto; sezioni personali (fornitori con
    `managed_by` uguale all'utente loggato) con gli aggiornamenti da
    revisionare e i fornitori senza documenti/requisiti assegnati.
    """

    template_name = "portal/backoffice/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # KPI globali (tutto il sistema, indipendenti dal gestore loggato).
        ctx["total_documents"] = Document.objects.count()
        ctx["documents_pending_review"] = Document.objects.filter(
            status="UPLOADED"
        ).count()
        ctx["total_requirements"] = VendorCompetence.objects.count()
        ctx["requirements_pending_review"] = (
            VendorCompetence.objects.exclude(document_file="")
            .filter(verified=False)
            .count()
        )
        ctx["total_change_requests"] = VendorChangeRequest.objects.count()
        ctx["change_requests_pending"] = VendorChangeRequest.objects.filter(
            status=VendorChangeRequest.STATUS_PENDING
        ).count()

        # Scaduti: data di scadenza superata, a prescindere dallo stato
        # salvato (vedi nota in BoDocumentListView/BoRequirementListView).
        today = timezone.now().date()
        ctx["documents_expired"] = Document.objects.filter(
            expiry_date__isnull=False, expiry_date__lt=today
        ).count()
        ctx["requirements_expired"] = VendorCompetence.objects.filter(
            expiry_date__isnull=False, expiry_date__lt=today
        ).count()

        # Sezioni personali: solo i fornitori gestiti dall'utente loggato.
        user = self.request.user
        ctx["my_pending_change_requests"] = (
            VendorChangeRequest.objects.filter(
                vendor__managed_by=user,
                status=VendorChangeRequest.STATUS_PENDING,
            )
            .select_related("vendor", "vendor_service")
            .order_by("-created_at")[:10]
        )
        ctx["my_pending_documents"] = (
            Document.objects.filter(vendor__managed_by=user, status="UPLOADED")
            .select_related("vendor", "document_type")
            .order_by("-uploaded_at")[:10]
        )
        ctx["my_pending_requirements"] = (
            VendorCompetence.objects.filter(
                vendor__managed_by=user, verified=False
            )
            .exclude(document_file="")
            .select_related("vendor", "competence")
            .order_by("-updated_at")[:10]
        )
        ctx["my_expired_documents"] = (
            Document.objects.filter(
                vendor__managed_by=user,
                expiry_date__isnull=False,
                expiry_date__lt=today,
            )
            .select_related("vendor", "document_type")
            .order_by("expiry_date")[:10]
        )
        ctx["my_expired_requirements"] = (
            VendorCompetence.objects.filter(
                vendor__managed_by=user,
                expiry_date__isnull=False,
                expiry_date__lt=today,
            )
            .select_related("vendor", "competence")
            .order_by("expiry_date")[:10]
        )
        ctx["my_vendors_without_documents"] = Vendor.objects.filter(
            managed_by=user, documents__isnull=True
        )[:10]
        ctx["my_vendors_without_requirements"] = Vendor.objects.filter(
            managed_by=user, vendor_competences__isnull=True
        )[:10]

        return ctx


# --- retro-compatibilità ----------------------------------------------------


class LegacyPortalRedirectView(View):
    """Redirect 301 da /documents/portal/ alla nuova dashboard /portale/."""

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse("portal:dashboard"))
