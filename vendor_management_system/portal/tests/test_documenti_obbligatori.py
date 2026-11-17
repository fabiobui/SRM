"""Documenti obbligatori di tecnici e mezzi: elencati nel dettaglio, caricati
da lì; il form di aggiunta propone solo i facoltativi."""

from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.portal.tests.factories import VendorUserFactory
from vendor_management_system.subcontractors.models import (
    EQUIPMENT_REQUIRED_DOCS,
    PENDING,
    TECHNICIAN_REQUIRED_DOCS,
    Equipment,
    EquipmentDocument,
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


def _pdf():
    return SimpleUploadedFile("a.pdf", b"x")


@pytest.mark.django_db
class TestDocumentiObbligatoriTecnico:
    def test_dettaglio_elenca_tutti_gli_obbligatori_come_mancanti(
        self, client
    ):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor, surname="Rossi", first_name="Mario"
        )

        response = client.get(
            reverse("portal:my-technician-detail", args=[tech.pk])
        )

        rows = response.context["required_rows"]
        assert [row["doc"] for row in rows] == [None] * len(
            TECHNICIAN_REQUIRED_DOCS
        )
        assert all("?tipo=" in row["upload_url"] for row in rows)

    def test_form_facoltativo_non_propone_gli_obbligatori(self, client):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor, surname="Rossi", first_name="Mario"
        )

        response = client.get(
            reverse("portal:my-technician-document-add", args=[tech.pk])
        )

        offered = {
            value
            for value, _ in response.context["form"].fields["doc_type"].choices
        }
        assert offered.isdisjoint(TECHNICIAN_REQUIRED_DOCS)
        assert "antincendio" in offered

    def test_form_facoltativo_rifiuta_un_tipo_obbligatorio(self, client):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor, surname="Rossi", first_name="Mario"
        )

        client.post(
            reverse("portal:my-technician-document-add", args=[tech.pk]),
            data={
                "doc_type": "patente",
                "expiry_date": "2027-06-30",
                "file": _pdf(),
            },
        )

        assert not TechnicianDocument.objects.filter(technician=tech).exists()

    def test_upload_obbligatorio_con_tipo_fisso(self, client):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor, surname="Rossi", first_name="Mario"
        )
        url = reverse("portal:my-technician-document-add", args=[tech.pk])

        page = client.get(url + "?tipo=patente")
        offered = [
            value
            for value, _ in page.context["form"].fields["doc_type"].choices
        ]
        assert offered == ["patente"]

        client.post(
            url + "?tipo=patente",
            data={
                "doc_type": "patente",
                "expiry_date": "2027-06-30",
                "file": _pdf(),
            },
        )

        doc = TechnicianDocument.objects.get(technician=tech)
        assert doc.doc_type == "patente"
        assert doc.validation_status == PENDING

    def test_tipo_fisso_rifiuta_un_altro_tipo(self, client):
        user = _login_subappaltatore(client)
        tech = Technician.objects.create(
            vendor=user.vendor, surname="Rossi", first_name="Mario"
        )

        client.post(
            reverse("portal:my-technician-document-add", args=[tech.pk])
            + "?tipo=patente",
            data={
                "doc_type": "antincendio",
                "expiry_date": "2027-06-30",
                "file": _pdf(),
            },
        )

        assert not TechnicianDocument.objects.filter(technician=tech).exists()


@pytest.mark.django_db
class TestDocumentiObbligatoriMezzo:
    def test_dettaglio_mostra_stato_dell_ultimo_documento_obbligatorio(
        self, client
    ):
        user = _login_subappaltatore(client)
        equipment = Equipment.objects.create(
            vendor=user.vendor, equipment_type="Furgone", plate="AB123CD"
        )
        EquipmentDocument.objects.create(
            equipment=equipment,
            doc_type="libretto",
            file=_pdf(),
            validation_status="REJECTED",
            rejection_note="Foto illeggibile",
        )

        response = client.get(
            reverse("portal:my-equipment-detail", args=[equipment.pk])
        )

        docs_by_label = {
            row["label"]: row["doc"]
            for row in response.context["required_rows"]
        }
        assert docs_by_label["Libretto"].validation_status == "REJECTED"
        assert docs_by_label["Assicurazione"] is None

    def test_form_facoltativo_non_propone_il_libretto(self, client):
        user = _login_subappaltatore(client)
        equipment = Equipment.objects.create(
            vendor=user.vendor, equipment_type="Furgone", plate="AB123CD"
        )

        response = client.get(
            reverse("portal:my-equipment-document-add", args=[equipment.pk])
        )

        offered = {
            value
            for value, _ in response.context["form"].fields["doc_type"].choices
        }
        assert offered.isdisjoint(EQUIPMENT_REQUIRED_DOCS)
        assert "leasing" in offered

    def test_upload_obbligatorio_con_tipo_fisso(self, client):
        user = _login_subappaltatore(client)
        equipment = Equipment.objects.create(
            vendor=user.vendor, equipment_type="Furgone", plate="AB123CD"
        )
        url = reverse("portal:my-equipment-document-add", args=[equipment.pk])

        client.post(
            url + "?tipo=assicurazione",
            data={
                "doc_type": "assicurazione",
                "expiry_date": "2027-06-30",
                "file": _pdf(),
            },
        )

        doc = EquipmentDocument.objects.get(equipment=equipment)
        assert doc.doc_type == "assicurazione"
        assert doc.expiry_date == date(2027, 6, 30)
