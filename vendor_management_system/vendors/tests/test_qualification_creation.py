"""Alla creazione il fornitore parte sempre "In attesa"."""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from vendor_management_system.vendors.admin import VendorAdmin
from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.mark.parametrize("valore", [None, ""])
def test_stato_vuoto_alla_creazione_diventa_in_attesa(valore):
    vendor = VendorFactory(qualification_status=valore)
    vendor.refresh_from_db()
    assert vendor.qualification_status == "PENDING"


def test_creazione_da_admin_ignora_lo_stato_scelto(rf):
    model_admin = VendorAdmin(Vendor, admin.site)
    vendor = Vendor(name="Nuovo", qualification_status="APPROVED")

    model_admin.save_model(rf.get("/"), vendor, form=None, change=False)

    vendor.refresh_from_db()
    assert vendor.qualification_status == "PENDING"


def test_modifica_da_admin_conserva_lo_stato_scelto(rf):
    model_admin = VendorAdmin(Vendor, admin.site)
    vendor = VendorFactory()
    vendor.qualification_status = "REJECTED"

    model_admin.save_model(rf.get("/"), vendor, form=None, change=True)

    vendor.refresh_from_db()
    assert vendor.qualification_status == "REJECTED"


def test_creazione_da_api_ignora_lo_stato_passato():
    user = User.objects.create_user(
        email="api-user@example.invalid", password="x", role="admin"
    )
    token = Token.objects.create(user=user).key

    response = APIClient().post(
        f"{reverse('vendors--list-create-vendor')}?token={token}",
        {"name": "Fornitore API", "qualification_status": "APPROVED"},
        format="json",
    )

    assert response.status_code == 201, response.data
    vendor = Vendor.objects.get(vendor_code=response.data["vendor_code"])
    assert vendor.qualification_status == "PENDING"
