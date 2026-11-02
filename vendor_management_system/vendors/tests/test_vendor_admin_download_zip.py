"""Test del download .zip delle sezioni "Documenti Contrattuali" e
"Abilitazioni e Requisiti Professionali" nella scheda Vendor in admin
(`VendorAdmin.download_zip_view`)."""

import io
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    DocumentCatalogFactory,
    DocumentFactory,
    VendorCompetenceFactory,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors.tests.factories import VendorFactory

PASSWORD = "test-pass-1234"


@pytest.fixture
def admin_client(client, db):
    superuser = User.objects.create_superuser(
        email="super-zip@example.invalid", password=PASSWORD, role="admin"
    )
    client.login(email=superuser.email, password=PASSWORD)
    return client


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def _zip_url(vendor, section):
    return reverse(
        "admin:vendors_vendor_download_zip", args=[vendor.pk, section]
    )


def _zip_names(response):
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        return archive.namelist()


@pytest.mark.django_db
def test_documenti_zip_contains_only_the_vendor_document_files(admin_client):
    vendor = VendorFactory()
    DocumentFactory(
        vendor=vendor,
        document_type=DocumentCatalogFactory(name="Visura camerale"),
        file=SimpleUploadedFile("visura.pdf", b"visura"),
    )
    DocumentFactory(
        vendor=vendor,
        document_type=DocumentCatalogFactory(name="DURC"),
        file=SimpleUploadedFile("durc.pdf", b"durc"),
    )
    altro_fornitore = VendorFactory()
    DocumentFactory(
        vendor=altro_fornitore,
        file=SimpleUploadedFile("altrui.pdf", b"altrui"),
    )

    response = admin_client.get(_zip_url(vendor, "documenti"))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert (
        f"{vendor.vendor_code}_documenti.zip"
        in response["Content-Disposition"]
    )
    names = _zip_names(response)
    assert len(names) == 2
    assert any(
        "Visura camerale" in n and n.endswith("visura.pdf") for n in names
    )
    assert any("DURC" in n and n.endswith("durc.pdf") for n in names)
    assert not any("altrui" in n for n in names)


@pytest.mark.django_db
def test_abilitazioni_zip_contains_only_the_competence_files(admin_client):
    vendor = VendorFactory()
    VendorCompetenceFactory(
        vendor=vendor,
        competence=CompetenceFactory(name="Patente ADR"),
        document_file=SimpleUploadedFile("adr.pdf", b"adr"),
    )
    VendorCompetenceFactory(vendor=vendor, competence=CompetenceFactory())

    response = admin_client.get(_zip_url(vendor, "abilitazioni"))

    assert response.status_code == 200
    names = _zip_names(response)
    assert len(names) == 1
    assert "Patente ADR" in names[0]
    assert names[0].endswith("adr.pdf")


@pytest.mark.django_db
def test_change_page_shows_zip_button_in_both_sections(admin_client):
    vendor = VendorFactory()

    response = admin_client.get(
        reverse("admin:vendors_vendor_change", args=[vendor.pk])
    )

    content = response.content.decode()
    assert _zip_url(vendor, "documenti") in content
    assert _zip_url(vendor, "abilitazioni") in content


@pytest.mark.django_db
def test_zip_is_not_produced_when_a_stored_file_is_missing(admin_client):
    vendor = VendorFactory()
    # Il record esiste ma il file non è nello storage
    DocumentFactory(vendor=vendor, file="documents/mancante.pdf")

    response = admin_client.get(_zip_url(vendor, "documenti"), follow=True)

    assert response.redirect_chain
    assert response.redirect_chain[-1][0].endswith(
        reverse("admin:vendors_vendor_change", args=[vendor.pk])
    )
    assert "Download non riuscito" in response.content.decode()
