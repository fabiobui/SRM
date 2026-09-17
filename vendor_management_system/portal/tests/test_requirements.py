"""Test del flusso "I miei requisiti professionali" del portale fornitore.

Le `VendorCompetence` sono pre-assegnate dal back-office: il fornitore può
solo caricare/aggiornare il file dell'attestato sui record già esistenti
per il proprio vendor.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.portal.tests.factories import (
    VendorCompetenceFactory,
    VendorUserFactory,
)

PASSWORD = "test-pass-1234"


@pytest.mark.django_db
class TestMyRequirementUpload:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_upload_attaches_file_and_resets_verification(self, client):
        user = self._login(client)
        requirement = VendorCompetenceFactory(
            vendor=user.vendor, verified=True
        )
        file_ = SimpleUploadedFile(
            "attestato.pdf", b"contenuto", "application/pdf"
        )

        response = client.post(
            reverse(
                "portal:my-requirement-upload",
                kwargs={"pk": requirement.pk},
            ),
            data={"document_file": file_},
        )

        requirement.refresh_from_db()
        assert response.status_code == 302
        assert requirement.document_file
        assert requirement.verified is False

    def test_upload_without_file_is_rejected(self, client):
        user = self._login(client)
        requirement = VendorCompetenceFactory(vendor=user.vendor)

        response = client.post(
            reverse(
                "portal:my-requirement-upload",
                kwargs={"pk": requirement.pk},
            ),
            data={},
        )

        requirement.refresh_from_db()
        assert response.status_code == 302
        assert not requirement.document_file

    def test_my_requirements_list_only_shows_own_vendor(self, client):
        user = self._login(client)
        own_requirement = VendorCompetenceFactory(vendor=user.vendor)
        VendorCompetenceFactory()  # requisito di un altro vendor

        response = client.get(reverse("portal:my-requirements"))

        requirements = list(response.context["requirements"])
        assert requirements == [own_requirement]
