"""Test dell'admin Django per `Vendor` (`/admin/vendors/vendor/`).

Copre il filtro per `managed_by` ("Utente gestione fornitore"), che
permette di isolare i fornitori seguiti da un certo referente
back-office/admin.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.vendors.admin import VendorAdmin
from vendor_management_system.vendors.tests.factories import VendorFactory

User = get_user_model()
PASSWORD = "test-pass-1234"


def test_list_filter_includes_managed_by():
    assert "managed_by" in VendorAdmin.list_filter


@pytest.mark.django_db
def test_vendor_changelist_filters_by_managed_by(client):
    superuser = User.objects.create_superuser(
        email="super-vendor-admin@example.invalid",
        password=PASSWORD,
        role="admin",
    )
    client.login(email=superuser.email, password=PASSWORD)

    bo_user_a = User.objects.create_user(
        email="bo-vendor-a@example.invalid", password=PASSWORD, role="bo_user"
    )
    bo_user_b = User.objects.create_user(
        email="bo-vendor-b@example.invalid", password=PASSWORD, role="bo_user"
    )
    vendor_a = VendorFactory(managed_by=bo_user_a)
    vendor_b = VendorFactory(managed_by=bo_user_b)

    url = reverse("admin:vendors_vendor_changelist")
    response = client.get(url, {"managed_by__id__exact": bo_user_a.pk})

    assert response.status_code == 200
    results = list(response.context["cl"].result_list)
    assert vendor_a in results
    assert vendor_b not in results
