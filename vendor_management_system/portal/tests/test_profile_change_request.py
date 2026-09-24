"""Test del flusso "Anagrafica" (Informazioni base + Contatti) del portale.

Il fornitore non scrive mai direttamente su `Vendor`: propone modifiche che
finiscono in una `VendorChangeRequest` PENDING, applicata solo quando il
back-office approva. Copre la whitelist `EDITABLE_VENDOR_FIELDS` e il caso
speciale del campo `address` (FK a un modello strutturato, gestito come
testo libero — vedi `portal/forms.py` e `portal/models.py`).
"""

import datetime

import pytest
from django.urls import reverse

from vendor_management_system.portal.forms import format_address
from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import VendorUserFactory
from vendor_management_system.vendors.competence import current_selection
from vendor_management_system.vendors.tests.factories import AddressFactory

PASSWORD = "test-pass-1234"


def _valid_profile_payload(vendor, **overrides):
    # Le zone di competenza sono checkbox: il POST deve ripartire dalla
    # selezione attuale, altrimenti ogni richiesta proporrebbe anche di
    # azzerarle.
    aree = current_selection(vendor)
    payload = {
        "competence_areas_provinces": aree["provinces"],
        "competence_areas_countries": aree["countries"],
        "name": vendor.name,
        "email": vendor.email or "",
        "phone": vendor.phone or "",
        "website": vendor.website or "",
        "reference_contact": vendor.reference_contact or "",
        "pec": vendor.pec or "",
        "reference_person": vendor.reference_person or "",
        "contact_details": vendor.contact_details or "",
        "vendor_task_description": vendor.vendor_task_description or "",
        "address_text": format_address(vendor.address),
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
class TestVendorChangeRequestCreateView:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_proposing_allowed_field_creates_pending_request(self, client):
        user = self._login(client)
        vendor = user.vendor
        payload = _valid_profile_payload(vendor, name="Nuova Ragione Sociale")

        response = client.post(
            reverse("portal:my-profile-change"), data=payload
        )

        assert response.status_code == 302
        change_request = VendorChangeRequest.objects.get(vendor=vendor)
        assert change_request.is_pending
        assert change_request.changes["name"]["new"] == "Nuova Ragione Sociale"
        vendor.refresh_from_db()
        assert vendor.name != "Nuova Ragione Sociale"  # non ancora applicato

    def test_no_diff_creates_no_request(self, client):
        user = self._login(client)
        vendor = user.vendor
        payload = _valid_profile_payload(vendor)

        client.post(reverse("portal:my-profile-change"), data=payload)

        assert not VendorChangeRequest.objects.filter(vendor=vendor).exists()

    def test_non_whitelisted_field_is_ignored(self, client):
        user = self._login(client)
        vendor = user.vendor
        original_vat_number = vendor.vat_number
        payload = _valid_profile_payload(
            vendor, vat_number="00000000000", vendor_code="HACKED"
        )

        client.post(reverse("portal:my-profile-change"), data=payload)

        change_request = VendorChangeRequest.objects.filter(
            vendor=vendor
        ).first()
        if change_request:
            assert "vat_number" not in change_request.changes
            assert "vendor_code" not in change_request.changes
        vendor.refresh_from_db()
        assert vendor.vat_number == original_vat_number

    def test_pec_is_editable(self, client):
        user = self._login(client)
        vendor = user.vendor
        payload = _valid_profile_payload(
            vendor, pec="fornitore@pec.example.it"
        )

        client.post(reverse("portal:my-profile-change"), data=payload)

        change_request = VendorChangeRequest.objects.get(vendor=vendor)
        assert (
            change_request.changes["pec"]["new"] == "fornitore@pec.example.it"
        )
        vendor.refresh_from_db()
        assert vendor.pec != "fornitore@pec.example.it"  # non ancora applicato

    def test_first_supply_date_is_not_editable(self, client):
        user = self._login(client)
        vendor = user.vendor
        original_first_supply_date = vendor.first_supply_date
        payload = _valid_profile_payload(
            vendor, first_supply_date="2020-01-15"
        )

        client.post(reverse("portal:my-profile-change"), data=payload)

        change_request = VendorChangeRequest.objects.filter(
            vendor=vendor
        ).first()
        if change_request:
            assert "first_supply_date" not in change_request.changes
        vendor.refresh_from_db()
        assert vendor.first_supply_date == original_first_supply_date

    def test_second_pending_profile_request_is_blocked(self, client):
        user = self._login(client)
        vendor = user.vendor
        client.post(
            reverse("portal:my-profile-change"),
            data=_valid_profile_payload(vendor, name="Prima modifica"),
        )

        response = client.post(
            reverse("portal:my-profile-change"),
            data=_valid_profile_payload(vendor, name="Seconda modifica"),
        )

        assert response.status_code == 302
        assert VendorChangeRequest.objects.filter(vendor=vendor).count() == 1

    def test_new_address_text_is_recorded_in_diff(self, client):
        user = self._login(client)
        vendor = user.vendor
        payload = _valid_profile_payload(
            vendor, address_text="Via Nuova 1, 20100, Milano"
        )

        client.post(reverse("portal:my-profile-change"), data=payload)

        change_request = VendorChangeRequest.objects.get(vendor=vendor)
        assert (
            change_request.changes["address"]["new"]
            == "Via Nuova 1, 20100, Milano"
        )


@pytest.mark.django_db
class TestVendorProfileDetailView:
    def test_pec_and_first_supply_date_are_displayed(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        vendor = user.vendor
        vendor.pec = "fornitore@pec.example.it"
        vendor.first_supply_date = datetime.date(2020, 1, 15)
        vendor.save()

        response = client.get(reverse("portal:my-profile"))

        assert response.status_code == 200
        content = response.content.decode()
        assert "fornitore@pec.example.it" in content
        assert "15/01/2020" in content


@pytest.mark.django_db
class TestApplyAddressChange:
    def test_approving_creates_address_when_none_exists(self):
        user = VendorUserFactory(password=PASSWORD)
        vendor = user.vendor
        vendor.address = None
        vendor.save()
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=user,
            changes={"address": {"old": "", "new": "Via Roma 1, Milano"}},
        )
        reviewer = VendorUserFactory(password=PASSWORD)

        change_request.apply_to_vendor(reviewer=reviewer)

        vendor.refresh_from_db()
        assert vendor.address is not None
        assert vendor.address.street_address == "Via Roma 1, Milano"

    def test_approving_updates_existing_address(self):
        user = VendorUserFactory(password=PASSWORD)
        vendor = user.vendor
        vendor.address = AddressFactory(street_address="Vecchio indirizzo")
        vendor.save()
        existing_address_id = vendor.address_id
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=user,
            changes={
                "address": {"old": "Vecchio indirizzo", "new": "Via Nuova 5"}
            },
        )
        reviewer = VendorUserFactory(password=PASSWORD)

        change_request.apply_to_vendor(reviewer=reviewer)

        vendor.refresh_from_db()
        assert vendor.address_id == existing_address_id
        assert vendor.address.street_address == "Via Nuova 5"
