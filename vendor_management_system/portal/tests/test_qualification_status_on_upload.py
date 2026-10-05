"""Effetto del caricamento del fornitore sullo stato di qualifica.

Un fornitore "Approvato" non cambia con un upload anticipato (la nuova
versione resta in attesa di revisione); uno "In attesa"/"Respinto" passa a
"Da revisionare" quando ha consegnato tutti gli obbligatori mancanti o
scaduti. I facoltativi non incidono mai sullo stato.
"""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    DocumentCatalogFactory,
    DocumentFactory,
    VendorCompetenceFactory,
    VendorUserFactory,
)
from vendor_management_system.vendors.models import Vendor

PASSWORD = "test-pass-1234"
IERI = timezone.now().date() - timedelta(days=1)


def _file(name="doc.pdf"):
    return SimpleUploadedFile(name, b"contenuto", "application/pdf")


def _upload_documento(client, document, **extra):
    return client.post(
        reverse("portal:my-document-upload", kwargs={"pk": document.pk}),
        data={"file": _file(), **extra},
    )


def _upload_requisito(client, requirement):
    return client.post(
        reverse("portal:my-requirement-upload", kwargs={"pk": requirement.pk}),
        data={"document_file": _file()},
    )


@pytest.fixture
def user(client):
    user = VendorUserFactory(password=PASSWORD)
    client.login(email=user.email, password=PASSWORD)
    return user


def _stato(user):
    user.vendor.refresh_from_db()
    return user.vendor.qualification_status


def _imposta(user, stato):
    Vendor.objects.filter(pk=user.vendor.pk).update(qualification_status=stato)


@pytest.mark.django_db
class TestUploadDocumento:
    @pytest.mark.parametrize("partenza", ["PENDING", "REJECTED"])
    def test_ultimo_obbligatorio_mancante_porta_a_da_revisionare(
        self, client, user, partenza
    ):
        _imposta(user, partenza)
        document = DocumentFactory(vendor=user.vendor)

        _upload_documento(client, document)

        assert _stato(user) == "TO_REVIEW"

    def test_restano_obbligatori_mancanti_lo_stato_non_cambia(
        self, client, user
    ):
        _imposta(user, "REJECTED")
        document = DocumentFactory(vendor=user.vendor)
        DocumentFactory(vendor=user.vendor)  # secondo obbligatorio, vuoto

        _upload_documento(client, document)

        assert _stato(user) == "REJECTED"

    def test_obbligatorio_scaduto_ricaricato_ma_ancora_scaduto_non_cambia(
        self, client, user
    ):
        _imposta(user, "REJECTED")
        document = DocumentFactory(
            vendor=user.vendor, file="a.pdf", expiry_date=IERI
        )

        _upload_documento(client, document, expiry_date=IERI.isoformat())

        assert _stato(user) == "REJECTED"

    def test_obbligatorio_scaduto_con_nuova_scadenza_va_in_revisione(
        self, client, user
    ):
        _imposta(user, "REJECTED")
        document = DocumentFactory(
            vendor=user.vendor, file="a.pdf", expiry_date=IERI
        )
        futura = (timezone.now().date() + timedelta(days=365)).isoformat()

        _upload_documento(client, document, expiry_date=futura)

        assert _stato(user) == "TO_REVIEW"

    def test_documento_facoltativo_non_cambia_lo_stato(self, client, user):
        _imposta(user, "REJECTED")
        document = DocumentFactory(
            vendor=user.vendor,
            document_type=DocumentCatalogFactory(is_required=False),
        )

        _upload_documento(client, document)

        assert _stato(user) == "REJECTED"

    def test_fornitore_approvato_resta_approvato(self, client, user):
        _imposta(user, "APPROVED")
        document = DocumentFactory(
            vendor=user.vendor, status="APPROVED", file="a.pdf"
        )

        _upload_documento(client, document)

        document.refresh_from_db()
        assert _stato(user) == "APPROVED"
        # La nuova versione attende la revisione: il record non cambia.
        assert document.file.name == "a.pdf"
        assert document.status == "APPROVED"
        assert document.has_pending_revision

    def test_facoltativo_approvato_ricaricato_va_in_revisione_in_attesa(
        self, client, user
    ):
        _imposta(user, "APPROVED")
        document = DocumentFactory(
            vendor=user.vendor,
            document_type=DocumentCatalogFactory(is_required=False),
            status="APPROVED",
            file="a.pdf",
        )

        _upload_documento(client, document)

        document.refresh_from_db()
        assert _stato(user) == "APPROVED"
        assert document.file.name == "a.pdf"
        assert document.has_pending_revision

    def test_aggiunta_di_documento_obbligatorio_da_in_attesa(
        self, client, user
    ):
        doc_type = DocumentCatalogFactory(is_required=True)

        client.post(
            reverse("portal:my-document-add"),
            {"document_type": doc_type.pk, "file": _file()},
        )

        assert _stato(user) == "TO_REVIEW"

    def test_aggiunta_di_documento_facoltativo_non_cambia_lo_stato(
        self, client, user
    ):
        doc_type = DocumentCatalogFactory(is_required=False)

        client.post(
            reverse("portal:my-document-add"),
            {"document_type": doc_type.pk, "file": _file()},
        )

        assert _stato(user) == "PENDING"


