"""Form del portale fornitore.

I form definiti qui sono usati dalle view dell'area /portale/. Il pattern è:
- `DocumentUploadForm`: upload file + metadati documento; usato da
  MyDocumentUploadView.
- `VendorProfileChangeForm`: anagrafica del proprio Vendor con whitelist di
  campi modificabili. Non salva direttamente il Vendor — il diff finisce in
  una VendorChangeRequest che il back-office deve approvare.
- `VendorServiceChangeForm`: campi descrittivi di un proprio VendorService
  (prezzo/contratto restano BO-only). Stesso pattern: il diff finisce in una
  VendorChangeRequest legata al servizio.
- `VendorServiceAddRequestForm`: proposta di un nuovo servizio dal catalogo
  (`ServiceType`), non ancora assegnato al vendor. Stesso pattern: genera una
  VendorChangeRequest (request_type=ADD_SERVICE) da approvare.
- `VendorOperationalAttributesForm`: attributi operativi del proprio Vendor.
  A differenza dei form precedenti salva direttamente (nessuna approvazione).
"""

from collections import defaultdict

from django import forms
from django.utils.translation import gettext_lazy as _

from vendor_management_system.documents.models import Document
from vendor_management_system.vendors.competence import (
    current_selection,
    format_selection,
)
from vendor_management_system.vendors.models import (
    ServiceType,
    Vendor,
    VendorCompetence,
    VendorOperationalAttributes,
    VendorService,
    category_scope_ids,
)
from vendor_management_system.vendors.widgets import CompetenceAreaField

from .models import (
    COMPETENCE_AREAS_KEY,
    EDITABLE_VENDOR_SERVICE_FIELDS,
    VendorChangeRequest,
)

# Whitelist server-side: solo questi campi sono modificabili dal fornitore via
# richiesta di modifica anagrafica. Campi identificativi/qualificativi/audit
# restano sotto il controllo del back-office. `address` non è qui: è una FK a
# un modello strutturato (Address), gestita a parte come testo libero (vedi
# `VendorProfileChangeForm.address_text`).
EDITABLE_VENDOR_FIELDS = (
    "name",
    "email",
    "phone",
    "website",
    "reference_contact",
    "pec",
    "reference_person",
    "contact_details",
    "vendor_task_description",
)


def format_address(address) -> str:
    """Formatta un Address come singola stringa per il campo testo libero."""
    if not address:
        return ""
    parts = [
        address.street_address,
        address.street_address_2,
        address.postal_code,
        address.city,
        address.state_province,
    ]
    return ", ".join(p for p in parts if p)


