"""Ruolo Buyer: vede solo la dashboard fornitori e quanto serve a usarla.

Completa la matrice di docs/PERMESSI_RUOLI.md: il Buyer non è staff, non entra
in /admin/, nelle API REST né nella dashboard back office.
"""

import pytest
from django.contrib.auth.models import Group
from django.core import mail
from django.test import Client
from django.urls import reverse
from rest_framework.authtoken.models import Token

from vendor_management_system.users.models import User
from vendor_management_system.vendors.tests.factories import VendorFactory

PASSWORD = "buyer-pass-1234"
DASHBOARD = "/vendors/dashboard/"


@pytest.fixture(autouse=True)
def _email_non_inviate_davvero(settings):
    settings.EMAIL_REDIRECT_TO = []


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.invalid", password=PASSWORD, role="buyer"
    )


@pytest.mark.django_db
def test_buyer_ha_il_suo_gruppo_e_non_e_staff(buyer):
    assert buyer.is_staff is False
    assert list(buyer.groups.values_list("name", flat=True)) == ["Buyer"]
    assert Group.objects.get(name="Buyer").permissions.count() == 0


@pytest.mark.django_db
def test_login_del_buyer_porta_alla_dashboard_fornitori(client, buyer):
    response = client.post(
        reverse("login"), {"email": buyer.email, "password": PASSWORD}
    )

    assert response.status_code == 302
    assert response.url == DASHBOARD


@pytest.mark.django_db
def test_redirect_generico_del_buyer_porta_alla_dashboard(client, buyer):
    client.force_login(buyer)

    response = client.get(reverse("dashboard-redirect"))

    assert response.status_code == 302
    assert response.url == DASHBOARD


@pytest.mark.django_db
def test_buyer_usa_dashboard_export_scheda_e_prospetto(client, buyer):
    vendor = VendorFactory()
    client.force_login(buyer)

    assert client.get(DASHBOARD).status_code == 200
    assert client.get("/vendors/export-excel/").status_code == 200
    assert (
        client.get(f"/vendors/dashboard/vendor/{vendor.pk}/").status_code
        == 200
    )
    response = client.post(
        "/vendors/dashboard/prospect/",
        {
            "name": "Prospetto Srl",
            "vat_number": "01234567890",
            "email": "prospetto@example.invalid",
        },
    )
    assert response.status_code == 201
    creato = User.objects.get(email="prospetto@example.invalid").vendor
    assert str(creato.managed_by_id) == str(buyer.pk)
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_buyer_non_vede_admin_dashboard_bo_e_api(client, buyer):
    client.force_login(buyer)

    assert client.get("/admin/").status_code == 302
    assert client.get(reverse("portal:bo-dashboard")).status_code == 302
    assert client.get("/vendors/dashboard-vendors/").status_code == 403
    assert client.get("/vendors/dashboard-stats/").status_code == 403


@pytest.mark.django_db
def test_buyer_con_token_non_legge_l_api_fornitori(buyer):
    token = Token.objects.create(user=buyer)

    response = Client().get(f"/vendors/?token={token.key}")

    assert response.status_code == 403


@pytest.mark.django_db
def test_dashboard_senza_link_admin_per_il_buyer(client, buyer):
    client.force_login(buyer)

    html = client.get(DASHBOARD).content.decode()

    assert f'href="{reverse("admin:index")}"' not in html


@pytest.mark.django_db
def test_il_buyer_puo_essere_utente_di_gestione_del_fornitore(buyer):
    vendor = VendorFactory(managed_by=buyer)
    vendor.full_clean(exclude=["vendor_code"])

    assert str(vendor.managed_by_id) == str(buyer.pk)


@pytest.mark.django_db
def test_fornitore_non_usa_le_funzioni_del_buyer(client):
    vendor = VendorFactory(email="contatto@example.invalid")
    utente = User.objects.create_user(
        email="fornitore-buyer@example.invalid",
        password=PASSWORD,
        role="vendor",
        vendor=vendor,
    )
    client.force_login(utente)

    assert (
        client.get(f"/vendors/dashboard/vendor/{vendor.pk}/").status_code
        == 403
    )
    assert client.post("/vendors/dashboard/prospect/", {}).status_code == 403
