"""Portale e revisione back office con le sezioni del fornitore.

Portale "vista unica": ogni elemento mostra la sua società (o Comune) e i
caricamenti nuovi prendono la sezione dal catalogo; se il fornitore lavora
con più società la sezione la assegna il back office. Il BO rivede solo la
Comune e la propria società.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.documents.models import Document
from vendor_management_system.portal.tests.factories import (
    DocumentCatalogFactory,
    DocumentFactory,
    VendorUserFactory,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import VendorCompany

pytestmark = pytest.mark.django_db
PASSWORD = "test-pass-1234"


def _file():
    return SimpleUploadedFile("doc.pdf", b"contenuto", "application/pdf")


@pytest.fixture
def vendor_user(client):
    user = VendorUserFactory(password=PASSWORD)
    client.login(email=user.email, password=PASSWORD)
    return user


class TestCaricamentoDalPortale:
    url = reverse("portal:my-document-add")

    def test_tipo_comune_va_in_comune(self, client, vendor_user):
        VendorCompany.objects.create(
            vendor=vendor_user.vendor, company_id="SICURA"
        )
        doc_type = DocumentCatalogFactory(scope="COMMON")
        client.post(self.url, {"document_type": doc_type.pk, "file": _file()})
        document = Document.objects.get(vendor=vendor_user.vendor)
        assert (document.company_id, document.section_confirmed) == (
            "COMUNE",
            True,
        )

    def test_unica_societa(self, client, vendor_user):
        VendorCompany.objects.create(
            vendor=vendor_user.vendor, company_id="SICURA"
        )
        doc_type = DocumentCatalogFactory(scope="COMPANY")
        client.post(self.url, {"document_type": doc_type.pk, "file": _file()})
        document = Document.objects.get(vendor=vendor_user.vendor)
        assert document.company_id == "SICURA"

    def test_piu_societa_sezione_da_assegnare(self, client, vendor_user):
        for code in ("SICURA", "EVIMED"):
            VendorCompany.objects.create(
                vendor=vendor_user.vendor, company_id=code
            )
        doc_type = DocumentCatalogFactory(scope="COMPANY")
        client.post(self.url, {"document_type": doc_type.pk, "file": _file()})
        document = Document.objects.get(vendor=vendor_user.vendor)
        assert (document.company_id, document.section_confirmed) == (
            "COMUNE",
            False,
        )

    def test_lista_mostra_la_societa(self, client, vendor_user):
        VendorCompany.objects.create(
            vendor=vendor_user.vendor, company_id="SICURA"
        )
        DocumentFactory(vendor=vendor_user.vendor, company_id="SICURA")
        html = client.get(reverse("portal:my-documents")).content.decode()
        assert "section-label" in html
        assert "Sicura" in html


@pytest.fixture
def shared_document():
    user = VendorUserFactory(password=PASSWORD)
    vendor = user.vendor
    for code in ("SICURA", "IGEAM"):
        VendorCompany.objects.create(vendor=vendor, company_id=code)
    return DocumentFactory(
        vendor=vendor, company_id="SICURA", status="UPLOADED", file="a.pdf"
    )


def _bo(client, company):
    user = User.objects.create_user(
        email=f"bo-{company}@example.invalid",
        password=PASSWORD,
        role="bo_user",
        company_id=company,
    )
    client.force_login(user)
    return user


class TestRevisioneBackOffice:
    def test_bo_di_altra_societa_non_vede_ne_approva(
        self, client, shared_document
    ):
        _bo(client, "IGEAM")
        detail = reverse(
            "portal:bo-document-detail", kwargs={"pk": shared_document.pk}
        )
        review = reverse(
            "portal:bo-document-review", kwargs={"pk": shared_document.pk}
        )
        assert client.get(detail).status_code == 404
        assert client.post(review, {"action": "approve"}).status_code == 403
        listing = client.get(reverse("portal:bo-documents"))
        assert shared_document not in listing.context["documents"]
        shared_document.refresh_from_db()
        assert shared_document.status == "UPLOADED"

    def test_bo_della_societa_approva_e_assegna_la_sezione(
        self, client, shared_document
    ):
        _bo(client, "SICURA")
        review = reverse(
            "portal:bo-document-review", kwargs={"pk": shared_document.pk}
        )
        client.post(review, {"action": "approve", "company": "COMUNE"})
        shared_document.refresh_from_db()
        assert shared_document.status == "APPROVED"
        assert shared_document.company_id == "COMUNE"
        assert shared_document.section_confirmed is True

    def test_assegnazione_a_sezione_non_ammessa_rifiutata(
        self, client, shared_document
    ):
        _bo(client, "SICURA")
        review = reverse(
            "portal:bo-document-review", kwargs={"pk": shared_document.pk}
        )
        client.post(review, {"action": "approve", "company": "IGEAM"})
        shared_document.refresh_from_db()
        assert shared_document.status == "UPLOADED"
        assert shared_document.company_id == "SICURA"
