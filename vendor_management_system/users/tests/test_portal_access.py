"""Test della creazione utenza portale fornitore e dell'email d'invito
(`users/portal_access.py` + `core/emails.py`)."""

import re

import pytest
from django.core import mail
from django.test import RequestFactory
from django.urls import resolve

from vendor_management_system.users.models import User
from vendor_management_system.users.portal_access import (
    PortalAccessError,
    create_portal_user,
    send_portal_invite,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

VENDOR_EMAIL = "fornitore-invito@example.invalid"


def _vendor(**kwargs):
    kwargs.setdefault("email", VENDOR_EMAIL)
    kwargs.setdefault("name", "Fornitore Prova Srl")
    return VendorFactory(**kwargs)


@pytest.mark.django_db
def test_create_portal_user_links_vendor_without_usable_password():
    vendor = _vendor(reference_contact="Mario Rossi")

    user = create_portal_user(vendor)

    assert user.email == VENDOR_EMAIL
    assert user.role == "vendor"
    assert user.vendor == vendor
    assert user.name == "Mario Rossi"
    assert not user.has_usable_password()
    assert list(user.groups.values_list("name", flat=True)) == ["Vendors"]


@pytest.mark.django_db
def test_create_portal_user_requires_vendor_email():
    with pytest.raises(PortalAccessError, match="email di contatto"):
        create_portal_user(_vendor(email=""))


@pytest.mark.django_db
def test_create_portal_user_rejects_email_used_by_another_user():
    User.objects.create_user(
        email=VENDOR_EMAIL.upper(), password="x", role="bo_user"
    )
    vendor = _vendor()

    with pytest.raises(PortalAccessError, match="già usata"):
        create_portal_user(vendor)
    assert not vendor.users.exists()


@pytest.mark.django_db
def test_create_portal_user_only_once_per_vendor():
    vendor = _vendor()
    create_portal_user(vendor)

    with pytest.raises(PortalAccessError, match="Reinvia invito"):
        create_portal_user(vendor)


@pytest.mark.django_db
def test_send_portal_invite_email_has_set_password_and_login_links(settings):
    settings.EMAIL_REDIRECT_TO = []
    settings.DEFAULT_FROM_EMAIL = "noreply@example.invalid"
    user = create_portal_user(_vendor())

    recipients = send_portal_invite(user, RequestFactory().get("/"))

    assert recipients == [VENDOR_EMAIL]
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    html = message.alternatives[0][0]
    assert message.to == [VENDOR_EMAIL]
    assert message.from_email == "noreply@example.invalid"
    assert "Fornitore Prova Srl" in html
    path = re.search(
        r"http://testserver(/auth/imposta-password/\S+/)", message.body
    ).group(1)
    assert resolve(path).url_name == "portal_invite_confirm"
    assert path in html
    assert "http://testserver/auth/login/" in message.body
    assert "http://testserver/auth/login/" in html
    assert "Ambiente di prova" not in html


@pytest.mark.django_db
def test_email_redirect_replaces_recipients(settings):
    settings.EMAIL_REDIRECT_TO = ["casella-test@example.invalid"]
    user = create_portal_user(_vendor())

    recipients = send_portal_invite(user, RequestFactory().get("/"))

    message = mail.outbox[0]
    assert recipients == ["casella-test@example.invalid"]
    assert message.to == ["casella-test@example.invalid"]
    assert message.subject.startswith(f"[REDIRECT → {VENDOR_EMAIL}]")
    assert f"Destinatario originale: {VENDOR_EMAIL}" in message.body
    assert "Ambiente di prova" in message.alternatives[0][0]
