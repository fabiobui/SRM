"""Test del pulsante "Crea accesso portale" sulla scheda Vendor in admin
(`VendorAdmin.portal_access_view`)."""

import pytest
from django.core import mail
from django.urls import reverse

from vendor_management_system.users.models import User
from vendor_management_system.users.portal_access import create_portal_user
from vendor_management_system.vendors.tests.factories import VendorFactory

PASSWORD = "test-pass-1234"


@pytest.fixture
def admin_client(client, db):
    superuser = User.objects.create_superuser(
        email="super-portal@example.invalid", password=PASSWORD, role="admin"
    )
    client.login(email=superuser.email, password=PASSWORD)
    return client


def _portal_access_url(vendor):
    return reverse("admin:vendors_vendor_portal_access", args=[vendor.pk])


@pytest.mark.django_db
def test_change_page_shows_portal_access_button(admin_client):
    vendor = VendorFactory(email="scheda@example.invalid")

    response = admin_client.get(
        reverse("admin:vendors_vendor_change", args=[vendor.pk])
    )

    content = response.content.decode()
    assert "Crea accesso portale" in content
    assert _portal_access_url(vendor) in content


@pytest.mark.django_db
def test_create_portal_access_creates_user_and_sends_invite(
    admin_client, settings
):
    settings.EMAIL_REDIRECT_TO = []
    vendor = VendorFactory(email="nuovo-accesso@example.invalid")
    url = _portal_access_url(vendor)
    assert admin_client.get(url).status_code == 200

    response = admin_client.post(url, {"action": "create"})

    assert response.url == reverse(
        "admin:vendors_vendor_change", args=[vendor.pk]
    )
    user = vendor.users.get()
    assert user.role == "vendor"
    assert not user.has_usable_password()
    assert [m.to for m in mail.outbox] == [["nuovo-accesso@example.invalid"]]


@pytest.mark.django_db
def test_resend_invite_only_while_password_not_set(admin_client):
    vendor = VendorFactory(email="reinvio@example.invalid")
    user = create_portal_user(vendor)
    url = _portal_access_url(vendor)

    admin_client.post(url, {"action": "resend", "user": user.pk})
    assert len(mail.outbox) == 1

    user.set_password(PASSWORD)
    user.save()
    response = admin_client.post(url, {"action": "resend", "user": user.pk})
    assert response.url == url
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_portal_access_requires_vendor_change_permission(client):
    staff = User.objects.create_user(
        email="staff-senza-permessi@example.invalid",
        password=PASSWORD,
        role="bo_user",
    )
    staff.is_staff = True
    staff.save()
    client.login(email=staff.email, password=PASSWORD)
    vendor = VendorFactory(email="protetto@example.invalid")

    response = client.post(_portal_access_url(vendor), {"action": "create"})

    assert response.status_code == 403
    assert not vendor.users.exists()
