"""Promemoria email di scadenza documenti e abilitazioni al fornitore."""

from datetime import date, datetime, timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command

from vendor_management_system.core.emails import send_templated_email
from vendor_management_system.documents.models import Document, DocumentCatalog
from vendor_management_system.vendors.expiry_reminders import (
    send_expiry_reminders,
)
from vendor_management_system.vendors.models import (
    Competence,
    ExpiryReminderLog,
    VendorCompetence,
)
from vendor_management_system.vendors.tasks import send_expiry_reminders_task
from vendor_management_system.vendors.tests.factories import VendorFactory

TODAY = date(2026, 10, 1)


@pytest.fixture(autouse=True)
def _no_redirect(settings):
    settings.EMAIL_REDIRECT_TO = []
    settings.PORTAL_BASE_URL = "https://portale.example.invalid"


def make_vendor(**kwargs):
    defaults = {
        "email": "fornitore@example.invalid",
        "expiry_notifications_enabled": True,
    }
    return VendorFactory(**{**defaults, **kwargs})


def make_document(
    vendor, days_left, *, threshold=30, status="APPROVED", renewal=True
):
    catalog = DocumentCatalog.objects.create(
        code=f"DOC-{DocumentCatalog.objects.count()}",
        name=f"DURC {DocumentCatalog.objects.count()}",
        requires_renewal=renewal,
        reminder_days_before=threshold,
    )
    return Document.objects.create(
        vendor=vendor,
        document_type=catalog,
        status=status,
        expiry_date=TODAY + timedelta(days=days_left),
    )


def make_competence(vendor, days_left, *, has_competence=True, renewal=True):
    competence = Competence.objects.create(
        code=f"REQ-{Competence.objects.count()}",
        name="Patentino PES/PAV",
        competence_category="OTHER",
        requires_renewal=renewal,
    )
    return VendorCompetence.objects.create(
        vendor=vendor,
        competence=competence,
        has_competence=has_competence,
        expiry_date=TODAY + timedelta(days=days_left),
    )


def stages():
    return list(ExpiryReminderLog.objects.values_list("stage", flat=True))


@pytest.mark.django_db
def test_first_reminder_at_threshold_and_not_repeated():
    vendor = make_vendor()
    make_document(vendor, 30)

    send_expiry_reminders(today=TODAY)
    send_expiry_reminders(today=TODAY)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["fornitore@example.invalid"]
    assert "DURC" in message.body
    assert "31/10/2026" in message.body
    assert "https://portale.example.invalid/auth/login/" in message.body
    assert stages() == [ExpiryReminderLog.STAGE_FIRST]


@pytest.mark.django_db
def test_document_type_threshold_drives_first_reminder():
    vendor = make_vendor()
    make_document(vendor, 45, threshold=45)
    make_document(vendor, 31, threshold=30)

    send_expiry_reminders(today=TODAY)

    assert len(mail.outbox) == 1
    assert ExpiryReminderLog.objects.get().item_label.startswith("DURC")
    assert "tra 45 giorni" in mail.outbox[0].body


@pytest.mark.django_db
def test_out_of_range_threshold_in_db_is_clamped():
    vendor = make_vendor()
    make_document(vendor, 100)
    make_document(vendor, 90)
    # Valore scritto senza passare dal form: viene trattato come 90.
    DocumentCatalog.objects.update(reminder_days_before=120)

    send_expiry_reminders(today=TODAY)

    assert ExpiryReminderLog.objects.count() == 1
    assert ExpiryReminderLog.objects.get().expiry_date == TODAY + timedelta(90)


@pytest.mark.django_db
def test_document_types_without_renewal_are_excluded():
    doc = make_document(make_vendor(), 5, renewal=False)

    send_expiry_reminders(today=TODAY)

    assert mail.outbox == []
    assert doc.document_type.reminder_days_before is None
    assert doc.validity_status == "VALID"


@pytest.mark.django_db
def test_reminder_days_required_only_with_renewal():
    catalog = DocumentCatalog(
        code="X", name="X", requires_renewal=True, reminder_days_before=None
    )
    with pytest.raises(ValidationError):
        catalog.clean()
    catalog.requires_renewal = False
    catalog.clean()


@pytest.mark.django_db
def test_last_notice_at_7_days_and_missed_first_is_skipped():
    vendor = make_vendor()
    make_document(vendor, 7)
    make_document(vendor, 5)

    send_expiry_reminders(today=TODAY)

    assert stages() == [ExpiryReminderLog.STAGE_SECOND] * 2
    assert "ULTIMO AVVISO" in mail.outbox[0].body


