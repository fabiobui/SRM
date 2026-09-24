"""Test del comando `seed_geography`, che popola il catalogo geografico
(Nazioni, Regioni, Province) usato dalle zone di competenza dei fornitori."""

import pytest
from django.core.management import call_command

from vendor_management_system.vendors.models import Country, Province, Region

# Attesi dalle fixture geography_italy.json + geography_countries.json.
NAZIONI_ATTESE = 30
REGIONI_ATTESE = 20
PROVINCE_ATTESE = 107

PK_ITALIA = "00000000-0000-0000-0000-000000000001"


@pytest.mark.django_db
def test_crea_il_catalogo_completo():
    call_command("seed_geography")

    assert Country.objects.count() == NAZIONI_ATTESE
    assert Region.objects.count() == REGIONI_ATTESE
    assert Province.objects.count() == PROVINCE_ATTESE


@pytest.mark.django_db
def test_gerarchia_corretta():
    call_command("seed_geography")

    italia = Country.objects.get(code="IT")
    assert italia.regions.count() == REGIONI_ATTESE

    lombardia = Region.objects.get(code="LOM")
    assert lombardia.country == italia
    assert Province.objects.get(code="MI").region == lombardia


@pytest.mark.django_db
def test_nazioni_estere_senza_regioni():
    """Le nazioni diverse dall'Italia sono foglie: il selettore
    territoriale le rende selezionabili solo a livello nazione."""
    call_command("seed_geography")

    foglie = Country.objects.filter(regions__isnull=True)
    assert foglie.count() == NAZIONI_ATTESE - 1
    assert not foglie.filter(code="IT").exists()
    assert foglie.filter(code="FR").exists()


@pytest.mark.django_db
def test_pk_deterministici_dalla_fixture():
    call_command("seed_geography")

    assert str(Country.objects.get(code="IT").pk) == PK_ITALIA


@pytest.mark.django_db
def test_idempotente():
    call_command("seed_geography")
    call_command("seed_geography")

    assert Country.objects.count() == NAZIONI_ATTESE
    assert Region.objects.count() == REGIONI_ATTESE
    assert Province.objects.count() == PROVINCE_ATTESE


@pytest.mark.django_db
def test_create_only_non_sovrascrive_le_personalizzazioni():
    """`is_active`, `sort_order` e il nome possono essere stati modificati
    da un admin: un re-seed al deploy non deve riportarli indietro."""
    call_command("seed_geography")

    provincia = Province.objects.get(code="MI")
    provincia.is_active = False
    provincia.sort_order = 999
    provincia.name = "Milano (città metropolitana)"
    provincia.save()

    call_command("seed_geography", "--create-only")

    provincia.refresh_from_db()
    assert provincia.is_active is False
    assert provincia.sort_order == 999
    assert provincia.name == "Milano (città metropolitana)"


@pytest.mark.django_db
def test_senza_create_only_riallinea_il_nome():
    """Senza il flag il nome torna quello di catalogo, ma `is_active` e
    un `sort_order` scelto da un admin restano intoccati."""
    call_command("seed_geography")

    provincia = Province.objects.get(code="MI")
    provincia.is_active = False
    provincia.sort_order = 999
    provincia.name = "Nome sbagliato"
    provincia.save()

    call_command("seed_geography")

    provincia.refresh_from_db()
    assert provincia.name == "Milano"
    assert provincia.is_active is False
    assert provincia.sort_order == 999


@pytest.mark.django_db
def test_riempie_il_sort_order_mai_impostato():
    """Sui database dove la geografia era stata creata dal vecchio
    `import_geography.py` regioni e province hanno tutte il default e
    l'ordinamento ripiegherebbe su alfabetico, diverso da un database
    nuovo. Un re-seed manuale le riallinea."""
    call_command("seed_geography")
    default = Region._meta.get_field("sort_order").default
    Region.objects.update(sort_order=default)

    call_command("seed_geography")

    ordine = dict(
        Region.objects.filter(code__in=["PIE", "LOM", "EMR"]).values_list(
            "code", "sort_order"
        )
    )
    assert ordine["PIE"] < ordine["LOM"] < ordine["EMR"]


@pytest.mark.django_db
def test_create_only_non_riempie_il_sort_order():
    """Al deploy non si tocca nulla di esistente."""
    call_command("seed_geography")
    default = Region._meta.get_field("sort_order").default
    Region.objects.update(sort_order=default)

    call_command("seed_geography", "--create-only")

    assert set(Region.objects.values_list("sort_order", flat=True)) == {
        default
    }
