"""Periodo validità e giorni di preavviso di documenti e requisiti: campi
validi solo se "Richiede Rinnovo", e stato EXPIRING_SOON dei requisiti."""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from vendor_management_system.documents.models import DocumentCatalog
from vendor_management_system.vendors.models import (
    Competence,
    VendorCompetence,
)
from vendor_management_system.vendors.tests.factories import VendorFactory


def make_competence(**kwargs):
    defaults = {
        "code": f"REQ-{Competence.objects.count()}",
        "name": "Requisito prova",
        "competence_category": "OTHER",
    }
    return Competence.objects.create(**{**defaults, **kwargs})


def assign(competence, days_left):
    return VendorCompetence.objects.create(
        vendor=VendorFactory(),
        competence=competence,
        has_competence=True,
        expiry_date=timezone.now().date() + timedelta(days=days_left),
    )


@pytest.mark.django_db
@pytest.mark.parametrize("factory", [DocumentCatalog, Competence])
def test_catalog_without_renewal_clears_renewal_fields(factory):
    kwargs = {"code": "C1", "name": "N1", "requires_renewal": False}
    if factory is Competence:
        kwargs["competence_category"] = "OTHER"
    item = factory.objects.create(
        validity_period_days=365, reminder_days_before=30, **kwargs
    )

    item.refresh_from_db()

    assert item.validity_period_days is None
    assert item.reminder_days_before is None


@pytest.mark.django_db
def test_partial_save_still_clears_renewal_fields():
    item = make_competence(requires_renewal=True)
    item.requires_renewal = False
    item.save(update_fields=["requires_renewal"])

    item.refresh_from_db()

    assert item.validity_period_days is None
    assert item.reminder_days_before is None


@pytest.mark.parametrize("factory", [DocumentCatalog, Competence])
def test_renewal_fields_required_with_renewal(factory):
    item = factory(
        code="C", name="N", requires_renewal=True, validity_period_days=None
    )
    with pytest.raises(ValidationError) as exc:
        item.clean()
    assert "validity_period_days" in exc.value.message_dict

    item.requires_renewal = False
    item.clean()


@pytest.mark.django_db
def test_competence_expiring_soon_uses_requirement_threshold():
    competence = make_competence(
        requires_renewal=True, reminder_days_before=45
    )

    assert assign(competence, 45).expiry_status == "EXPIRING_SOON"
    assert assign(competence, 46).expiry_status == "VALID"
    assert assign(competence, -1).expiry_status == "EXPIRED"


@pytest.mark.django_db
def test_competence_without_renewal_is_never_expiring_soon():
    competence = make_competence(requires_renewal=False)

    assert assign(competence, 3).expiry_status == "VALID"


@pytest.mark.django_db
def test_vendor_expiring_competences_follow_threshold():
    competence = make_competence(
        requires_renewal=True, reminder_days_before=30
    )
    soon = assign(competence, 10)
    assign(competence, 60)

    assert soon.vendor.expiring_competences == [soon]


@pytest.mark.django_db
def test_competence_validity_endpoint(admin_client):
    renewable = make_competence(
        requires_renewal=True, validity_period_days=730
    )
    fixed = make_competence(requires_renewal=False)

    response = admin_client.get("/admin/vendors/vendor/competence-validity/")

    types = response.json()["types"]
    assert types[str(renewable.pk)]["days"] == 730
    assert types[str(fixed.pk)]["days"] is None
