"""Test del controllo duplicati su Codice Embyon, Partita IVA e Codice
Fiscale nel VendorAdmin (AIDEV-21).

Copre sia la validazione server-side in `VendorAdminForm` (attiva anche a
JS disattivato, obbligatoria per bloccare davvero il salvataggio) sia
l'endpoint AJAX `duplicate-check/` usato per il controllo live nel tab
"Informazioni Base", prima che l'utente salvi.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.vendors.admin import VendorAdminForm
from vendor_management_system.vendors.tests.factories import VendorFactory

User = get_user_model()
PASSWORD = "test-pass-1234"


# ---------------------------------------------------------------------------
# VendorAdminForm
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_form_rejects_duplicate_old_code():
    VendorFactory(old_code="F 35")

    form = VendorAdminForm(data={"old_code": "F 35"})
    form.is_valid()

    assert "old_code" in form.errors
    assert "già usato" in str(form.errors["old_code"])


@pytest.mark.django_db
def test_form_rejects_duplicate_vat_number_case_insensitive():
    VendorFactory(vat_number="IT01234567890")

    form = VendorAdminForm(data={"vat_number": "it01234567890"})
    form.is_valid()

    assert "vat_number" in form.errors
    assert "già usato" in str(form.errors["vat_number"])


@pytest.mark.django_db
def test_form_rejects_duplicate_fiscal_code_case_insensitive():
    VendorFactory(fiscal_code="RSSMRA80A01H501U")

    form = VendorAdminForm(data={"fiscal_code": "rssmra80a01h501u"})
    form.is_valid()

    assert "fiscal_code" in form.errors
    assert "già usato" in str(form.errors["fiscal_code"])


@pytest.mark.django_db
def test_form_error_links_to_existing_vendor_change_page():
    existing = VendorFactory(old_code="F 35")

    form = VendorAdminForm(data={"old_code": "F 35"})
    form.is_valid()

    expected_url = reverse("admin:vendors_vendor_change", args=[existing.pk])
    assert expected_url in str(form.errors["old_code"])
    assert existing.pk in str(form.errors["old_code"])


@pytest.mark.django_db
def test_form_does_not_flag_duplicate_against_itself_when_editing():
    vendor = VendorFactory(old_code="F 35", vat_number="IT01234567890")

    form = VendorAdminForm(
        data={"old_code": "F 35", "vat_number": "IT01234567890"},
        instance=vendor,
    )
    form.is_valid()

    assert "old_code" not in form.errors
    assert "vat_number" not in form.errors


@pytest.mark.django_db
def test_form_allows_unique_values():
    VendorFactory(old_code="F 35")

    form = VendorAdminForm(data={"old_code": "F 99"})
    form.is_valid()

    assert "old_code" not in form.errors


# ---------------------------------------------------------------------------
# Endpoint AJAX duplicate-check/
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_client_logged_in(client):
    superuser = User.objects.create_superuser(
        email="super-duplicate-check@example.invalid",
        password=PASSWORD,
        role="admin",
    )
    client.login(email=superuser.email, password=PASSWORD)
    return client


@pytest.mark.django_db
def test_duplicate_check_view_returns_duplicate_true(admin_client_logged_in):
    existing = VendorFactory(old_code="F 35")

    url = reverse("admin:vendors_vendor_duplicate_check")
    response = admin_client_logged_in.get(
        url, {"field": "old_code", "value": "F 35"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["duplicate"] is True
    assert data["vendor_code"] == existing.pk
    assert data["change_url"] == reverse(
        "admin:vendors_vendor_change", args=[existing.pk]
    )


@pytest.mark.django_db
def test_duplicate_check_view_returns_duplicate_false_for_unique_value(
    admin_client_logged_in,
):
    url = reverse("admin:vendors_vendor_duplicate_check")
    response = admin_client_logged_in.get(
        url, {"field": "vat_number", "value": "IT99999999999"}
    )

    assert response.status_code == 200
    assert response.json() == {"duplicate": False}


@pytest.mark.django_db
def test_duplicate_check_view_excludes_current_pk(admin_client_logged_in):
    vendor = VendorFactory(fiscal_code="RSSMRA80A01H501U")

    url = reverse("admin:vendors_vendor_duplicate_check")
    response = admin_client_logged_in.get(
        url,
        {
            "field": "fiscal_code",
            "value": "RSSMRA80A01H501U",
            "pk": vendor.pk,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"duplicate": False}


@pytest.mark.django_db
def test_duplicate_check_view_requires_staff_login(client):
    url = reverse("admin:vendors_vendor_duplicate_check")
    response = client.get(url, {"field": "old_code", "value": "F 35"})

    assert response.status_code in (302, 403)