@pytest.mark.django_db
class TestUploadRequisito:
    @pytest.mark.parametrize("partenza", ["PENDING", "REJECTED"])
    def test_ultimo_obbligatorio_mancante_porta_a_da_revisionare(
        self, client, user, partenza
    ):
        _imposta(user, partenza)
        requirement = VendorCompetenceFactory(
            vendor=user.vendor, competence=CompetenceFactory(is_mandatory=True)
        )

        _upload_requisito(client, requirement)

        assert _stato(user) == "TO_REVIEW"

    def test_requisito_facoltativo_non_cambia_lo_stato(self, client, user):
        _imposta(user, "REJECTED")
        requirement = VendorCompetenceFactory(
            vendor=user.vendor,
            competence=CompetenceFactory(is_mandatory=False),
        )

        _upload_requisito(client, requirement)

        assert _stato(user) == "REJECTED"

    def test_aggiunta_di_requisito_obbligatorio_da_in_attesa(
        self, client, user
    ):
        competence = CompetenceFactory(is_mandatory=True)

        client.post(
            reverse("portal:my-requirement-add"),
            {"competence": competence.pk, "document_file": _file()},
        )

        assert _stato(user) == "TO_REVIEW"

    def test_fornitore_approvato_resta_approvato(self, client, user):
        _imposta(user, "APPROVED")
        requirement = VendorCompetenceFactory(
            vendor=user.vendor,
            competence=CompetenceFactory(is_mandatory=True),
            document_file="a.pdf",
            verified=True,
        )

        _upload_requisito(client, requirement)

        requirement.refresh_from_db()
        assert _stato(user) == "APPROVED"
        assert requirement.document_file.name == "a.pdf"
        assert requirement.verified is True
        assert requirement.has_pending_revision


@pytest.mark.django_db
class TestAvvisoRevisioneInAttesa:
    def test_il_dettaglio_documento_avvisa_della_nuova_versione(
        self, client, user
    ):
        document = DocumentFactory(
            vendor=user.vendor, status="APPROVED", file="a.pdf"
        )
        _upload_documento(client, document)

        response = client.get(
            reverse("portal:my-document-detail", kwargs={"pk": document.pk})
        )

        assert "in attesa di revisione" in response.content.decode()

    def test_il_dettaglio_requisito_avvisa_della_nuova_versione(
        self, client, user
    ):
        requirement = VendorCompetenceFactory(
            vendor=user.vendor,
            competence=CompetenceFactory(is_mandatory=True),
            document_file="a.pdf",
            verified=True,
        )
        _upload_requisito(client, requirement)

        response = client.get(
            reverse(
                "portal:my-requirement-detail", kwargs={"pk": requirement.pk}
            )
        )

        assert "in attesa di verifica" in response.content.decode()
