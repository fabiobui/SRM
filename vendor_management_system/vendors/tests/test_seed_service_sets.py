"""Test per il flag `--create-only` di `seed_service_sets`, usato dal
deploy automatico per non sovrascrivere Set Servizi personalizzati da
admin (vedi compose/django/start e docs/DEPLOY.md)."""

import pytest
from django.core.management import call_command

from vendor_management_system.vendors.models import ServiceSet, ServiceType


@pytest.mark.django_db
def test_creates_service_set():
    call_command("seed_service_sets")

    service_set = ServiceSet.objects.get(name="STUDIO TECNICO")
    assert service_set.service_types.count() == 9


@pytest.mark.django_db
def test_create_only_does_not_touch_existing_set():
    call_command("seed_service_sets")

    service_set = ServiceSet.objects.get(name="STUDIO TECNICO")
    service_set.description = "Personalizzato da admin"
    service_set.save(update_fields=["description"])
    removed = service_set.service_types.first()
    service_set.service_types.remove(removed)

    call_command("seed_service_sets", "--create-only")

    service_set.refresh_from_db()
    assert service_set.description == "Personalizzato da admin"
    assert removed not in service_set.service_types.all()


@pytest.mark.django_db
def test_create_only_still_creates_missing_sets():
    ServiceSet.objects.filter(name="STUDIO TECNICO").delete()
    ServiceType.objects.all().delete()

    call_command("seed_service_sets", "--create-only")

    service_set = ServiceSet.objects.get(name="STUDIO TECNICO")
    assert service_set.service_types.count() == 9
