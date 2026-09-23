"""Test per i nuovi Set Requisiti Formatore/Consulente/Laboratorio, creati
dal comando `seed_competence_sets` (AIDEV-10)."""

import pytest
from django.core.management import call_command

from vendor_management_system.vendors.models import Competence, CompetenceSet

NEW_SETS = {
    "FORMATORE": {"REQ-023", "REQ-024", "REQ-021"},
    "CONSULENTE": {"REQ-023", "REQ-024"},
    "LABORATORIO": {"REQ-023", "REQ-024"},
}


@pytest.fixture
def formatore_requirement():
    """REQ-021 è riusato dal set FORMATORE: deve preesistere a catalogo,
    come dopo un normale giro di `populate_competences`."""
    return Competence.objects.create(
        code="REQ-021",
        name="Formazione Formatori",
        competence_category="OTHER",
    )


@pytest.mark.django_db
def test_seed_creates_new_competences(formatore_requirement):
    call_command("seed_competence_sets")

    itp = Competence.objects.get(code="REQ-023")
    assert itp.name == "Idoneità Tecnico Professionale"

    accreditamento = Competence.objects.get(code="REQ-024")
    assert accreditamento.name == "Accreditamento"


@pytest.mark.django_db
@pytest.mark.parametrize("set_name,expected_codes", NEW_SETS.items())
def test_seed_creates_new_competence_sets(
    formatore_requirement, set_name, expected_codes
):
    call_command("seed_competence_sets")

    comp_set = CompetenceSet.objects.get(name=set_name)
    assert comp_set.category is None
    assert (
        set(comp_set.competences.values_list("code", flat=True))
        == expected_codes
    )


@pytest.mark.django_db
def test_seed_is_idempotent(formatore_requirement):
    call_command("seed_competence_sets")
    call_command("seed_competence_sets")

    for set_name in NEW_SETS:
        assert CompetenceSet.objects.filter(name=set_name).count() == 1
    assert Competence.objects.filter(code="REQ-023").count() == 1
    assert Competence.objects.filter(code="REQ-024").count() == 1


@pytest.mark.django_db
def test_create_only_does_not_touch_existing_set(formatore_requirement):
    call_command("seed_competence_sets")

    comp_set = CompetenceSet.objects.get(name="CONSULENTE")
    comp_set.description = "Personalizzato da admin"
    comp_set.save(update_fields=["description"])
    comp_set.competences.remove(Competence.objects.get(code="REQ-024"))

    call_command("seed_competence_sets", "--create-only")

    comp_set.refresh_from_db()
    assert comp_set.description == "Personalizzato da admin"
    assert "REQ-024" not in set(
        comp_set.competences.values_list("code", flat=True)
    )


@pytest.mark.django_db
def test_create_only_still_creates_missing_sets(formatore_requirement):
    CompetenceSet.objects.filter(name="LABORATORIO").delete()

    call_command("seed_competence_sets", "--create-only")

    comp_set = CompetenceSet.objects.get(name="LABORATORIO")
    assert (
        set(comp_set.competences.values_list("code", flat=True))
        == NEW_SETS["LABORATORIO"]
    )
