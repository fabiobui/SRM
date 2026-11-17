"""Viste del portale per tecnici e mezzi dei fornitori Subappaltatori.

Tutte le viste rispondono 404 ai fornitori che non sono Subappaltatori e
filtrano per fornitore loggato, così una voce altrui non è raggiungibile.
Ogni inserimento o modifica del fornitore torna in stato PENDING.

I documenti obbligatori (colonna dell'Excel) sono elencati nel dettaglio e
caricati da lì, con `?tipo=<chiave>`. Il menu di aggiunta propone solo i
facoltativi.
"""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from vendor_management_system.core.permissions import VendorRequiredMixin
from vendor_management_system.subcontractors.models import (
    EQUIPMENT_DOC_TYPES,
    EQUIPMENT_REQUIRED_DOCS,
    PENDING,
    TECHNICIAN_DOC_TYPES,
    TECHNICIAN_REQUIRED_DOCS,
    Equipment,
    EquipmentDocument,
    Technician,
    TechnicianDocument,
    optional_doc_choices,
)

from .subcontractor_forms import (
    EquipmentDocumentForm,
    EquipmentForm,
    TechnicianDocumentForm,
    TechnicianForm,
)


class SubcontractorRequiredMixin(VendorRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if (
            user.is_authenticated
            and user.is_vendor_user()
            and not user.vendor.is_subappaltatore
        ):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def _vendor(self):
        return self.request.user.vendor


class _VendorScopedMixin(SubcontractorRequiredMixin):
    def get_queryset(self):
        return self.model.objects.filter(vendor=self._vendor())

    def form_valid(self, form):
        form.instance.vendor = self._vendor()
        form.instance.validation_status = PENDING
        messages.success(self.request, self.success_message)
        return super().form_valid(form)


class _DocumentRulesMixin:
    """Regole dei documenti per tipo: obbligatori nel dettaglio, facoltativi
    nel form di aggiunta. Con `?tipo=<obbligatorio>` il form è limitato a
    quel solo tipo."""

    doc_types = None
    required_docs = ()

    def requested_required_type(self):
        tipo = self.request.GET.get("tipo")
        return tipo if tipo in self.required_docs else None

    def allowed_doc_types(self):
        tipo = self.requested_required_type()
        if tipo:
            return [(tipo, self.doc_types[tipo][0])]
        return optional_doc_choices(self.doc_types, self.required_docs)

    def required_rows(self, documents, upload_url):
        rows = []
        for key in self.required_docs:
            latest = (
                documents.filter(doc_type=key)
                .order_by("-uploaded_at", "-pk")
                .first()
            )
            rows.append(
                {
                    "label": self.doc_types[key][0],
                    "doc": latest,
                    "upload_url": f"{upload_url}?tipo={key}",
                }
            )
        return rows

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["allowed_types"] = self.allowed_doc_types()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tipo = self.requested_required_type()
        context["required_label"] = self.doc_types[tipo][0] if tipo else None
        return context


# --- tecnici -----------------------------------------------------------------


class TechnicianListView(SubcontractorRequiredMixin, ListView):
    template_name = "portal/subcontractors/technicians_list.html"
    context_object_name = "technicians"

    def get_queryset(self):
        return Technician.objects.filter(vendor=self._vendor())


class TechnicianCreateView(_VendorScopedMixin, CreateView):
    model = Technician
    form_class = TechnicianForm
    template_name = "portal/subcontractors/form.html"
    success_message = "Tecnico inserito: in attesa di validazione."

    def get_success_url(self):
        return reverse("portal:my-technician-detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title="Nuovo tecnico",
            cancel_url=reverse("portal:my-technicians"),
            **kwargs,
        )


class TechnicianUpdateView(_VendorScopedMixin, UpdateView):
    model = Technician
    form_class = TechnicianForm
    template_name = "portal/subcontractors/form.html"
    success_message = "Tecnico aggiornato: in attesa di validazione."

    def get_success_url(self):
        return reverse("portal:my-technician-detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title="Modifica tecnico",
            cancel_url=reverse(
                "portal:my-technician-detail", args=[self.object.pk]
            ),
            **kwargs,
        )


class TechnicianDetailView(
    _DocumentRulesMixin, SubcontractorRequiredMixin, DetailView
):
    template_name = "portal/subcontractors/technician_detail.html"
    context_object_name = "technician"
    doc_types = TECHNICIAN_DOC_TYPES
    required_docs = TECHNICIAN_REQUIRED_DOCS

    def get_queryset(self):
        return Technician.objects.filter(vendor=self._vendor())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        add_url = reverse(
            "portal:my-technician-document-add", args=[self.object.pk]
        )
        context["documents"] = self.object.documents.all()
        context["add_url"] = add_url
        context["required_rows"] = self.required_rows(
            self.object.documents.all(), add_url
        )
        return context


class TechnicianDocumentCreateView(
    _DocumentRulesMixin, SubcontractorRequiredMixin, CreateView
):
    model = TechnicianDocument
    form_class = TechnicianDocumentForm
    template_name = "portal/subcontractors/form.html"
    doc_types = TECHNICIAN_DOC_TYPES
    required_docs = TECHNICIAN_REQUIRED_DOCS

    @cached_property
    def technician(self):
        return get_object_or_404(
            Technician, pk=self.kwargs["pk"], vendor=self._vendor()
        )

    def form_valid(self, form):
        form.instance.technician = self.technician
        form.instance.validation_status = PENDING
        messages.success(
            self.request, "Documento caricato: in attesa di validazione."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "portal:my-technician-detail", args=[self.technician.pk]
        )

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title=f"Nuovo documento - {self.technician}",
            cancel_url=self.get_success_url(),
            **kwargs,
        )


