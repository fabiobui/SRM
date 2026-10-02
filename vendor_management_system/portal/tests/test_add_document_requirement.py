"""Test dell'aggiunta autonoma di documenti e requisiti dal portale fornitore.

Il fornitore sceglie un tipo/requisito dal catalogo e carica subito il file:
il record nasce in attesa di verifica BO e non può duplicare o fuoriuscire
dal proprio vendor.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.documents.models import Document
from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    DocumentCatalogFactory,
    DocumentFactory,
    VendorCompetenceFactory,
    VendorUserFactory,
)
from vendor_management_system.vendors.models import VendorCompetence

PASSWORD = "test-pass-1234"


def _file(name="doc.pdf"):
    return SimpleUploadedFile(name, b"contenuto", "application/pdf")


@pytest.fixture
def user(client):
    user = VendorUserFactory(password=PASSWORD)
    client.login(email=user.email, password=PASSWORD)
    return user


@pytest.mark.django_db
class TestDocumentAdd:
    url = reverse("portal:my-document-add")

    def test_creates_uploaded_document(self, client, user):
        doc_type = DocumentCatalogFactory()

        response = client.post(
            self.url, {"document_type": doc_type.pk, "file": _file()}
        )

        document = Document.objects.get(vendor=user.vendor)
        assert response.status_code == 302
        assert document.document_type == doc_type
        assert document.status == "UPLOADED"
        assert document.file

    def test_already_present_type_is_rejected(self, client, user):
        document = DocumentFactory(vendor=user.vendor)

        response = client.post(
            self.url,
            {"document_type": document.document_type.pk, "file": _file()},
        )

        assert response.status_code == 200
        assert Document.objects.filter(vendor=user.vendor).count() == 1

    def test_inactive_type_is_rejected(self, client, user):
        doc_type = DocumentCatalogFactory(is_active=False)

        response = client.post(
            self.url, {"document_type": doc_type.pk, "file": _file()}
        )

        assert response.status_code == 200
        assert not Document.objects.filter(vendor=user.vendor).exists()

    def test_file_is_required(self, client, user):
        doc_type = DocumentCatalogFactory()

        response = client.post(self.url, {"document_type": doc_type.pk})

        assert response.status_code == 200
        assert not Document.objects.filter(vendor=user.vendor).exists()

    def test_anonymous_is_redirected(self, client):
        response = client.get(self.url)

        assert response.status_code == 302


@pytest.mark.django_db
class TestRequirementAdd:
    url = reverse("portal:my-requirement-add")

    def test_creates_unverified_requirement(self, client, user):
        competence = CompetenceFactory()

        response = client.post(
            self.url,
            {"competence": competence.pk, "document_file": _file()},
        )

        requirement = VendorCompetence.objects.get(vendor=user.vendor)
        assert response.status_code == 302
        assert requirement.competence == competence
        assert requirement.verified is False
        assert requirement.document_file

    def test_already_assigned_requirement_is_rejected(self, client, user):
        assigned = VendorCompetenceFactory(vendor=user.vendor)

        response = client.post(
            self.url,
            {"competence": assigned.competence.pk, "document_file": _file()},
        )

        assert response.status_code == 200
        assert VendorCompetence.objects.filter(vendor=user.vendor).count() == 1

    def test_inactive_requirement_is_rejected(self, client, user):
        competence = CompetenceFactory(is_active=False)

        response = client.post(
            self.url,
            {"competence": competence.pk, "document_file": _file()},
        )

        assert response.status_code == 200
        assert not VendorCompetence.objects.filter(vendor=user.vendor).exists()
