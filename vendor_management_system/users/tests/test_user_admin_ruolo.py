"""Il campo ruolo si assegna o modifica solo da un superuser.

Un Admin non superuser può modificare gli altri utenti (nome, attivo, ecc.)
ma non il loro ruolo, e non può crearne di nuovi.
"""

import pytest
from django.urls import reverse

from vendor_management_system.users.models import User
from vendor_management_system.vendors.tests.factories import VendorFactory

PASSWORD = "ruolo-pass-1234"


@pytest.fixture
def admin_client(client, db):
    admin = User.objects.create_user(
        email="admin-ruolo-test@example.invalid",
        password=PASSWORD,
        role="admin",
    )
    client.login(email=admin.email, password=PASSWORD)
    return client


@pytest.fixture
def superuser_client(client, db):
    superuser = User.objects.create_superuser(
        email="super-ruolo-test@example.invalid",
        password=PASSWORD,
        role="admin",
    )
    client.login(email=superuser.email, password=PASSWORD)
    return client


def _dati_modifica(utente, **overrides):
    data = {
        "email": utente.email,
        "name": utente.name,
        "user_type": "local",
        "is_active": "on",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_admin_non_superuser_non_vede_il_campo_ruolo(admin_client):
    bersaglio = User.objects.create_user(
        email="bo-target@example.invalid", password=PASSWORD, role="bo_user"
    )

    response = admin_client.get(
        reverse("admin:users_user_change", args=[bersaglio.pk])
    )

    assert response.status_code == 200
    assert "role" not in response.context["adminform"].form.fields


@pytest.mark.django_db
def test_admin_non_superuser_non_puo_cambiare_il_ruolo(admin_client):
    bersaglio = User.objects.create_user(
        email="bo-target@example.invalid", password=PASSWORD, role="bo_user"
    )

    response = admin_client.post(
        reverse("admin:users_user_change", args=[bersaglio.pk]),
        _dati_modifica(bersaglio, role="admin", name="Nome Cambiato"),
    )

    bersaglio.refresh_from_db()
    assert response.status_code == 302  # salvataggio riuscito
    assert bersaglio.name == "Nome Cambiato"
    assert bersaglio.role == "bo_user"
    assert bersaglio.is_staff is False


@pytest.mark.django_db
def test_admin_non_superuser_non_puo_promuovere_se_stesso(admin_client):
    admin = User.objects.get(email="admin-ruolo-test@example.invalid")

    admin_client.post(
        reverse("admin:users_user_change", args=[admin.pk]),
        _dati_modifica(admin, role="buyer"),
    )

    admin.refresh_from_db()
    assert admin.role == "admin"


@pytest.mark.django_db
def test_admin_non_superuser_non_puo_creare_utenti(admin_client):
    response = admin_client.get(reverse("admin:users_user_add"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_non_superuser_non_scollega_il_fornitore(
    admin_client,
):
    vendor = VendorFactory()
    portale = User.objects.create_user(
        email="fornitore-target@example.invalid",
        password=PASSWORD,
        role="vendor",
        vendor=vendor,
    )

    response = admin_client.post(
        reverse("admin:users_user_change", args=[portale.pk]),
        _dati_modifica(portale, vendor=vendor.pk, name="Referente"),
    )

    portale.refresh_from_db()
    assert response.status_code == 302
    assert portale.role == "vendor"
    assert portale.vendor_id == vendor.pk


@pytest.mark.django_db
def test_superuser_puo_cambiare_il_ruolo(superuser_client):
    bersaglio = User.objects.create_user(
        email="bo-target-super@example.invalid",
        password=PASSWORD,
        role="bo_user",
    )

    response = superuser_client.post(
        reverse("admin:users_user_change", args=[bersaglio.pk]),
        _dati_modifica(bersaglio, role="buyer"),
    )

    bersaglio.refresh_from_db()
    assert response.status_code == 302
    assert bersaglio.role == "buyer"


@pytest.mark.django_db
def test_superuser_puo_creare_utenti(superuser_client):
    response = superuser_client.get(reverse("admin:users_user_add"))

    assert response.status_code == 200
