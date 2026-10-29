"""Test del salvataggio rapido di una riga contratto dalla scheda fornitore
(endpoint `salva-contratto/` del VendorAdmin, AIDEV-173)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.vendors.models import Contract
from vendor_management_system.vendors.tests.factories import VendorFactory

User = get_user_model()
PASSWORD = "test-pass-1234"

PAYLOAD = {
    "contract_number": "CTR-173-001",
    "title": "Contratto di prova",
    "status": "DRAFT",
    "start_date": "2026-01-01",
}


def _url(vendor):
    return reverse("admin:vendors_vendor_contract_save", args=[vendor.pk])


@pytest.fixture
def admin_client_logged_in(client):
    superuser = User.objects.create_superuser(
        email="super-contract-save@example.invalid",
        password=PASSWORD,
        role="admin",
    )
    client.login(email=superuser.email, password=PASSWORD)
    return client


@pytest.mark.django_db
def test_creates_contract_for_the_vendor(admin_client_logged_in):
    vendor = VendorFactory()

    response = admin_client_logged_in.post(_url(vendor), PAYLOAD)

    assert response.status_code == 200
    contract = Contract.objects.get(contract_number="CTR-173-001")
    assert contract.vendor == vendor
    assert response.json()["id"] == str(contract.pk)


@pytest.mark.django_db
def test_returns_field_errors_and_saves_nothing(admin_client_logged_in):
    vendor = VendorFactory()
    Contract.objects.create(vendor=vendor, **PAYLOAD)

    response = admin_client_logged_in.post(_url(vendor), PAYLOAD)

    assert response.status_code == 400
    assert "contract_number" in response.json()["errors"]
    assert Contract.objects.count() == 1


@pytest.mark.django_db
def test_requires_post(admin_client_logged_in):
    vendor = VendorFactory()

    response = admin_client_logged_in.get(_url(vendor))

    assert response.status_code == 405


@pytest.mark.django_db
def test_unknown_vendor_is_404(admin_client_logged_in):
    url = reverse("admin:vendors_vendor_contract_save", args=["NOPE"])

    response = admin_client_logged_in.post(url, PAYLOAD)

    assert response.status_code == 404


@pytest.mark.django_db
def test_staff_without_permissions_is_denied(client):
    staff = User.objects.create_user(
        email="staff-contract-save@example.invalid", password=PASSWORD
    )
    staff.is_staff = True
    staff.save()
    client.login(email=staff.email, password=PASSWORD)
    vendor = VendorFactory()

    response = client.post(_url(vendor), PAYLOAD)

    assert response.status_code == 403
    assert not Contract.objects.exists()
