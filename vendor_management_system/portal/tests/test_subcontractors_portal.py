"""Portale fornitore: tecnici e mezzi dei soli fornitori Subappaltatori."""

from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.portal.tests.factories import VendorUserFactory
from vendor_management_system.subcontractors.models import (
    PENDING,
    VALIDATED,
    Equipment,
    Technician,
    TechnicianDocument,
)

PASSWORD = "test-pass-1234"


def _login_subappaltatore(client):
    user = VendorUserFactory(password=PASSWORD)
    user.vendor.vendor_type = "Subappaltatore"
    user.vendor.save()
    client.login(email=user.email, password=PASSWORD)
    return user


def _login_altro_fornitore(client):
    user = VendorUserFactory(password=PASSWORD)
    client.login(email=user.email, password=PASSWORD)
    return user


@pytest.mark.django_db
class TestSubcontractorPortalAccess:
    @pytest.mark.parametrize(
        "url_name",
        [
            "portal:my-technicians",
            "portal:my-equipment",
            "portal:my-technician-new",
        ],
    )
    def test_fornitore_non_subappaltatore_riceve_404(self, client, url_name):
        _login_altro_fornitore(client)

        response = client.get(reverse(url_name))

        assert response.status_code == 404

    def test_subappaltatore_vede_le_sezioni(self, client):
        _login_subappaltatore(client)

        assert client.get(reverse("portal:my-technicians")).status_code == 200
        assert client.get(reverse("portal:my-equipment")).status_code == 200

    def test_voce_di_un_altro_fornitore_non_e_raggiungibile(
        self, client, vendor_factory
    ):
        _login_subappaltatore(client)
        altro = vendor_factory(vendor_type="Subappaltatore")
        tech = Technician.objects.create(
            vendor=altro, surname="Bianchi", first_name="Luca"
        )

        response = client.get(
            reverse("portal:my-technician-detail", args=[tech.pk])
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestSubcontractorPortalWrites:
    def test_nuovo_tecnico_entra_in_attesa_di_validazione(self, client):
        user = _login_subappaltatore(client)

        response = client.post(
            reverse("portal:my-technician-new"),
            data={
                "surname": "Rossi",
                "first_name": "Mario",
                "role": "Elettricista",
                "badge": "B-001",
            },
        )

        assert response.status_code == 302
        tech = Technician.objects.get(surname="Rossi")
        assert tech.vendor == user.vendor
        assert tech.validation_status == PENDING

    def test_modifica_riporta_il_tecnico_in_attesa(self, client):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor,
            surname="Rossi",
            first_name="Mario",
            validation_status=VALIDATED,
        )

        client.post(
            reverse("portal:my-technician-edit", args=[tech.pk]),
            data={
                "surname": "Rossi",
                "first_name": "Marco",
                "role": "",
                "badge": "",
            },
        )

        tech.refresh_from_db()
        assert tech.first_name == "Marco"
        assert tech.validation_status == PENDING

    def test_documento_con_scadenza_senza_data_viene_rifiutato(self, client):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor, surname="Rossi", first_name="Mario"
        )

        response = client.post(
            reverse("portal:my-technician-document-add", args=[tech.pk]),
            data={
                "doc_type": "antincendio",
                "expiry_date": "",
                "file": SimpleUploadedFile("a.pdf", b"x"),
            },
        )

        assert response.status_code == 200
        assert not TechnicianDocument.objects.filter(technician=tech).exists()

    def test_documento_valido_entra_in_attesa(self, client):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor, surname="Rossi", first_name="Mario"
        )

        client.post(
            reverse("portal:my-technician-document-add", args=[tech.pk]),
            data={
                "doc_type": "antincendio",
                "expiry_date": date(2027, 6, 30).isoformat(),
                "file": SimpleUploadedFile("a.pdf", b"x"),
            },
        )

        doc = TechnicianDocument.objects.get(technician=tech)
        assert doc.validation_status == PENDING

    def test_nuovo_mezzo_entra_in_attesa_di_validazione(self, client):
        user = _login_subappaltatore(client)

        client.post(
            reverse("portal:my-equipment-new"),
            data={
                "equipment_type": "Furgone",
                "plate": "AB123CD",
                "serial_code": "",
                "instrument": "",
            },
        )

        equipment = Equipment.objects.get(plate="AB123CD")
        assert equipment.vendor == user.vendor
        assert equipment.validation_status == PENDING