class DocumentUploadForm(forms.ModelForm):
    """Form upload di un singolo documento da parte del fornitore.

    Il `Document` è già stato creato dal BO (con `document_type` definito e
    stato `PENDING`). Il fornitore carica solo il file e, opzionalmente,
    aggiorna le date e le note. La view identifica il documento dal `pk` in
    URL e applica `vendor=request.user.vendor` come filtro per evitare IDOR.
    """

    class Meta:
        model = Document
        fields = ("file", "issue_date", "expiry_date", "notes")
        widgets = {
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "issue_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Note opzionali",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["file"].required = True

    def clean_file(self):
        f = self.cleaned_data.get("file")
        if not f:
            raise forms.ValidationError(_("Devi caricare un file."))
        max_size = 20 * 1024 * 1024  # 20 MB
        if f.size > max_size:
            raise forms.ValidationError(_("File troppo grande (max 20 MB)."))
        return f


class CompetenceDocumentUploadForm(forms.ModelForm):
    """Form upload del documento/attestato di un requisito assegnato.

    La `VendorCompetence` è già stata creata dal BO (con `competence`
    definita). Il fornitore carica solo il file (`document_file`) e,
    opzionalmente, aggiorna numero certificazione, date e note. La view
    identifica il record dal `pk` in URL e applica
    `vendor=request.user.vendor` come filtro per evitare IDOR.
    """

    class Meta:
        model = VendorCompetence
        fields = (
            "document_file",
            "certification_number",
            "issue_date",
            "expiry_date",
            "notes",
        )
        widgets = {
            "document_file": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "certification_number": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "issue_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Note opzionali",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["document_file"].required = True

    def clean_document_file(self):
        f = self.cleaned_data.get("document_file")
        if not f:
            raise forms.ValidationError(_("Devi caricare un file."))
        max_size = 20 * 1024 * 1024  # 20 MB
        if f.size > max_size:
            raise forms.ValidationError(_("File troppo grande (max 20 MB)."))
        return f


class VendorProfileChangeForm(forms.ModelForm):
    """Form modifica anagrafica fornitore.

    Espone i campi in `EDITABLE_VENDOR_FIELDS` più `address_text` (testo
    libero per l'indirizzo). La view `VendorChangeRequestCreateView` NON
    salva il Vendor: usa `compute_diff()` per generare la
    `VendorChangeRequest`.
    """

    class Meta:
        model = Vendor
        fields = EDITABLE_VENDOR_FIELDS
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "reference_contact": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "pec": forms.EmailInput(attrs={"class": "form-control"}),
            "reference_person": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "contact_details": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "vendor_task_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    address_text = forms.CharField(
        label=_("Indirizzo"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        help_text=_(
            "Testo libero: via, CAP, città, provincia. Nessuna "
            "normalizzazione automatica in questa fase."
        ),
    )

    # Come `address_text`: campo non-model, perché la copertura vive in due
    # M2M che non sono serializzabili nel diff JSON.
    competence_areas = CompetenceAreaField(
        label=_("Zone di competenza"),
        required=False,
        help_text=_(
            "Province italiane coperte e/o nazioni estere in cui operi. "
            "Una regione risulta coperta per intero quando lo sono tutte "
            "le sue province."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Snapshot PRIMA di is_valid(): il _post_clean() di Django muta
        # self.instance coi valori nuovi (vedi ModelForm.construct_instance),
        # quindi leggere self.instance dopo is_valid() confronterebbe il
        # nuovo valore con se stesso. Va salvato qui, non in compute_diff().
        self._old_values = {
            field: getattr(self.instance, field, None)
            for field in EDITABLE_VENDOR_FIELDS
        }
        self._old_address = format_address(self.instance.address)
        self.fields["address_text"].initial = self._old_address

        self._old_areas = current_selection(self.instance)
        self._old_areas_label = format_selection(
            self._old_areas["provinces"], self._old_areas["countries"]
        )
        self.fields["competence_areas"].initial = self._old_areas

    def compute_diff(self) -> dict:
        """Calcola il diff fra il valore originale e quello proposto.

        Ritorna {field: {"old": ..., "new": ...}} solo per i campi
        effettivamente cambiati. `address` è gestito a parte perché non è
        un campo del `ModelForm` (vedi `EDITABLE_VENDOR_FIELDS`).
        """
        if not self.is_valid():
            return {}

        diff = {}
        for field in EDITABLE_VENDOR_FIELDS:
            new_value = self.cleaned_data.get(field)
            old_value = self._old_values.get(field)
            # Confronto stringhe per evitare differenze su None vs ""
            old_norm = "" if old_value is None else old_value
            new_norm = "" if new_value is None else new_value
            if old_norm != new_norm:
                diff[field] = {"old": old_value, "new": new_value}

        new_address = self.cleaned_data.get("address_text", "").strip()
        if self._old_address != new_address:
            diff["address"] = {"old": self._old_address, "new": new_address}

        # Zone di competenza. In `changes` finiscono due cose:
        # la frase leggibile in `old`/`new`, che i tre renderer generici
        # del diff stampano cosi' com'e' senza bisogno di un template
        # filter, e i codici in `old_codes`/`new_codes`, che sono la
        # fonte macchina usata dall'approvazione. Le frasi vanno congelate
        # qui e non ricalcolate a video: dopo l'approvazione `old` deve
        # continuare a raccontare com'era allora. Tutto e' str/list[str]
        # perche' `VendorChangeRequest.changes` e' un JSONField senza
        # DjangoJSONEncoder.
        nuove_aree = self.cleaned_data.get(COMPETENCE_AREAS_KEY) or {
            "provinces": [],
            "countries": [],
        }
        prima = (
            set(self._old_areas["provinces"]),
            set(self._old_areas["countries"]),
        )
        dopo = (set(nuove_aree["provinces"]), set(nuove_aree["countries"]))
        if prima != dopo:
            diff[COMPETENCE_AREAS_KEY] = {
                "old": self._old_areas_label,
                "new": format_selection(
                    nuove_aree["provinces"], nuove_aree["countries"]
                ),
                "old_codes": self._old_areas,
                "new_codes": {
                    "provinces": sorted(nuove_aree["provinces"]),
                    "countries": sorted(nuove_aree["countries"]),
                },
            }

        return diff


class VendorServiceChangeForm(forms.ModelForm):
    """Form modifica di un servizio del fornitore.

    Espone solo `EDITABLE_VENDOR_SERVICE_FIELDS`: prezzo orario e contratto
    collegato restano di sola competenza back-office. Non salva il
    `VendorService` — usa `compute_diff()` per generare la
    `VendorChangeRequest` (legata al servizio, non al vendor).
    """

    class Meta:
        model = VendorService
        fields = EDITABLE_VENDOR_SERVICE_FIELDS
        widgets = {
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Snapshot PRIMA di is_valid(): vedi il commento in
        # VendorProfileChangeForm.__init__ — _post_clean() di Django muta
        # self.instance coi valori nuovi prima che compute_diff() li legga.
        self._old_values = {
            field: getattr(self.instance, field, None)
            for field in EDITABLE_VENDOR_SERVICE_FIELDS
        }

    def compute_diff(self) -> dict:
        """Calcola il diff sui soli campi descrittivi del servizio.

        Stessa logica di `VendorProfileChangeForm.compute_diff()`, ristretta
        a `EDITABLE_VENDOR_SERVICE_FIELDS`.
        """
        if not self.is_valid():
            return {}

        diff = {}
        for field in EDITABLE_VENDOR_SERVICE_FIELDS:
            new_value = self.cleaned_data.get(field)
            old_value = self._old_values.get(field)
            old_norm = "" if old_value is None else old_value
            new_norm = "" if new_value is None else new_value
            if old_norm != new_norm:
                diff[field] = {"old": old_value, "new": new_value}
        return diff


def available_service_types_for_vendor(vendor):
    """Servizi del catalogo che il vendor può proporre di aggiungere.

    Esclude i servizi già assegnati e quelli con una richiesta ADD_SERVICE
    già in attesa (evita duplicati). Se il vendor ha una classificazione
    (`Vendor.category`) e questa — o un suo antenato — ha almeno un
    `ServiceSet` collegato, filtra ai soli servizi di quei set (coerenza
    con la classificazione, vedi `vendors/admin.py:service_sets_view` per lo
    stesso meccanismo lato back-office). Altrimenti (nessuna classificazione,
    o nessun set collegato) ritorna l'intero catalogo attivo: un fornitore
    non deve mai trovarsi con una tendina vuota solo perché per la sua
    classificazione non è stato configurato nessun set.
    """
    already_assigned = VendorService.objects.filter(vendor=vendor).values_list(
        "service_type_id", flat=True
    )
    pending_add = VendorChangeRequest.objects.filter(
        vendor=vendor,
        request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
        status=VendorChangeRequest.STATUS_PENDING,
    ).values_list("service_type_id", flat=True)
    queryset = ServiceType.objects.filter(
        is_active=True, parent__isnull=False
    ).exclude(pk__in=list(already_assigned) + list(pending_add))

    if vendor.category_id:
        scope = category_scope_ids(vendor.category)
        scoped_queryset = queryset.filter(
            service_sets__category_id__in=scope, service_sets__is_active=True
        ).distinct()
        if scoped_queryset.exists():
            return scoped_queryset
    return queryset.distinct()


def _grouped_service_type_choices(queryset):
    """Costruisce le `choices` di un `ChoiceField` raggruppate per sezione
    (optgroup = tipologia padre), stesso ordinamento già usato in
    `VendorServiceInline.formfield_for_foreignkey` (vendors/admin.py)."""
    grouped = defaultdict(list)
    for service_type in queryset.select_related("parent").order_by(
        "parent__sort_order", "parent__name", "sort_order", "name"
    ):
        grouped[service_type.parent.name].append(
            (str(service_type.pk), service_type.name)
        )
    return [(section, items) for section, items in grouped.items()]


class VendorServiceAddRequestForm(forms.Form):
    """Richiesta di aggiunta di un nuovo servizio dal catalogo.

    `service_type` è un `ChoiceField` (non `ModelChoiceField`) per poter
    mostrare la tendina raggruppata per sezione tramite optgroup. Gli altri
    campi ricalcano `EDITABLE_VENDOR_SERVICE_FIELDS`: prezzo orario e
    contratto restano BO-only anche qui. Non salva nulla — la view genera
    la `VendorChangeRequest` (request_type=ADD_SERVICE) da approvare.
    """

    service_type = forms.ChoiceField(
        label=_("Servizio da aggiungere"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_primary = forms.BooleanField(
        label=_("Servizio principale"),
        required=False,
    )
    start_date = forms.DateField(
        label=_("Data inizio erogazione"),
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date"}
        ),
    )
    end_date = forms.DateField(
        label=_("Data fine erogazione"),
        required=False,
        widget=forms.DateInput(
            attrs={"class": "form-control", "type": "date"}
        ),
    )
    notes = forms.CharField(
        label=_("Note"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, vendor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vendor = vendor
        self._queryset = available_service_types_for_vendor(vendor)
        self.fields["service_type"].choices = _grouped_service_type_choices(
            self._queryset
        )

    def clean_service_type(self):
        # Ri-valida sempre contro lo stesso queryset filtrato: non fidarsi
        # del pk POSTato, altrimenti un fornitore potrebbe manomettere il
        # valore per richiedere un servizio già assegnato o fuori scope.
        pk = self.cleaned_data["service_type"]
        service_type = self._queryset.filter(pk=pk).first()
        if service_type is None:
            raise forms.ValidationError(_("Servizio non disponibile."))
        return service_type

    def compute_changes(self) -> dict:
        """Diff da salvare in `VendorChangeRequest.changes`: solo i campi
        effettivamente valorizzati (i campi assenti restano ai default del
        modello `VendorService` alla creazione)."""
        if not self.is_valid():
            return {}
        changes = {}
        for field in EDITABLE_VENDOR_SERVICE_FIELDS:
            value = self.cleaned_data.get(field)
            if value not in (None, "", False):
                changes[field] = {"old": None, "new": value}
        return changes


class VendorOperationalAttributesForm(forms.ModelForm):
    """Form attributi operativi del fornitore.

    A differenza degli altri form del portale salva direttamente il
    `VendorOperationalAttributes` (nessuna approvazione back-office): sono
    dati puramente descrittivi/operativi, senza impatto su compliance o
    audit.
    """

    class Meta:
        model = VendorOperationalAttributes
        exclude = ("id", "vendor")
        widgets = {
            "aerial_platforms_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "mobile_scaffolding_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
            "lifting_equipment_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }


class VendorChangeReviewForm(forms.Form):
    """Form BO per approvare/rifiutare una richiesta di modifica."""

    ACTION_CHOICES = [
        ("approve", _("Approva")),
        ("reject", _("Rifiuta")),
    ]
    action = forms.ChoiceField(
        choices=ACTION_CHOICES, widget=forms.HiddenInput()
    )
    review_notes = forms.CharField(
        label=_("Note di revisione"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
