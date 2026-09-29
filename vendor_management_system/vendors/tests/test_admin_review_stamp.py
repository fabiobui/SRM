"""AIDEV-100: dall'admin, quando il gestore approva un documento o verifica un
requisito, revisore e data vengono compilati in automatico."""

import pytest
from django.contrib import admin
from django.test import RequestFactory

from vendor_management_system.documents.models import Document
from vendor_management_system.portal.tests.factories import (
    DocumentFactory,
    VendorCompetenceFactory,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors.admin import (
    DocumentInline,
    VendorAdmin,
    VendorCompetenceInline,
)
from vendor_management_system.vendors.models import Vendor, VendorCompetence
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def gestore():
    return User.objects.create_superuser(
        email="gestore@example.invalid", password="x", role="admin"
    )


def _salva(inline_cls, model, vendor, gestore, prefix, riga):
    """Salva l'inline come farebbe l'admin, con una sola riga modificata."""
    request = RequestFactory().post("/")
    request.user = gestore
    inline = inline_cls(Vendor, admin.site)
    formset_cls = inline.get_formset(request, vendor)
    dati = {
        f"{prefix}-TOTAL_FORMS": "1",
        f"{prefix}-INITIAL_FORMS": "1",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }
    dati.update({f"{prefix}-0-{k}": v for k, v in riga.items()})
    formset = formset_cls(dati, instance=vendor, prefix=prefix)
    assert formset.is_valid(), formset.errors
    model_admin = VendorAdmin(Vendor, admin.site)
    model_admin.save_formset(request, None, formset, True)


def test_approvare_un_documento_compila_revisore_e_data(gestore):
    vendor = VendorFactory()
    doc = DocumentFactory(vendor=vendor, status="UPLOADED")

    _salva(
        DocumentInline,
        Document,
        vendor,
        gestore,
        "documents",
        {
            "id": doc.pk,
            "vendor": vendor.pk,
            "document_type": doc.document_type_id,
            "status": "APPROVED",
        },
    )

    doc.refresh_from_db()
    assert doc.status == "APPROVED"
    assert doc.reviewed_by.email == gestore.email
    assert doc.reviewed_at is not None


def test_documento_non_toccato_non_riceve_revisore(gestore):
    vendor = VendorFactory()
    doc = DocumentFactory(vendor=vendor, status="UPLOADED")

    _salva(
        DocumentInline,
        Document,
        vendor,
        gestore,
        "documents",
        {
            "id": doc.pk,
            "vendor": vendor.pk,
            "document_type": doc.document_type_id,
            "status": "UPLOADED",
            "notes": "",
        },
    )

    doc.refresh_from_db()
    assert doc.reviewed_by is None


def test_spuntare_verificata_compila_verificatore_e_data(gestore):
    vendor = VendorFactory()
    req = VendorCompetenceFactory(vendor=vendor)

    _salva(
        VendorCompetenceInline,
        VendorCompetence,
        vendor,
        gestore,
        "vendor_competences",
        {
            "id": req.pk,
            "vendor": vendor.pk,
            "competence": req.competence_id,
            "verified": "on",
        },
    )

    req.refresh_from_db()
    assert req.verified is True
    assert req.verified_by == gestore.email
    assert req.verified_date is not None
