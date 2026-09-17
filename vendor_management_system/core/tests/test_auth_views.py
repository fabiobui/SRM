"""Test del redirect post-login per ruolo (`CustomLoginView.redirect_by_role`).

Copre tutti i rami: `bo_user` atterra sulla dashboard consolidata
back-office (`/portale/backoffice/dashboard/`); `admin`/superuser e
`vendor` restano sui rispettivi redirect esistenti.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.portal.tests.factories import VendorUserFactory

User = get_user_model()
PASSWORD = "test-pass-1234"


def _post_login(client, email, password=PASSWORD):
    return client.post(
        reverse("login"), {"email": email, "password": password}
    )


@pytest.mark.django_db
def test_bo_user_redirects_to_new_backoffice_dashboard(client):
    user = User.objects.create_user(
        email="bo-login@example.invalid", password=PASSWORD, role="bo_user"
    )

    response = _post_login(client, user.email)

    assert response.status_code == 302
    assert response.url == "/portale/backoffice/dashboard/"


@pytest.mark.django_db
def test_admin_user_still_redirects_to_django_admin(client):
    user = User.objects.create_user(
        email="admin-login@example.invalid", password=PASSWORD, role="admin"
    )

    response = _post_login(client, user.email)

    assert response.status_code == 302
    assert response.url == "/admin/"


@pytest.mark.django_db
def test_superuser_still_redirects_to_django_admin(client):
    user = User.objects.create_superuser(
        email="superuser-login@example.invalid", password=PASSWORD
    )

    response = _post_login(client, user.email)

    assert response.status_code == 302
    assert response.url == "/admin/"


@pytest.mark.django_db
def test_vendor_user_still_redirects_to_legacy_portal(client):
    user = VendorUserFactory(password=PASSWORD)

    response = _post_login(client, user.email)

    assert response.status_code == 302
    assert response.url == "/documents/portal/"
