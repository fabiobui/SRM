"""Creazione rapida di un fornitore prospetto dalla dashboard.

Servono solo i dati minimi (ragione sociale, P.IVA o C.F., email): il
fornitore nasce "In attesa", l'utente che lo crea ne diventa l'utente di
gestione e il fornitore riceve subito l'invito al portale.
"""

import logging
from dataclasses import dataclass, field

from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from vendor_management_system.users.models import User
from vendor_management_system.users.portal_access import (
    create_portal_user,
    send_portal_invite,
)
from vendor_management_system.vendors.models import Vendor

logger = logging.getLogger(__name__)


class ProspectVendorForm(forms.Form):
    name = forms.CharField(label=_("Ragione sociale"), max_length=255)
    vat_number = forms.CharField(
        label=_("Partita IVA"), max_length=20, required=False
    )
    fiscal_code = forms.CharField(
        label=_("Codice Fiscale"), max_length=16, required=False
    )
    email = forms.EmailField(label=_("Email del fornitore"))

    def clean_name(self):
        return self.cleaned_data["name"].strip()

    def clean_vat_number(self):
        return (self.cleaned_data.get("vat_number") or "").strip()

    def clean_fiscal_code(self):
        value = (self.cleaned_data.get("fiscal_code") or "").strip()
        if value and Vendor.objects.filter(fiscal_code__iexact=value).exists():
            raise forms.ValidationError(
                _("Esiste già un fornitore con questo Codice Fiscale.")
            )
        return value

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        # Un'email già usata da un utente impedirebbe l'accesso al portale:
        # meglio fermarsi prima di creare un'anagrafica orfana.
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                _("Questa email è già usata da un altro utente.")
            )
        return email

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("vat_number") and not cleaned.get("fiscal_code"):
            if "vat_number" not in self.errors and (
                "fiscal_code" not in self.errors
            ):
                raise forms.ValidationError(
                    _("Indica la Partita IVA o il Codice Fiscale.")
                )
        return cleaned


@dataclass
class ProspectResult:
    vendor: Vendor
    warnings: list = field(default_factory=list)
    invite_sent_to: list = field(default_factory=list)


def create_prospect(data, created_by, request):
    """Crea fornitore e utenza portale, poi invia l'invito.

    Un errore di invio non annulla la creazione: il risultato porta un
    avviso e l'operatore può usare "Reinvia invito" dall'admin.
    """
    warnings = []
    vat_number = data["vat_number"]
    if (
        vat_number
        and Vendor.objects.filter(vat_number__iexact=vat_number).exists()
    ):
        warnings.append(
            "La Partita IVA è già usata da un altro fornitore: "
            "l'anagrafica è stata creata comunque."
        )

    with transaction.atomic():
        vendor = Vendor.objects.create(
            name=data["name"],
            vat_number=vat_number or None,
            fiscal_code=data["fiscal_code"] or None,
            email=data["email"],
            managed_by=created_by,
        )
        user = create_portal_user(vendor)

    result = ProspectResult(vendor=vendor, warnings=warnings)
    try:
        result.invite_sent_to = send_portal_invite(user, request)
    except Exception:  # noqa: BLE001 - già loggato da send_templated_email
        logger.exception("Invito portale non inviato per %s", vendor.pk)
        result.warnings.append(
            "Invio dell'email d'invito non riuscito: usa \"Reinvia "
            "invito\" dall'anagrafica del fornitore."
        )
    return result
