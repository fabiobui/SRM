"""Stato di validità unificato (documenti e requisiti), data di
qualifica automatica, colonna "Portale attivato" e abilitazioni senza i
campi booleani."""

from datetime import date, timedelta

import pytest
from django.contrib import admin

from vendor_management_system.documents.models import (
    DocumentCatalog,
)
from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    DocumentFactory,
    VendorCompetenceFactory,
    VendorUserFactory,
)
from vendor_management_system.vendors.admin import (
    DocumentInline,
    VendorAdmin,
    VendorCompetenceInline,
)
from vendor_management_system.vendors.models import Vendor, VendorCompetence
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db

FUTURE = date.today() + timedelta(days=400)
SOON = date.today() + timedelta(days=5)
PAST = date.today() - timedelta(days=1)


def _doc(status, *, file="docs/a.pdf", expiry=None, reminder=30):
    catalog = DocumentCatalog.objects.create(
        code=f"T-{DocumentCatalog.objects.count()}",
        name="Tipo",
        requires_renewal=True,
        reminder_days_before=reminder,
    )
    return DocumentFactory(
        document_type=catalog, status=status, file=file, expiry_date=expiry
    )


@pytest.mark.parametrize(
    "status,file,expiry,atteso",
    [
        ("PENDING", "", None, "PENDING"),
        ("UPLOADED", "docs/a.pdf", FUTURE, "IN_REVIEW"),
        ("REJECTED", "docs/a.pdf", FUTURE, "NOT_VALID"),
        ("APPROVED", "docs/a.pdf", FUTURE, "VALID"),
        ("APPROVED", "docs/a.pdf", SOON, "EXPIRING_SOON"),
        ("APPROVED", "docs/a.pdf", PAST, "EXPIRED"),
    ],
)
def test_validity_status_documento(status, file, expiry, atteso):
    assert _doc(status, file=file, expiry=expiry).validity_status == atteso


def test_file_caricato_da_admin_va_in_revisione():
    doc = _doc("PENDING", file="docs/a.pdf")
    assert doc.status == "UPLOADED"
    assert doc.validity_status == "IN_REVIEW"


@pytest.mark.parametrize(
    "campi,atteso",
    [
        ({}, "PENDING"),
        ({"document_file": "reqs/a.pdf"}, "IN_REVIEW"),
        ({"document_file": "reqs/a.pdf", "rejected": True}, "NOT_VALID"),
        ({"document_file": "reqs/a.pdf", "verified": True}, "VALID"),
        (
            {
                "document_file": "reqs/a.pdf",
                "verified": True,
                "expiry_date": PAST,
            },
            "EXPIRED",
        ),
    ],
)
def test_validity_status_requisito(campi, atteso):
    req = VendorCompetenceFactory(**campi)
    assert req.validity_status == atteso


def test_requisito_in_scadenza():
    competence = CompetenceFactory(requires_renewal=True)
    competence.reminder_days_before = 30
    competence.save()
    req = VendorCompetenceFactory(
        competence=competence,
        document_file="reqs/a.pdf",
        verified=True,
        expiry_date=SOON,
    )
    assert req.validity_status == "EXPIRING_SOON"
    assert req.satisfies_requirement


def test_data_qualifica_si_valorizza_al_cambio_di_stato():
    vendor = VendorFactory(qualification_status="PENDING")
    vendor = Vendor.objects.get(pk=vendor.pk)

    vendor.qualification_status = "REJECTED"
    vendor.save()

    vendor.refresh_from_db()
    assert vendor.qualification_date == date.today()


def test_data_qualifica_modificata_a_mano_resta():
    vendor = Vendor.objects.get(
        pk=VendorFactory(qualification_status="PENDING").pk
    )
    manuale = date(2024, 1, 15)

    vendor.qualification_status = "REJECTED"
    vendor.qualification_date = manuale
    vendor.save()

    vendor.refresh_from_db()
    assert vendor.qualification_date == manuale


def test_cambio_stato_funziona_con_use_tz_false(settings):
    settings.USE_TZ = False
    vendor = VendorFactory(qualification_status="PENDING")

    vendor._update_qualification_status("TO_REVIEW")

    vendor.refresh_from_db()
    assert vendor.qualification_status == "TO_REVIEW"
    assert vendor.qualification_date == date.today()


def test_sync_automatico_aggiorna_la_data():
    vendor = VendorFactory(qualification_status="PENDING")
    vendor._update_qualification_status("TO_REVIEW")

    vendor.refresh_from_db()
    assert vendor.qualification_date == date.today()


def test_colonna_portale_attivato():
    admin_vendor = VendorAdmin(Vendor, admin.site)
    senza = VendorFactory()
    invitato = VendorFactory()
    attivo = VendorFactory()
    VendorUserFactory(vendor=invitato).set_unusable_password()
    u = invitato.users.get()
    u.set_unusable_password()
    u.save()
    VendorUserFactory(vendor=attivo)

    def risultato(v):
        v = Vendor.objects.prefetch_related("users").get(pk=v.pk)
        return admin_vendor.portal_activated(v)

    assert risultato(senza) is False
    assert risultato(invitato) is False
    assert risultato(attivo) is True


CAMPI_NASCOSTI = ("verified",)
CAMPI_TIPO_REQUISITO = (
    "is_competenza",
    "is_qualifica",
    "is_iscrizione_albo",
    "has_certification",
)


def test_inline_abilitazioni_mostra_tipo_requisito_senza_verificata():
    inline = VendorCompetenceInline(Vendor, admin.site)
    for campo in CAMPI_TIPO_REQUISITO:
        assert campo in inline.fields
    for campo in CAMPI_NASCOSTI:
        assert campo not in inline.fields
        assert campo not in inline.readonly_fields


def test_admin_abilitazioni_mostra_tipo_requisito_senza_verificata():
    model_admin = admin.site._registry[VendorCompetence]
    in_form = {
        campo for _, opts in model_admin.fieldsets for campo in opts["fields"]
    }
    visibili = {
        *model_admin.list_display,
        *model_admin.list_filter,
        *in_form,
    }
    assert set(CAMPI_TIPO_REQUISITO) <= visibili
    assert not visibili & set(CAMPI_NASCOSTI)


def test_inline_documenti_senza_stato_lavorazione():
    inline = DocumentInline(Vendor, admin.site)
    assert "status" not in inline.fields


def test_etichetta_in_review_uniformata_in_inglese():
    from vendor_management_system.documents.models import (
        VALIDITY_STATUS_META,
    )

    assert VALIDITY_STATUS_META["IN_REVIEW"][0] == "IN REVIEW"
