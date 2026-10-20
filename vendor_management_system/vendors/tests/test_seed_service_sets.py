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


# --- Set Servizi IGEAM (AIDEV-118) ---

IGEAM_SET_SIZES = {
    "624": 2,
    "AMB": 14,
    "CERTIFICAZIONI": 14,
    "CONSULENZA GENERALE HS": 5,
    "FORMAZIONE - ALTRI CORSI": 24,
    "FORMAZIONE - LAVORATORI/DDL": 4,
    "FORMAZIONE - PRIMO SOCCORSO": 1,
    "FORMAZIONE - ATTREZZATURE": 1,
    "FORMAZIONE - ANTINCENDIO": 3,
    "IGIENE INDUSTRIALE": 16,
    "INGEGNERIA": 15,
    "RISK": 12,
    "SICUREZZA CANTIERI": 4,
    "STRUMENTI": 8,
}


@pytest.mark.django_db
def test_creates_igeam_sets_without_category():
    call_command("seed_service_sets")

    for name, size in IGEAM_SET_SIZES.items():
        service_set = ServiceSet.objects.get(name=name)
        assert service_set.category is None
        assert service_set.service_types.count() == size


@pytest.mark.django_db
def test_igeam_sets_names_uppercase_and_services_described():
    call_command("seed_service_sets")

    igeam_sets = ServiceSet.objects.filter(name__in=IGEAM_SET_SIZES)
    assert all(s.name == s.name.upper() for s in igeam_sets)

    service = ServiceType.objects.get(code="SERV-0016")
    assert service.description.startswith("Valutazione e gestione dei rischi")
    assert (
        ServiceType.objects.filter(
            service_sets__in=igeam_sets, description__in=["", None]
        ).count()
        == 0
    )


@pytest.mark.django_db
def test_igeam_new_services_created_under_expected_parent():
    call_command("seed_service_sets")

    planimetrie = ServiceType.objects.get(
        name="PLANIMETRIE PIANO DI EMERGENZA"
    )
    assert planimetrie.parent.code == "CGHS"
    assert ServiceType.objects.get(name="CEM").parent.code == "IGIND"

    strumenti = ServiceType.objects.get(code="STRUMENTI")
    assert strumenti.parent is None
    assert strumenti.subservices.count() == 8


@pytest.mark.django_db
def test_igeam_existing_service_is_linked_not_duplicated():
    parent = ServiceType.objects.create(code="INGEGN", name="Ingegn")
    existing = ServiceType.objects.create(
        code="SERV-0008", name="Progettista antincendio", parent=parent
    )

    call_command("seed_service_sets")

    assert ServiceType.objects.filter(code="SERV-0008").count() == 1
    existing.refresh_from_db()
    assert existing.name == "Progettista antincendio"
    assert (
        existing
        in ServiceSet.objects.get(name="INGEGNERIA").service_types.all()
    )


@pytest.mark.django_db
def test_igeam_seed_is_idempotent():
    call_command("seed_service_sets")
    types_before = ServiceType.objects.count()
    sets_before = ServiceSet.objects.count()

    call_command("seed_service_sets")

    assert ServiceType.objects.count() == types_before
    assert ServiceSet.objects.count() == sets_before


@pytest.mark.django_db
def test_solo_igeam_update_riallinea_servizi_e_non_tocca_altri_set():
    call_command("seed_service_sets")
    ServiceType.objects.filter(code="SERV-0008").update(
        name="Progettista antincendio", description="Vecchia"
    )
    other = ServiceSet.objects.get(name="MEDICINA DEL LAVORO")
    other.description = "Personalizzato da admin"
    other.save(update_fields=["description"])

    call_command("seed_service_sets", "--solo-igeam", "--update-catalog")

    assert (
        ServiceType.objects.get(code="SERV-0008").name == "PROG. ANTINCENDIO"
    )
    assert ServiceType.objects.get(code="SERV-0008").description != "Vecchia"
    other.refresh_from_db()
    assert other.description == "Personalizzato da admin"


@pytest.mark.django_db
def test_scaffalature_ha_codice_nuovo_e_e_learning_resta_intatto():
    formazione = ServiceType.objects.create(code="FORM", name="Formazione")
    ServiceType.objects.create(
        code="SERV-0082", name="E-LEARNING", parent=formazione
    )

    call_command("seed_service_sets")

    assert ServiceType.objects.get(code="SERV-0082").name == "E-LEARNING"
    scaffalature = ServiceType.objects.get(code="SERV-0124")
    assert scaffalature.name == "Scaffalature - UNI EN 15635:2009"
    altri_corsi = ServiceSet.objects.get(name="FORMAZIONE - ALTRI CORSI")
    assert scaffalature in altri_corsi.service_types.all()
    assert not altri_corsi.service_types.filter(code="SERV-0082").exists()
