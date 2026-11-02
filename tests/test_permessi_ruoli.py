"""Flussi di accesso per ruolo: Admin, BO User, Vendors e anonimo.

Ogni test fissa una riga della matrice in docs/PERMESSI_RUOLI.md. L'Admin è
un utente di ruolo `admin` NON superuser: deve bastare il gruppo.
"""

import pytest
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token

from vendor_management_system.users.models import User
from vendor_management_system.vendors.tests.factories import VendorFactory

PASSWORD = "permessi-pass-1234"
DASHBOARD = "/vendors/dashboard/"
EXPORT_EXCEL = "/vendors/export-excel/"
DASHBOARD_VENDORS_API = "/vendors/dashboard-vendors/"
DASHBOARD_STATS_API = "/vendors/dashboard-stats/"
VENDORS_API = "/vendors/"


@pytest.fixture(autouse=True)
def _email_non_inviate_davvero(settings):
    settings.EMAIL_REDIRECT_TO = []


def _utente(email, role, **extra):
    return User.objects.create_user(
        email=email, password=PASSWORD, role=role, **extra
    )


@pytest.fixture
def admin(db):
    return _utente("admin-ruolo@example.invalid", "admin")


@pytest.fixture
def bo_user(db):
    return _utente("bo-ruolo@example.invalid", "bo_user")


@pytest.fixture
def fornitore(db):
    vendor = VendorFactory(email="contatto@example.invalid")
    return _utente("fornitore@example.invalid", "vendor", vendor=vendor)


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="super-ruolo@example.invalid", password=PASSWORD
    )


def _login(client, user):
    client.force_login(user)
    return client


def _portale_accesso_url(vendor):
    return reverse("admin:vendors_vendor_portal_access", args=[vendor.pk])


@pytest.mark.django_db
def test_admin_gestisce_admin_e_dashboard(client, admin):
    vendor = VendorFactory()
    _login(client, admin)

    assert client.get(reverse("admin:index")).status_code == 200
    assert (
        client.get(reverse("admin:vendors_vendor_changelist")).status_code
        == 200
    )
    assert (
        client.get(reverse("admin:users_user_changelist")).status_code == 200
    )
    assert client.get(DASHBOARD).status_code == 200
    assert client.get(reverse("portal:bo-dashboard")).status_code == 200
    assert client.get(_portale_accesso_url(vendor)).status_code == 200


@pytest.mark.django_db
def test_admin_crea_utenza_portale_senza_essere_superuser(client, admin):
    vendor = VendorFactory(email="nuovo@example.invalid")
    _login(client, admin)

    response = client.post(_portale_accesso_url(vendor), {"action": "create"})

    assert response.status_code == 302
    utente = vendor.users.get()
    assert utente.role == "vendor"
    assert utente.email == "nuovo@example.invalid"


@pytest.mark.django_db
def test_admin_non_gestisce_gruppi_ne_superuser(client, admin, superuser):
    _login(client, admin)

    assert client.get("/admin/auth/group/").status_code == 403
    assert (
        client.get(
            reverse("admin:users_user_change", args=[superuser.pk])
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_superuser_puo_concedere_il_superuser(client, superuser, bo_user):
    _login(client, superuser)

    response = client.get(
        reverse("admin:users_user_change", args=[bo_user.pk])
    )

    assert response.status_code == 200
    assert 'name="is_superuser"' in response.content.decode()


@pytest.mark.django_db
def test_admin_non_puo_concedere_il_superuser(client, admin, bo_user):
    _login(client, admin)

    response = client.get(
        reverse("admin:users_user_change", args=[bo_user.pk])
    )

    assert response.status_code == 200
    assert 'name="is_superuser"' not in response.content.decode()


@pytest.mark.django_db
def test_bo_user_non_entra_in_admin(client, bo_user):
    vendor = VendorFactory(email="bo-admin@example.invalid")
    _login(client, bo_user)

    assert client.get(reverse("admin:index")).status_code == 302
    assert (
        client.get(reverse("admin:vendors_vendor_changelist")).status_code
        == 302
    )

    response = client.post(_portale_accesso_url(vendor), {"action": "create"})

    assert response.status_code == 302
    assert not vendor.users.exists()


@pytest.mark.django_db
def test_bo_user_accede_alle_dashboard_e_all_export(client, bo_user):
    _login(client, bo_user)

    assert client.get(DASHBOARD).status_code == 200
    assert client.get(reverse("portal:bo-dashboard")).status_code == 200
    assert client.get(EXPORT_EXCEL).status_code == 200
    assert client.get(DASHBOARD_VENDORS_API).status_code == 200


@pytest.mark.django_db
def test_fornitore_vede_solo_il_portale(client, fornitore):
    _login(client, fornitore)

    assert client.get(reverse("portal:dashboard")).status_code == 200
    assert client.get(DASHBOARD).status_code == 302
    assert client.get(EXPORT_EXCEL).status_code == 302
    assert client.get(reverse("portal:bo-dashboard")).status_code == 302
    assert client.get(DASHBOARD_VENDORS_API).status_code == 403
    assert client.get(DASHBOARD_STATS_API).status_code == 403
    assert client.get("/admin/").status_code == 302


@pytest.mark.django_db
def test_fornitore_con_token_non_legge_l_elenco_fornitori(fornitore):
    token = Token.objects.create(user=fornitore)

    response = Client().get(f"{VENDORS_API}?token={token.key}")

    assert response.status_code == 403


@pytest.mark.django_db
def test_bo_user_con_token_legge_l_elenco_fornitori(bo_user):
    token = Token.objects.create(user=bo_user)

    response = Client().get(f"{VENDORS_API}?token={token.key}")

    assert response.status_code == 200


@pytest.mark.django_db
def test_anonimo_non_legge_dati_fornitori(client):
    assert client.get(DASHBOARD_VENDORS_API).status_code == 401
    assert client.get(DASHBOARD_STATS_API).status_code == 401
    assert client.get(VENDORS_API).status_code == 401
    assert client.get(EXPORT_EXCEL).status_code == 302
    assert client.get(DASHBOARD).status_code == 302
