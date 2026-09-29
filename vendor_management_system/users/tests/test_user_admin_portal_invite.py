"""Test di Utenti → Aggiungi utente per il ruolo Fornitore:
senza password parte l'invito via email, con password resta il
comportamento di prima."""

import pytest
from django.core import mail
from django.urls import reverse

from vendor_management_system.users.models import User
from vendor_management_system.vendors.tests.factories import VendorFactory

PASSWORD = "test-pass-1234"
NEW_USER_EMAIL = "nuovo-fornitore@example.invalid"


@pytest.fixture
def admin_client(client, db):
    superuser = User.objects.create_superuser(
        email="super-users@example.invalid", password=PASSWORD, role="admin"
    )
    client.login(email=superuser.email, password=PASSWORD)
    return client


def _add_user(client, **overrides):
    data = {
        "email": NEW_USER_EMAIL,
        "name": "Nuovo Fornitore",
        "user_type": "local",
        "role": "vendor",
        "vendor": VendorFactory().pk,
        "password1": "",
        "password2": "",
    }
    data.update(overrides)
    return client.post(reverse("admin:users_user_add"), data)


@pytest.mark.django_db
def test_vendor_without_password_gets_invite(admin_client, settings):
    settings.EMAIL_REDIRECT_TO = []

    response = _add_user(admin_client)

    assert response.status_code == 302
    user = User.objects.get(email=NEW_USER_EMAIL)
    assert not user.has_usable_password()
    assert [m.to for m in mail.outbox] == [[NEW_USER_EMAIL]]


@pytest.mark.django_db
def test_vendor_with_password_keeps_manual_flow(admin_client):
    password = "Password-Manuale-2026!"

    _add_user(admin_client, password1=password, password2=password)

    user = User.objects.get(email=NEW_USER_EMAIL)
    assert user.check_password(password)
    assert mail.outbox == []


@pytest.mark.django_db
def test_local_bo_user_still_requires_password(admin_client):
    response = _add_user(admin_client, role="bo_user", vendor="")

    assert response.status_code == 200
    assert "La password è obbligatoria" in response.content.decode()
    assert not User.objects.filter(email=NEW_USER_EMAIL).exists()
