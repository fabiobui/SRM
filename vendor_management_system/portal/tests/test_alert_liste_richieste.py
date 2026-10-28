"""Feedback dei fornitori sul portale: liste obbligatori/facoltativi, date
servizi facoltative, separazione richieste anagrafica/servizi."""

import pytest
from django.urls import reverse

from vendor_management_system.portal.forms import VendorServiceAddRequestForm
from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import (
    DocumentFactory,
    VendorCompetenceFactory,
    VendorServiceFactory,
    VendorUserFactory,
)

PASSWORD = "test-pass-1234"


@pytest.fixture
def vendor(client):
    user = VendorUserFactory(password=PASSWORD)
    client.login(email=user.email, password=PASSWORD)
    return user.vendor


@pytest.mark.django_db
class TestListeObbligatoriFacoltativi:
    def test_documenti_da_caricare_divisi_per_obbligatorieta(
        self, client, vendor
    ):
        DocumentFactory(
            vendor=vendor, status="PENDING", document_type__is_required=True
        )
        DocumentFactory(
            vendor=vendor, status="PENDING", document_type__is_required=False
        )

        response = client.get(reverse("portal:my-documents"))

        groups = response.context["pending_groups"]
        assert [g["mandatory"] for g in groups] == [True, False]
        html = response.content.decode()
        assert "Obbligatori da caricare" in html
        assert "Facoltativi da caricare" in html

    def test_requisiti_da_caricare_divisi_per_obbligatorieta(
        self, client, vendor
    ):
        VendorCompetenceFactory(
            vendor=vendor, document_file="", competence__is_mandatory=False
        )

        response = client.get(reverse("portal:my-requirements"))

        groups = response.context["pending_groups"]
        assert [g["mandatory"] for g in groups] == [False]
        assert "Obbligatori da caricare" not in response.content.decode()


@pytest.mark.django_db
class TestDateServiziFacoltative:
    def test_date_erogazione_facoltative_con_testo_evidente(self, vendor):
        form = VendorServiceAddRequestForm(vendor)

        for name in ("start_date", "end_date"):
            assert form.fields[name].required is False
            assert "facoltativo" in str(form.fields[name].label).lower()
            assert form.fields[name].help_text


@pytest.mark.django_db
class TestSeparazioneRichieste:
    def test_aggiunta_servizio_pendente_non_blocca_richiesta_anagrafica(
        self, client, vendor
    ):
        VendorChangeRequest.objects.create(
            vendor=vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
            changes={},
        )

        response = client.get(reverse("portal:my-profile-change"))

        assert response.status_code == 200

    def test_eliminazione_approvata_conta_tra_i_servizi(self, client, vendor):
        VendorChangeRequest.objects.create(
            vendor=vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE,
            status=VendorChangeRequest.STATUS_APPROVED,
            changes={},
        )
        VendorChangeRequest.objects.create(vendor=vendor, changes={})

        response = client.get(reverse("portal:dashboard"))

        assert response.context["servizi_stats"]["approved"] == 1
        assert response.context["anagrafica_stats"]["approved"] == 0
        assert response.context["anagrafica_stats"]["pending"] == 1

    def test_storico_fornitore_filtra_per_tipo(self, client, vendor):
        service = VendorServiceFactory(vendor=vendor)
        VendorChangeRequest.objects.create(vendor=vendor, changes={})
        VendorChangeRequest.objects.create(
            vendor=vendor, vendor_service=service, changes={}
        )
        url = reverse("portal:my-change-requests")

        anagrafica = client.get(url).context["requests"]
        servizi = client.get(url, {"tipo": "servizi"}).context["requests"]

        assert [r.vendor_service for r in anagrafica] == [None]
        assert [r.vendor_service for r in servizi] == [service]


@pytest.mark.django_db
class TestRicaricaDocumentoApprovatoInScadenza:
    """Un documento approvato e in scadenza si può ricaricare: la nuova
    versione resta in attesa di revisione senza errori."""

    def _documento(self, vendor):
        from datetime import date, timedelta

        from django.core.files.uploadedfile import SimpleUploadedFile

        return DocumentFactory(
            vendor=vendor,
            status="APPROVED",
            file=SimpleUploadedFile("old.pdf", b"%PDF-1.4 old"),
            expiry_date=date.today() + timedelta(days=5),
            document_type__requires_renewal=True,
            document_type__validity_period_days=365,
            document_type__reminder_days_before=30,
        )

    def test_portale_upload_su_documento_in_scadenza(self, client, vendor):
        from django.core.files.uploadedfile import SimpleUploadedFile

        document = self._documento(vendor)

        response = client.post(
            reverse("portal:my-document-upload", kwargs={"pk": document.pk}),
            {
                "file": SimpleUploadedFile("new.pdf", b"%PDF-1.4 new"),
                "expiry_date": "2027-12-31",
            },
            follow=True,
        )

        assert response.status_code == 200
        document.refresh_from_db()
        assert document.status == "APPROVED"
        assert document.pending_file

    def test_upload_legacy_su_documento_in_scadenza(self, client, vendor):
        from django.core.files.uploadedfile import SimpleUploadedFile

        document = self._documento(vendor)

        response = client.post(
            reverse("document-upload"),
            {
                "document_type": document.document_type_id,
                "file": SimpleUploadedFile("new.pdf", b"%PDF-1.4 new"),
                "expiry_date": "2027-12-31",
            },
            follow=True,
        )

        messages = [str(m) for m in response.context["messages"]]
        assert not any("Errore" in m for m in messages), messages
        document.refresh_from_db()
        assert document.pending_file

    def test_upload_legacy_nuovo_documento_con_date(self, client, vendor):
        from django.core.files.uploadedfile import SimpleUploadedFile

        tipo = DocumentFactory(vendor=vendor).document_type
        Document = type(DocumentFactory(vendor=vendor))
        Document.objects.filter(vendor=vendor, document_type=tipo).delete()

        response = client.post(
            reverse("document-upload"),
            {
                "document_type": tipo.pk,
                "file": SimpleUploadedFile("n.pdf", b"%PDF-1.4"),
                "expiry_date": "2027-12-31",
            },
            follow=True,
        )

        messages = [str(m) for m in response.context["messages"]]
        assert not any("Errore" in m for m in messages), messages
        assert (
            Document.objects.get(
                vendor=vendor, document_type=tipo
            ).expiry_date.isoformat()
            == "2027-12-31"
        )

    def test_upload_legacy_senza_file_non_perde_quello_esistente(
        self, client, vendor
    ):
        document = self._documento(vendor)

        client.post(
            reverse("document-upload"),
            {"document_type": document.document_type_id},
            follow=True,
        )

        document.refresh_from_db()
        assert document.file
