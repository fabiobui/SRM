"""Test delle pagine pubbliche di impostazione / reset password:
link d'invito al portale fornitori e "Password dimenticata?"."""

import re
from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import resolve, reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from vendor_management_system.portal.tests.factories import VendorUserFactory
from vendor_management_system.users.models import User
from vendor_management_system.users.portal_access import (
    InviteTokenGenerator,
    create_portal_user,
    invite_token_generator,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

NEW_PASSWORD = "Portale-Fornitori-2026!"


def _invite_url(user, token):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    return reverse(
        "portal_invite_confirm", kwargs={"uidb64": uidb64, "token": token}
    )


@pytest.fixture
def invited_user(db):
    return create_portal_user(VendorFactory(email="invitato@example.invalid"))


@pytest.mark.django_db
def test_invite_link_sets_password_then_login_works(client, invited_user):
    url = _invite_url(
        invited_user, invite_token_generator.make_token(invited_user)
    )

    # Il link valido reindirizza alla pagina del form (token in sessione).
    form_url = client.get(url).url
    response = client.get(form_url)
    assert response.context["validlink"] is True
    assert response.context["is_invite"] is True

    response = client.post(
        form_url,
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert response.url == reverse("password_reset_complete")
    invited_user.refresh_from_db()
    assert invited_user.check_password(NEW_PASSWORD)

    response = client.post(
        reverse("login"),
        {"email": invited_user.email, "password": NEW_PASSWORD},
    )
    assert response.url == "/documents/portal/"

    # Password impostata: lo stesso link non è più utilizzabile.
    client.logout()
    assert client.get(url).context["validlink"] is False


@pytest.mark.django_db
def test_invite_link_rejects_expired_or_reset_tokens(
    client, settings, invited_user
):
    settings.PORTAL_INVITE_TIMEOUT_DAYS = 3
    four_days_ago = datetime.now() - timedelta(days=4)
    with mock.patch.object(
        InviteTokenGenerator, "_now", return_value=four_days_ago
    ):
        expired = invite_token_generator.make_token(invited_user)
    reset_token = default_token_generator.make_token(invited_user)

    for token in (expired, reset_token):
        response = client.get(_invite_url(invited_user, token))
        assert response.context["validlink"] is False
        assert "non è valido o è scaduto" in response.content.decode()


@pytest.mark.django_db
def test_password_reset_emails_only_local_users(client, settings):
    settings.EMAIL_REDIRECT_TO = []
    local = VendorUserFactory(email="locale@example.invalid")
    User.objects.create_user(
        email="ldap@example.invalid", role="bo_user", is_ldap_user=True
    )

    for email in (
        "ldap@example.invalid",
        "sconosciuto@example.invalid",
        local.email,
    ):
        response = client.post(reverse("password_reset"), {"email": email})
        # Stessa risposta per tutti: non si rivela quali email esistono.
        assert response.url == reverse("password_reset_done")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [local.email]
    path = re.search(r"http://testserver(/auth/reset/\S+/)", message.body)
    assert resolve(path.group(1)).url_name == "password_reset_confirm"
