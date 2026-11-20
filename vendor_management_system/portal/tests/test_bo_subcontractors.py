"""Back office: validazione di tecnici e mezzi dei subappaltatori.

Tecnici e mezzi appartengono alla sezione Sicura del fornitore (Comune se
il fornitore non ha sezioni società): li valida chi può rivedere quella
sezione.
"""

import pytest
from django.urls import reverse

from vendor_management_system.subcontractors.models import (
    PENDING,
    REJECTED,
    VALIDATED,
    Technician,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import VendorCompany
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db


def _bo(client, company):
    user = User.objects.create_user(
        email=f"bo-sub-{company}@example.invalid",
        password="x",
        role="bo_user",
        company_id=company,
    )
    client.force_login(user)


def _technician(with_sicura=True):
    vendor = VendorFactory(vendor_type="Subappaltatore")
    if with_sicura:
        VendorCompany.objects.create(vendor=vendor, company_id="SICURA")
    return Technician.objects.create(
        vendor=vendor, surname="Rossi", first_name="Mario"
    )


def _review(technician):
    return reverse(
        "portal:bo-subcontractor-review",
        kwargs={"kind": "technician", "pk": technician.pk},
    )


def test_bo_sicura_vede_e_valida(client):
    technician = _technician()
    _bo(client, "SICURA")
    page = client.get(reverse("portal:bo-subcontractors"))
    groups = {g["kind"]: list(g["items"]) for g in page.context["groups"]}
    assert technician in groups["technician"]

    client.post(_review(technician), {"action": "approve"})
    technician.refresh_from_db()
    assert technician.validation_status == VALIDATED


def test_respingere_richiede_il_motivo(client):
    technician = _technician()
    _bo(client, "SICURA")
    client.post(_review(technician), {"action": "reject"})
    technician.refresh_from_db()
    assert technician.validation_status == PENDING

    client.post(_review(technician), {"action": "reject", "note": "Badge"})
    technician.refresh_from_db()
    assert technician.validation_status == REJECTED
    assert technician.rejection_note == "Badge"


def test_bo_di_altra_societa_non_vede_ne_valida(client):
    technician = _technician()
    _bo(client, "EVIMED")
    page = client.get(reverse("portal:bo-subcontractors"))
    groups = {g["kind"]: list(g["items"]) for g in page.context["groups"]}
    assert technician not in groups["technician"]
    assert (
        client.post(_review(technician), {"action": "approve"}).status_code
        == 403
    )


def test_fornitore_senza_societa_lo_valida_qualunque_bo(client):
    technician = _technician(with_sicura=False)
    _bo(client, "EVIMED")
    client.post(_review(technician), {"action": "approve"})
    technician.refresh_from_db()
    assert technician.validation_status == VALIDATED
