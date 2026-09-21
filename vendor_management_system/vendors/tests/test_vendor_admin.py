"""Test dell'admin Django per `Vendor` (`/admin/vendors/vendor/`).

Copre il filtro per `managed_by` ("Utente gestione fornitore"), che
permette di isolare i fornitori seguiti da un certo referente
back-office/admin.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vendor_management_system.vendors.admin import VendorAdmin
from vendor_management_system.vendors.tests.factories import VendorFactory

User = get_user_model()
PASSWORD = "test-pass-1234"


def test_list_filter_includes_managed_by():
    assert "managed_by" in VendorAdmin.list_filter


def test_vendor_code_is_first_in_list_display():
    # `list_display_links` non è impostato: Django rende cliccabile di
    # default la prima colonna. Deve essere "Codice Fornitore", non più
    # "Codice Embyon" (AIDEV-41).
    assert VendorAdmin.list_display[0] == "vendor_code"
    assert VendorAdmin.list_display[1] == "old_code"


def test_pec_fieldset_position():
    fieldsets = dict(VendorAdmin.fieldsets)
    contatti_fields = fieldsets[_("Contatti")]["fields"]
    assert (
        contatti_fields.index("pec")
        == contatti_fields.index("reference_contact") + 1
    )
    assert contatti_fields.index("pec") == contatti_fields.index("website") - 1


def test_first_supply_date_fieldset_position():
    fieldsets = dict(VendorAdmin.fieldsets)
    base_fields = fieldsets[_("Informazioni Base")]["fields"]
    assert base_fields.index("first_supply_date") == (
        base_fields.index("competence_zones") + 1
    )
    assert base_fields.index("first_supply_date") == (
        base_fields.index("vendor_final_evaluation") - 1
    )


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
