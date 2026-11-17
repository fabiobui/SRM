import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from vendor_management_system.subcontractors.models import (
    PENDING,
    REJECTED,
    VALIDATED,
    Technician,
    TechnicianDocument,
    latest_validated_documents,
)


def _doc(technician, doc_type, status, expiry=None):
    return TechnicianDocument.objects.create(
        technician=technician,
        doc_type=doc_type,
        expiry_date=expiry,
        file=SimpleUploadedFile("a.pdf", b"x"),
        validation_status=status,
    )


@pytest.mark.django_db
def test_documento_con_scadenza_senza_data_non_e_valido(vendor_factory):
    vendor = vendor_factory()
    tech = Technician.objects.create(
        vendor=vendor, surname="Rossi", first_name="Mario"
    )
    doc = TechnicianDocument(
        technician=tech,
        doc_type="antincendio",
        file=SimpleUploadedFile("a.pdf", b"x"),
    )
    with pytest.raises(ValidationError) as exc:
        doc.clean()
    assert "expiry_date" in exc.value.message_dict


@pytest.mark.django_db
def test_solo_il_piu_recente_validato_per_tipo_e_considerato(vendor_factory):
    vendor = vendor_factory()
    tech = Technician.objects.create(
        vendor=vendor, surname="Rossi", first_name="Mario"
    )
    _doc(tech, "antincendio", VALIDATED)
    newer = _doc(tech, "antincendio", VALIDATED)
    _doc(tech, "antincendio", PENDING)
    _doc(tech, "primo_soccorso", REJECTED)

    assert latest_validated_documents(tech.documents.all()) == [newer]
