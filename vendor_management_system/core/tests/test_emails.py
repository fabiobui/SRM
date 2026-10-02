"""Logo Fulgard allegato inline a tutte le email HTML."""

import django
import pytest
from django.core import mail

from vendor_management_system.core import emails


def _send():
    emails.send_templated_email(
        subject="Prova",
        template_name="password_reset",
        context={"reset_url": "https://x.invalid", "reset_hours": 24},
        to=["utente@example.invalid"],
    )
    return mail.outbox[-1]


@pytest.fixture(autouse=True)
def _no_redirect(settings):
    settings.EMAIL_REDIRECT_TO = []


def test_logo_attached_inline_and_referenced_by_cid(tmp_path, monkeypatch):
    logo = tmp_path / "fulgard-logo.jpg"
    logo.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
    monkeypatch.setattr(emails, "LOGO_PATH", logo)

    message = _send()

    html = message.alternatives[0][0]
    assert 'src="cid:fulgard-logo"' in html
    raw = message.message()
    # Django 6 (non in produzione) usa sempre "mixed", vedi core/emails.py.
    expected_subtype = "related" if django.VERSION < (6, 0) else "mixed"
    assert raw.get_content_subtype() == expected_subtype
    images = [p for p in raw.walk() if p.get_content_maintype() == "image"]
    assert [img["Content-ID"] for img in images] == ["<fulgard-logo>"]


def test_missing_logo_does_not_block_email(tmp_path, monkeypatch):
    monkeypatch.setattr(emails, "LOGO_PATH", tmp_path / "manca.jpg")

    message = _send()

    assert "cid:" not in message.alternatives[0][0]
    assert message.attachments == []
