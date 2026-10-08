"""Test dell'admin Django per `Vendor` (`/admin/vendors/vendor/`).

Copre il filtro per `managed_by` ("Utenti gestione fornitore"), che
permette di isolare i fornitori seguiti da un certo referente
back-office/admin, la validazione dei gestori (dominio email, primario
non secondario) e delle classificazioni aggiuntive.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from vendor_management_system.portal.tests.factories import CategoryFactory
from vendor_management_system.vendors.admin import VendorAdmin, VendorAdminForm
from vendor_management_system.vendors.tests.factories import VendorFactory

User = get_user_model()
PASSWORD = "test-pass-1234"


def test_list_filter_includes_managed_by():
    assert "managed_by" in VendorAdmin.list_filter
    assert "secondary_managers" in VendorAdmin.list_filter


def test_managers_share_a_row_in_base_info_fieldset():
    base_fields = dict(VendorAdmin.fieldsets)[_("Informazioni Base")]["fields"]
    assert ("managed_by", "secondary_managers") in base_fields
    assert "additional_categories" in base_fields


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
    # `competence_zones` (M2M verso le vecchie zone nominate) e' stato
    # sostituito dal selettore territoriale `competence_areas`, nella
    # stessa posizione.
    assert base_fields.index("first_supply_date") == (
        base_fields.index("competence_areas") + 1
    )
    # La Valutazione Finale e' calcolata e sta in "Qualifica e Audit".
    assert base_fields.index("first_supply_date") == (
        base_fields.index("risk_level") - 1
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
    vendor_c = VendorFactory(managed_by=bo_user_b)
    vendor_c.secondary_managers.add(bo_user_a)

    url = reverse("admin:vendors_vendor_changelist")
    response = client.get(url, {"managed_by__id__exact": bo_user_a.pk})

    assert response.status_code == 200
    results = list(response.context["cl"].result_list)
    assert vendor_a in results
    assert vendor_b not in results

    response = client.get(url, {"secondary_managers__id__exact": bo_user_a.pk})
    assert list(response.context["cl"].result_list) == [vendor_c]


@pytest.mark.django_db
def test_admin_form_validates_managers_and_additional_categories(settings):
    settings.VENDOR_MANAGER_EMAIL_DOMAIN = "fulgard.com"
    ok = User.objects.create_user(
        email="ok@fulgard.com", password=PASSWORD, role="bo_user"
    )
    other = User.objects.create_user(
        email="other@fulgard.com", password=PASSWORD, role="bo_user"
    )
    foreign = User.objects.create_user(
        email="bo@example.invalid", password=PASSWORD, role="bo_user"
    )
    category = CategoryFactory()
    vendor = VendorFactory(category=category)

    def errors(**data):
        form = VendorAdminForm(data=data, instance=vendor)
        form.is_valid()
        return form.errors

    assert "managed_by" in errors(managed_by=foreign.pk)
    assert "secondary_managers" in errors(secondary_managers=[foreign.pk])
    assert "secondary_managers" in errors(
        managed_by=ok.pk, secondary_managers=[ok.pk, other.pk]
    )
    assert "managed_by" not in errors(
        managed_by=ok.pk, secondary_managers=[other.pk]
    )
    assert "additional_categories" in errors(
        category=category.pk, additional_categories=[category.pk]
    )
