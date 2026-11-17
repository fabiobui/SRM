from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from vendor_management_system.subcontractors.models import (
    PENDING,
    VALIDATED,
    Technician,
    TechnicianDocument,
)
from vendor_management_system.vendors.expiry_reminders import due_items
from vendor_management_system.vendors.models import ExpiryReminderLog


def _subappaltatore(vendor_factory):
    return vendor_factory(vendor_type="Subappaltatore")


def _technician_doc(technician, expiry_in_days, status=VALIDATED):
    return TechnicianDocument.objects.create(
        technician=technician,
        doc_type="antincendio",
        expiry_date=timezone.localdate() + timedelta(days=expiry_in_days),
        file=SimpleUploadedFile("a.pdf", b"x"),
        validation_status=status,
    )


@pytest.mark.django_db
def test_attestato_validato_in_scadenza_genera_promemoria(vendor_factory):
    vendor = _subappaltatore(vendor_factory)
    tech = Technician.objects.create(
        vendor=vendor,
        surname="Rossi",
        first_name="Mario",
        validation_status=VALIDATED,
    )
    _technician_doc(tech, expiry_in_days=10)

    items = due_items(vendor, timezone.localdate())

    assert [item.kind for item in items] == [
        ExpiryReminderLog.KIND_TECHNICIAN_DOCUMENT
    ]


@pytest.mark.django_db
def test_documento_in_attesa_non_genera_promemoria(vendor_factory):
    vendor = _subappaltatore(vendor_factory)
    tech = Technician.objects.create(
        vendor=vendor,
        surname="Rossi",
        first_name="Mario",
        validation_status=VALIDATED,
    )
    _technician_doc(tech, expiry_in_days=10, status=PENDING)

    assert due_items(vendor, timezone.localdate()) == []


@pytest.mark.django_db
def test_rinnovo_sostituisce_il_promemoria_del_vecchio_attestato(
    vendor_factory,
):
    vendor = _subappaltatore(vendor_factory)
    tech = Technician.objects.create(
        vendor=vendor,
        surname="Rossi",
        first_name="Mario",
        validation_status=VALIDATED,
    )
    _technician_doc(tech, expiry_in_days=10)
    _technician_doc(tech, expiry_in_days=365)

    assert due_items(vendor, timezone.localdate()) == []


@pytest.mark.django_db
def test_fornitore_non_subappaltatore_non_riceve_promemoria_tecnici(
    vendor_factory,
):
    vendor = vendor_factory()
    tech = Technician.objects.create(
        vendor=vendor,
        surname="Rossi",
        first_name="Mario",
        validation_status=VALIDATED,
    )
    _technician_doc(tech, expiry_in_days=10)

    assert due_items(vendor, timezone.localdate()) == []
