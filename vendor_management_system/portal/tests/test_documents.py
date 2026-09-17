"""Test del flusso "I miei documenti" del portale fornitore.

I `Document` sono pre-creati dal back-office (status PENDING, file vuoto):
il fornitore può solo caricare/aggiornare il file sui record già esistenti
per il proprio vendor (mai crearne di nuovi tipi).
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.portal.tests.factories import (
    DocumentFactory,
    VendorUserFactory,
)

PASSWORD = "test-pass-1234"


@pytest.mark.django_db
class TestMyDocumentUpload:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_upload_marks_document_uploaded(self, client):
        user = self._login(client)
        document = DocumentFactory(vendor=user.vendor, status="PENDING")
        file_ = SimpleUploadedFile("durc.pdf", b"contenuto", "application/pdf")

        response = client.post(
            reverse("portal:my-document-upload", kwargs={"pk": document.pk}),
            data={"file": file_},
        )

        document.refresh_from_db()
        assert response.status_code == 302
        assert document.status == "UPLOADED"
        assert document.file

    def test_reupload_resets_previous_review(self, client):
        user = self._login(client)
        reviewer = VendorUserFactory(password=PASSWORD)
        document = DocumentFactory(
            vendor=user.vendor,
            status="REJECTED",
            reviewed_by=reviewer,
        )
        file_ = SimpleUploadedFile("durc.pdf", b"contenuto", "application/pdf")

        client.post(
            reverse("portal:my-document-upload", kwargs={"pk": document.pk}),
            data={"file": file_},
        )

        document.refresh_from_db()
        assert document.status == "UPLOADED"
        assert document.reviewed_by is None
        assert document.reviewed_at is None

    def test_upload_without_file_is_rejected(self, client):
        user = self._login(client)
        document = DocumentFactory(vendor=user.vendor, status="PENDING")

        response = client.post(
            reverse("portal:my-document-upload", kwargs={"pk": document.pk}),
            data={},
        )

        document.refresh_from_db()
        assert response.status_code == 302
        assert document.status == "PENDING"

    def test_my_documents_list_only_shows_own_vendor(self, client):
        user = self._login(client)
        own_document = DocumentFactory(vendor=user.vendor)
        DocumentFactory()  # documento di un altro vendor

        response = client.get(reverse("portal:my-documents"))

        documents = list(response.context["documents"])
        assert documents == [own_document]
