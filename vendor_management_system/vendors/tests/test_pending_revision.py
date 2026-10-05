"""Revisione in attesa di documenti e requisiti già approvati.

Se il fornitore ricarica in anticipo un documento/requisito ancora valido, la
nuova versione resta "in attesa" (una sola per record) e il record approvato
non cambia finché l'ufficio non approva; solo allora file e date vengono
sostituiti. Se invece il record non è valido (mancante, non approvato,
scaduto) l'upload lo sostituisce subito, come prima.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    DocumentFactory,
    VendorCompetenceFactory,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db

User = get_user_model()
OGGI = timezone.now().date()
IERI = OGGI - timedelta(days=1)
TRA_UN_MESE = OGGI + timedelta(days=30)
TRA_UN_ANNO = OGGI + timedelta(days=365)


def _file(name="nuovo.pdf"):
    return SimpleUploadedFile(name, b"contenuto", "application/pdf")


def _doc_approvato(**extra):
    campi = {
        "status": "APPROVED",
        "file": "vendor_documents/vecchio.pdf",
        "expiry_date": TRA_UN_MESE,
    }
    campi.update(extra)
    return DocumentFactory(**campi)


def _req_verificato(**extra):
    campi = {
        "verified": True,
        "document_file": "vendor_competences/vecchio.pdf",
        "expiry_date": TRA_UN_MESE,
    }
    campi.update(extra)
    return VendorCompetenceFactory(**campi)


class TestDocumentoSubmitUpload:
    def test_documento_approvato_e_valido_mette_la_nuova_versione_in_attesa(
        self,
    ):
        doc = _doc_approvato()

        staged = doc.submit_upload(
            file=_file(), expiry_date=TRA_UN_ANNO, notes="rinnovo"
        )

        doc.refresh_from_db()
        assert staged is True
        assert doc.file.name == "vendor_documents/vecchio.pdf"
        assert doc.expiry_date == TRA_UN_MESE
        assert doc.status == "APPROVED"
        assert doc.has_pending_revision
        assert doc.pending_expiry_date == TRA_UN_ANNO
        assert doc.pending_notes == "rinnovo"
        assert doc.pending_uploaded_at is not None

    @pytest.mark.parametrize("status", ["UPLOADED", "REJECTED", "PENDING"])
    def test_documento_non_approvato_viene_sostituito_subito(self, status):
        doc = DocumentFactory(
            status=status, file="vendor_documents/vecchio.pdf"
        )

        staged = doc.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)

        doc.refresh_from_db()
        assert staged is False
        assert doc.status == "UPLOADED"
        assert doc.expiry_date == TRA_UN_ANNO
        assert not doc.has_pending_revision

    def test_documento_scaduto_viene_sostituito_subito(self):
        doc = _doc_approvato(expiry_date=IERI)

        staged = doc.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)

        doc.refresh_from_db()
        assert staged is False
        assert doc.status == "UPLOADED"
        assert not doc.has_pending_revision

    def test_un_nuovo_upload_sostituisce_la_revisione_in_attesa(self):
        doc = _doc_approvato()
        doc.submit_upload(file=_file("a.pdf"), expiry_date=TRA_UN_ANNO)

        doc.submit_upload(file=_file("b.pdf"), expiry_date=TRA_UN_MESE)

        doc.refresh_from_db()
        assert "b" in doc.pending_file.name
        assert doc.pending_expiry_date == TRA_UN_MESE

    def test_applicare_la_revisione_sostituisce_file_e_date(self):
        doc = _doc_approvato()
        doc.submit_upload(
            file=_file(), issue_date=OGGI, expiry_date=TRA_UN_ANNO, notes="n"
        )

        doc.apply_pending_revision()

        doc.refresh_from_db()
        assert "nuovo" in doc.file.name
        assert doc.issue_date == OGGI
        assert doc.expiry_date == TRA_UN_ANNO
        assert doc.notes == "n"
        assert not doc.has_pending_revision
        assert doc.pending_expiry_date is None

    def test_scartare_la_revisione_lascia_il_record_com_e(self):
        doc = _doc_approvato()
        doc.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)

        doc.discard_pending_revision()

        doc.refresh_from_db()
        assert doc.file.name == "vendor_documents/vecchio.pdf"
        assert doc.expiry_date == TRA_UN_MESE
        assert doc.status == "APPROVED"
        assert not doc.has_pending_revision

    def test_il_fornitore_approvato_resta_approvato(self):
        vendor = VendorFactory()
        doc = _doc_approvato(vendor=vendor)
        vendor.qualification_status = "APPROVED"
        vendor.save()

        doc.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)

        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"


class TestRequisitoSubmitUpload:
    def test_requisito_verificato_e_valido_mette_la_nuova_versione_in_attesa(
        self,
    ):
        req = _req_verificato()

        staged = req.submit_upload(
            document_file=_file(),
            certification_number="N-2",
            expiry_date=TRA_UN_ANNO,
            notes="rinnovo",
        )

        req.refresh_from_db()
        assert staged is True
        assert req.document_file.name == "vendor_competences/vecchio.pdf"
        assert req.expiry_date == TRA_UN_MESE
        assert req.verified is True
        assert req.has_pending_revision
        assert req.pending_certification_number == "N-2"
        assert req.pending_expiry_date == TRA_UN_ANNO

    def test_requisito_non_verificato_viene_sostituito_subito(self):
        req = _req_verificato(verified=False)

        staged = req.submit_upload(
            document_file=_file(), expiry_date=TRA_UN_ANNO
        )

        req.refresh_from_db()
        assert staged is False
        assert req.verified is False
        assert req.expiry_date == TRA_UN_ANNO
        assert not req.has_pending_revision

    def test_requisito_scaduto_viene_sostituito_subito(self):
        req = _req_verificato(expiry_date=IERI)

        staged = req.submit_upload(
            document_file=_file(), expiry_date=TRA_UN_ANNO
        )

        req.refresh_from_db()
        assert staged is False
        assert req.verified is False
        assert "nuovo" in req.document_file.name

    def test_applicare_e_scartare(self):
        req = _req_verificato()
        req.submit_upload(
            document_file=_file(),
            certification_number="N-2",
            expiry_date=TRA_UN_ANNO,
        )

        req.apply_pending_revision()
        req.refresh_from_db()
        assert "nuovo" in req.document_file.name
        assert req.certification_number == "N-2"
        assert req.expiry_date == TRA_UN_ANNO
        assert not req.has_pending_revision

        req.submit_upload(document_file=_file("x.pdf"), expiry_date=OGGI)
        req.discard_pending_revision()
        req.refresh_from_db()
        assert req.expiry_date == TRA_UN_ANNO
        assert not req.has_pending_revision


def _login_bo(client):
    user = User.objects.create_user(
        email="bo-pending@example.invalid", password="x", role="bo_user"
    )
    client.login(email=user.email, password="x")
    return user


class TestRevisioneBackOffice:
    def test_approvando_si_applica_la_revisione_del_documento(self, client):
        bo = _login_bo(client)
        doc = _doc_approvato()
        doc.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)

        client.post(
            reverse("portal:bo-document-review", kwargs={"pk": doc.pk}),
            {"action": "approve"},
        )

        doc.refresh_from_db()
        assert "nuovo" in doc.file.name
        assert doc.expiry_date == TRA_UN_ANNO
        assert doc.status == "APPROVED"
        assert doc.reviewed_by.email == bo.email
        assert not doc.has_pending_revision

    def test_rifiutando_il_documento_approvato_resta_in_vigore(self, client):
        _login_bo(client)
        doc = _doc_approvato()
        doc.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)

        client.post(
            reverse("portal:bo-document-review", kwargs={"pk": doc.pk}),
            {"action": "reject"},
        )

        doc.refresh_from_db()
        assert doc.file.name == "vendor_documents/vecchio.pdf"
        assert doc.expiry_date == TRA_UN_MESE
        assert doc.status == "APPROVED"
        assert not doc.has_pending_revision

    def test_la_lista_documenti_mostra_quelli_con_revisione_in_attesa(
        self, client
    ):
        _login_bo(client)
        con_revisione = _doc_approvato()
        con_revisione.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)
        senza_revisione = _doc_approvato()

        response = client.get(reverse("portal:bo-documents"))

        documenti = list(response.context["documents"])
        assert con_revisione in documenti
        assert senza_revisione not in documenti

    def test_approvando_si_applica_la_revisione_del_requisito(self, client):
        _login_bo(client)
        req = _req_verificato(competence=CompetenceFactory())
        req.submit_upload(document_file=_file(), expiry_date=TRA_UN_ANNO)

        client.post(
            reverse("portal:bo-requirement-review", kwargs={"pk": req.pk}),
            {"action": "approve"},
        )

        req.refresh_from_db()
        assert "nuovo" in req.document_file.name
        assert req.expiry_date == TRA_UN_ANNO
        assert req.verified is True
        assert not req.has_pending_revision

    def test_rifiutando_il_requisito_verificato_resta_in_vigore(self, client):
        _login_bo(client)
        req = _req_verificato()
        req.submit_upload(document_file=_file(), expiry_date=TRA_UN_ANNO)

        client.post(
            reverse("portal:bo-requirement-review", kwargs={"pk": req.pk}),
            {"action": "reject"},
        )

        req.refresh_from_db()
        assert req.document_file.name == "vendor_competences/vecchio.pdf"
        assert req.expiry_date == TRA_UN_MESE
        assert req.verified is True
        assert not req.has_pending_revision

    def test_la_lista_requisiti_mostra_quelli_con_revisione_in_attesa(
        self, client
    ):
        _login_bo(client)
        con_revisione = _req_verificato()
        con_revisione.submit_upload(
            document_file=_file(), expiry_date=TRA_UN_ANNO
        )
        senza_revisione = _req_verificato()

        response = client.get(reverse("portal:bo-requirements"))

        requisiti = list(response.context["requirements"])
        assert con_revisione in requisiti
        assert senza_revisione not in requisiti

    def test_le_liste_segnalano_la_nuova_versione_in_attesa(self, client):
        _login_bo(client)
        doc = _doc_approvato()
        doc.submit_upload(file=_file(), expiry_date=TRA_UN_ANNO)
        req = _req_verificato()
        req.submit_upload(document_file=_file(), expiry_date=TRA_UN_ANNO)

        documenti = client.get(reverse("portal:bo-documents"))
        requisiti = client.get(reverse("portal:bo-requirements"))

        assert "Nuova versione" in documenti.content.decode()
        assert "Nuova versione" in requisiti.content.decode()