# --- mezzi/dotazioni ---------------------------------------------------------


class EquipmentListView(SubcontractorRequiredMixin, ListView):
    template_name = "portal/subcontractors/equipment_list.html"
    context_object_name = "equipment_items"

    def get_queryset(self):
        return Equipment.objects.filter(vendor=self._vendor())


class EquipmentCreateView(_VendorScopedMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "portal/subcontractors/form.html"
    success_message = "Mezzo inserito: in attesa di validazione."

    def get_success_url(self):
        return reverse("portal:my-equipment-detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title="Nuovo mezzo/dotazione",
            cancel_url=reverse_lazy("portal:my-equipment"),
            **kwargs,
        )


class EquipmentUpdateView(_VendorScopedMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "portal/subcontractors/form.html"
    success_message = "Mezzo aggiornato: in attesa di validazione."

    def get_success_url(self):
        return reverse("portal:my-equipment-detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title="Modifica mezzo/dotazione",
            cancel_url=reverse(
                "portal:my-equipment-detail", args=[self.object.pk]
            ),
            **kwargs,
        )


class EquipmentDetailView(
    _DocumentRulesMixin, SubcontractorRequiredMixin, DetailView
):
    template_name = "portal/subcontractors/equipment_detail.html"
    context_object_name = "equipment"
    doc_types = EQUIPMENT_DOC_TYPES
    required_docs = EQUIPMENT_REQUIRED_DOCS

    def get_queryset(self):
        return Equipment.objects.filter(vendor=self._vendor())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        add_url = reverse(
            "portal:my-equipment-document-add", args=[self.object.pk]
        )
        context["documents"] = self.object.documents.all()
        context["add_url"] = add_url
        context["required_rows"] = self.required_rows(
            self.object.documents.all(), add_url
        )
        return context


class EquipmentDocumentCreateView(
    _DocumentRulesMixin, SubcontractorRequiredMixin, CreateView
):
    model = EquipmentDocument
    form_class = EquipmentDocumentForm
    template_name = "portal/subcontractors/form.html"
    doc_types = EQUIPMENT_DOC_TYPES
    required_docs = EQUIPMENT_REQUIRED_DOCS

    @cached_property
    def equipment(self):
        return get_object_or_404(
            Equipment, pk=self.kwargs["pk"], vendor=self._vendor()
        )

    def form_valid(self, form):
        form.instance.equipment = self.equipment
        form.instance.validation_status = PENDING
        messages.success(
            self.request, "Documento caricato: in attesa di validazione."
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("portal:my-equipment-detail", args=[self.equipment.pk])

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            title=f"Nuovo documento - {self.equipment}",
            cancel_url=self.get_success_url(),
            **kwargs,
        )
