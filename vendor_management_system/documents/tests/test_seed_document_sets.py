"""Test per i nuovi Set Documentali Formatore/Dipendente/Consulente/
Laboratorio, creati dal comando `seed_document_sets` (AIDEV-10)."""

import pytest
from django.core.management import call_command

from vendor_management_system.documents.models import (
    DocumentCatalog,
    DocumentSet,
)

NEW_SETS = {
    "FORMATORE": {
        "CV",
        "VISURA_CAM",
        "DURC",
        "POLIZZA",
        "INF_PRIVACY",
        "ACQ-ALL2",
    },
    "DIPENDENTE": {"CV", "DOC_IDENT"},
    "CONSULENTE": {
        "CV",
        "VISURA_CAM",
        "DURC",
        "POLIZZA",
        "INF_PRIVACY",
        "ACQ-ALL2",
    },
    "LABORATORIO": {
        "VISURA_CAM",
        "DURC",
        "POLIZZA",
        "INF_PRIVACY",
        "ACQ-ALL2",
    },
}

NEW_DOCUMENT_TYPE_CODES = {"CV", "DOC_IDENT", "INF_PRIVACY", "POLIZZA"}


@pytest.fixture
def preexisting_document_types():
    """VISURA_CAM/DURC/ACQ-ALL2 sono riusati dai nuovi set: devono
    preesistere a catalogo, come dopo un normale giro di
    `populate_document_types`."""
    for code in ["VISURA_CAM", "DURC", "ACQ-ALL2"]:
        DocumentCatalog.objects.create(code=code, name=code)


@pytest.mark.django_db
def test_seed_creates_new_document_types(preexisting_document_types):
    call_command("seed_document_sets")

    codes = set(
        DocumentCatalog.objects.filter(
            code__in=NEW_DOCUMENT_TYPE_CODES
        ).values_list("code", flat=True)
    )
    assert codes == NEW_DOCUMENT_TYPE_CODES


@pytest.mark.django_db
@pytest.mark.parametrize("set_name,expected_codes", NEW_SETS.items())
def test_seed_creates_new_document_sets(
    preexisting_document_types, set_name, expected_codes
):
    call_command("seed_document_sets")

    doc_set = DocumentSet.objects.get(name=set_name)
    assert doc_set.category is None
    assert (
        set(doc_set.document_types.values_list("code", flat=True))
        == expected_codes
    )


@pytest.mark.django_db
def test_seed_is_idempotent(preexisting_document_types):
    call_command("seed_document_sets")
    call_command("seed_document_sets")

    for set_name in NEW_SETS:
        assert DocumentSet.objects.filter(name=set_name).count() == 1
    for code in NEW_DOCUMENT_TYPE_CODES:
        assert DocumentCatalog.objects.filter(code=code).count() == 1


@pytest.mark.django_db
def test_create_only_does_not_touch_existing_set(preexisting_document_types):
    call_command("seed_document_sets")

    doc_set = DocumentSet.objects.get(name="FORMATORE")
    doc_set.description = "Personalizzato da admin"
    doc_set.save(update_fields=["description"])
    doc_set.document_types.remove(DocumentCatalog.objects.get(code="POLIZZA"))

    call_command("seed_document_sets", "--create-only")

    doc_set.refresh_from_db()
    assert doc_set.description == "Personalizzato da admin"
    assert "POLIZZA" not in set(
        doc_set.document_types.values_list("code", flat=True)
    )


@pytest.mark.django_db
def test_create_only_still_creates_missing_sets(preexisting_document_types):
    DocumentSet.objects.filter(name="LABORATORIO").delete()

    call_command("seed_document_sets", "--create-only")

    doc_set = DocumentSet.objects.get(name="LABORATORIO")
    assert (
        set(doc_set.document_types.values_list("code", flat=True))
        == NEW_SETS["LABORATORIO"]
    )
