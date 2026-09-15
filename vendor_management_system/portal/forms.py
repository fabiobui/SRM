"""Form del portale fornitore.

I form definiti qui sono usati dalle view dell'area /portale/. Il pattern è:
- `DocumentUploadForm`: upload file + metadati documento; usato da MyDocumentUploadView.
- `VendorProfileChangeForm`: anagrafica del proprio Vendor con whitelist di campi
  modificabili. Non salva direttamente il Vendor — il diff finisce in una
  VendorChangeRequest che il back-office deve approvare.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from vendor_management_system.documents.models import Document
from vendor_management_system.vendors.models import Vendor, VendorCompetence


# Whitelist server-side: solo questi campi sono modificabili dal fornitore via
# richiesta di modifica anagrafica. Campi identificativi/qualificativi/audit
# restano sotto il controllo del back-office.
EDITABLE_VENDOR_FIELDS = (
    "name",
    "email",
    "phone",
    "website",
    "reference_contact",
    "reference_person",
    "contact_details",
    "vendor_task_description",
)


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
                attrs={"class": "form-control", "rows": 3, "placeholder": "Note opzionali"}
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
    """Form upload del documento/attestato di un requisito professionale assegnato.

    La `VendorCompetence` è già stata creata dal BO (con `competence` definita).
    Il fornitore carica solo il file (`document_file`) e, opzionalmente, aggiorna
    numero certificazione, date e note. La view identifica il record dal `pk` in
    URL e applica `vendor=request.user.vendor` come filtro per evitare IDOR.
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
            "document_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "certification_number": forms.TextInput(attrs={"class": "form-control"}),
            "issue_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Note opzionali"}
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

    Espone solo i campi in `EDITABLE_VENDOR_FIELDS`. La view `VendorChangeRequestCreateView`
    NON salva il Vendor: usa `compute_diff()` per generare la `VendorChangeRequest`.
    """

    class Meta:
        model = Vendor
        fields = EDITABLE_VENDOR_FIELDS
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "reference_contact": forms.TextInput(attrs={"class": "form-control"}),
            "reference_person": forms.TextInput(attrs={"class": "form-control"}),
            "contact_details": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "vendor_task_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
        }

    def compute_diff(self) -> dict:
        """Calcola il diff fra il valore corrente sul DB e il nuovo valore proposto.

        Ritorna {field: {"old": ..., "new": ...}} solo per i campi effettivamente cambiati.
        """
        if not self.is_valid():
            return {}

        diff = {}
        original = self.instance  # il vendor originale (immutato)
        for field in EDITABLE_VENDOR_FIELDS:
            new_value = self.cleaned_data.get(field)
            old_value = getattr(original, field, None)
            # Confronto stringhe per evitare differenze su None vs ""
            old_norm = "" if old_value is None else old_value
            new_norm = "" if new_value is None else new_value
            if old_norm != new_norm:
                diff[field] = {"old": old_value, "new": new_value}
        return diff


class VendorChangeReviewForm(forms.Form):
    """Form usato dal back-office per approvare/rifiutare una richiesta anagrafica."""

    ACTION_CHOICES = [
        ("approve", _("Approva")),
        ("reject", _("Rifiuta")),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput())
    review_notes = forms.CharField(
        label=_("Note di revisione"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
