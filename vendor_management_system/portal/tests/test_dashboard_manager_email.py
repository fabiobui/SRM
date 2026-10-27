"""La home del portale mostra la mail del gestore di riferimento."""

import pytest
from django.urls import reverse

from vendor_management_system.portal.tests.factories import VendorUserFactory
from vendor_management_system.users.models import User

PASSWORD = "test-pass-1234"


def _home(client, **vendor_attrs):
    user = VendorUserFactory(password=PASSWORD)
    client.login(email=user.email, password=PASSWORD)
    return user.vendor, client.get(reverse("portal:dashboard"))


@pytest.mark.django_db
def test_mostra_email_gestore_principale(client):
    user = VendorUserFactory(password=PASSWORD)
    gestore = User.objects.create_user(
        email="gestore-ref@example.invalid", password="x", role="admin"
    )
    user.vendor.managed_by = gestore
    user.vendor.save()
    client.login(email=user.email, password=PASSWORD)

    response = client.get(reverse("portal:dashboard"))

    assert "gestore-ref@example.invalid" in response.content.decode()


@pytest.mark.django_db
def test_senza_gestore_non_mostra_il_referente(client):
    _, response = _home(client)

    assert "Il tuo referente" not in response.content.decode()