@pytest.mark.django_db
def test_first_then_last_notice_over_time():
    vendor = make_vendor()
    make_document(vendor, 30)

    send_expiry_reminders(today=TODAY)
    send_expiry_reminders(today=TODAY + timedelta(days=10))
    send_expiry_reminders(today=TODAY + timedelta(days=23))
    send_expiry_reminders(today=TODAY + timedelta(days=24))

    assert len(mail.outbox) == 2
    assert sorted(stages()) == ["FIRST", "SECOND"]


@pytest.mark.django_db
def test_renewed_document_restarts_reminders():
    vendor = make_vendor()
    doc = make_document(vendor, 5)
    send_expiry_reminders(today=TODAY)

    doc.expiry_date = TODAY + timedelta(days=370)
    doc.save()
    send_expiry_reminders(today=TODAY + timedelta(days=345))

    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_competences_included_only_if_possessed_and_renewable():
    vendor = make_vendor()
    make_competence(vendor, 30)
    make_competence(vendor, 30, has_competence=False)
    make_competence(vendor, 30, renewal=False)

    send_expiry_reminders(today=TODAY)

    log = ExpiryReminderLog.objects.get()
    assert log.item_kind == ExpiryReminderLog.KIND_COMPETENCE
    assert "Patentino PES/PAV" in mail.outbox[0].body


@pytest.mark.django_db
def test_excluded_vendors_and_documents():
    make_document(make_vendor(expiry_notifications_enabled=False), 30)
    make_document(make_vendor(email=""), 30)
    make_document(make_vendor(is_active=False), 30)
    make_document(make_vendor(), 30, status="UPLOADED")
    make_document(make_vendor(), -1)

    send_expiry_reminders(today=TODAY)

    assert mail.outbox == []
    assert not ExpiryReminderLog.objects.exists()


@pytest.mark.django_db
def test_one_email_per_vendor():
    vendor = make_vendor()
    make_document(vendor, 30)
    make_document(vendor, 6)
    make_competence(vendor, 20)

    send_expiry_reminders(today=TODAY)

    assert len(mail.outbox) == 1
    assert ExpiryReminderLog.objects.count() == 3


@pytest.mark.django_db
def test_failed_send_is_retried_and_does_not_block_others():
    failing = make_vendor(name="AAA Fallisce", email="ko@example.invalid")
    make_document(failing, 30)
    make_document(make_vendor(name="BBB Ok", email="ok@example.invalid"), 30)

    def flaky_send(**kwargs):
        if kwargs["to"] == ["ko@example.invalid"]:
            raise ConnectionRefusedError("SMTP giù")
        return send_templated_email(**kwargs)

    with patch(
        "vendor_management_system.vendors.expiry_reminders.send_templated_email",
        side_effect=flaky_send,
    ):
        summary = send_expiry_reminders(today=TODAY)

    assert [v.name for v, _ in summary["failed"]] == ["AAA Fallisce"]
    assert [m.to for m in mail.outbox] == [["ok@example.invalid"]]
    assert not ExpiryReminderLog.objects.filter(vendor=failing).exists()

    send_expiry_reminders(today=TODAY)
    assert mail.outbox[-1].to == ["ko@example.invalid"]


@pytest.mark.django_db
def test_dry_run_command_sends_nothing():
    make_document(make_vendor(name="Fornitore Prova"), 30)
    out = StringIO()

    call_command(
        "send_expiry_reminders",
        "--dry-run",
        "--date",
        "2026-10-01",
        stdout=out,
    )

    assert "Fornitore Prova" in out.getvalue()
    assert mail.outbox == []
    assert not ExpiryReminderLog.objects.exists()


@pytest.mark.django_db
def test_celery_task_returns_summary():
    make_document(make_vendor(), 30)

    with patch(
        "vendor_management_system.vendors.expiry_reminders.timezone.now",
        return_value=datetime(2026, 10, 1, 7, 0),
    ):
        result = send_expiry_reminders_task.apply().get()

    assert result == {"sent": 1, "items": 1, "failed": 0}


@pytest.mark.django_db
def test_runs_without_timezone_support(settings):
    # Su test USE_TZ=False: now() è naive e localdate() solleverebbe errore.
    settings.USE_TZ = False

    summary = send_expiry_reminders()

    assert summary["failed"] == []


@pytest.mark.django_db
def test_reminder_log_admin_is_read_only(admin_client):
    make_document(make_vendor(name="Fornitore Storico"), 30)
    send_expiry_reminders(today=TODAY)

    response = admin_client.get("/admin/vendors/expiryreminderlog/")

    assert response.status_code == 200
    assert "Fornitore Storico" in response.content.decode()
    add = admin_client.get("/admin/vendors/expiryreminderlog/add/")
    assert add.status_code == 403


@pytest.mark.parametrize("days", [9, 91])
def test_reminder_days_before_limits(days):
    field = DocumentCatalog._meta.get_field("reminder_days_before")
    with pytest.raises(ValidationError):
        field.run_validators(days)
