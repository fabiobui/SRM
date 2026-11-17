"""Form del portale per tecnici e mezzi dei fornitori Subappaltatori.

Il fornitore non sceglie stato di validazione né fornitore: li imposta la
view. Ogni modifica riporta la voce in attesa di validazione del back office.
I form documento ricevono `allowed_types`: la view decide quali tipi
proporre (facoltativi, oppure un solo obbligatorio).
"""

from django import forms

from vendor_management_system.subcontractors.models import (
    Equipment,
    EquipmentDocument,
    Technician,
    TechnicianDocument,
)

_TEXT = {"class": "form-control"}
_DATE = {"class": "form-control", "type": "date"}
_SELECT = {"class": "form-select"}


class TechnicianForm(forms.ModelForm):
    class Meta:
        model = Technician
        fields = ("surname", "first_name", "role", "badge")
        widgets = {
            "surname": forms.TextInput(attrs=_TEXT),
            "first_name": forms.TextInput(attrs=_TEXT),
            "role": forms.TextInput(attrs=_TEXT),
            "badge": forms.TextInput(attrs=_TEXT),
        }


class _DocumentTypeFormMixin:
    def __init__(self, *args, allowed_types=None, **kwargs):
        super().__init__(*args, **kwargs)
        if allowed_types is not None:
            self.fields["doc_type"].choices = allowed_types


class TechnicianDocumentForm(_DocumentTypeFormMixin, forms.ModelForm):
    class Meta:
        model = TechnicianDocument
        fields = ("doc_type", "expiry_date", "file")
        widgets = {
            "doc_type": forms.Select(attrs=_SELECT),
            "expiry_date": forms.DateInput(attrs=_DATE),
            "file": forms.ClearableFileInput(attrs=_TEXT),
        }


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ("equipment_type", "plate", "serial_code", "instrument")
        widgets = {
            "equipment_type": forms.TextInput(attrs=_TEXT),
            "plate": forms.TextInput(attrs=_TEXT),
            "serial_code": forms.TextInput(attrs=_TEXT),
            "instrument": forms.TextInput(attrs=_TEXT),
        }


class EquipmentDocumentForm(_DocumentTypeFormMixin, forms.ModelForm):
    class Meta:
        model = EquipmentDocument
        fields = ("doc_type", "expiry_date", "file")
        widgets = {
            "doc_type": forms.Select(attrs=_SELECT),
            "expiry_date": forms.DateInput(attrs=_DATE),
            "file": forms.ClearableFileInput(attrs=_TEXT),
        }
