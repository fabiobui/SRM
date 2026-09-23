"""Test per il flag `--create-only` di `populate_document_types`, usato dal
deploy automatico per non sovrascrivere tipi documento personalizzati da
admin (vedi compose/django/start e docs/DEPLOY.md)."""

import pytest
from django.core.management import call_command

from vendor_management_system.documents.models import DocumentCatalog


@pytest.mark.django_db
def test_creates_missing_document_types():
    call_command("populate_document_types")

    durc = DocumentCatalog.objects.get(code="DURC")
    assert durc.document_category == "LEGAL"
    assert durc.is_required is True


@pytest.mark.django_db
def test_create_only_does_not_touch_existing_document_type():
    call_command("populate_document_types")

    durc = DocumentCatalog.objects.get(code="DURC")
    durc.name = "Personalizzato da admin"
    durc.save(update_fields=["name"])

    call_command("populate_document_types", "--create-only")

    durc.refresh_from_db()
    assert durc.name == "Personalizzato da admin"


@pytest.mark.django_db
def test_create_only_still_creates_missing_types():
    call_command("populate_document_types", "--create-only")

    assert DocumentCatalog.objects.filter(code="DURC").exists()


@pytest.mark.django_db
def test_default_mode_still_overwrites_existing_document_type():
    call_command("populate_document_types")

    durc = DocumentCatalog.objects.get(code="DURC")
    durc.name = "Personalizzato da admin"
    durc.save(update_fields=["name"])

    call_command("populate_document_types")

    durc.refresh_from_db()
    assert durc.name == "DURC (Documento Unico di Regolarità Contributiva)"
