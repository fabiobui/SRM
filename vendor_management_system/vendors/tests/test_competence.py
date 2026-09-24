"""Test della copertura territoriale dei fornitori.

Coprono il modulo condiviso `vendors/competence.py`, che e' l'unico punto
di verita' usato da admin, portale, dashboard, export e filtri.
"""

import pytest

from vendor_management_system.vendors import competence
from vendor_management_system.vendors.models import Country, Province, Region
from vendor_management_system.vendors.tests.factories import (
    CountryFactory,
    ProvinceFactory,
    RegionFactory,
    VendorFactory,
)


def _province_di(codice_regione):
    return sorted(
        Province.objects.filter(region__code=codice_regione).values_list(
            "code", flat=True
        )
    )


# --------------------------------------------------------------------------
# Scrittura
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_copertura_province_roundtrip(geografia_italia):
    vendor = VendorFactory()

    competence.set_vendor_competence(
        vendor, province_codes=["MI", "BG"], country_codes=[]
    )

    assert competence.current_selection(vendor)["provinces"] == ["BG", "MI"]
    assert Province.objects.get(code="MI").competent_vendors.first() == vendor


@pytest.mark.django_db
def test_nazione_estera_salvata_nel_campo_dedicato(geografia_italia):
    vendor = VendorFactory()

    competence.set_vendor_competence(
        vendor, province_codes=[], country_codes=["FR", "DE"]
    )

    assert competence.current_selection(vendor)["countries"] == ["DE", "FR"]


@pytest.mark.django_db
def test_italia_non_finisce_mai_fra_le_nazioni(geografia_italia):
    """Altrimenti ci sarebbero due verita' in contraddizione sulla
    copertura italiana: le province e il flag di nazione."""
    vendor = VendorFactory()

    competence.set_vendor_competence(
        vendor, province_codes=[], country_codes=["IT", "FR"]
    )

    assert competence.current_selection(vendor)["countries"] == ["FR"]


@pytest.mark.django_db
def test_codici_sconosciuti_scartati_in_silenzio(geografia_italia):
    """`set_vendor_competence` e' tollerante di proposito: e' anche il
    percorso di approvazione di proposte con codici congelati tempo fa."""
    vendor = VendorFactory()

    competence.set_vendor_competence(
        vendor, province_codes=["MI", "ZZZ"], country_codes=["XX"]
    )

    selezione = competence.current_selection(vendor)
    assert selezione["provinces"] == ["MI"]
    assert selezione["countries"] == []


@pytest.mark.django_db
def test_province_disattivate_scartate(geografia_italia):
    vendor = VendorFactory()
    Province.objects.filter(code="BG").update(is_active=False)

    competence.set_vendor_competence(
        vendor, province_codes=["MI", "BG"], country_codes=[]
    )

    assert competence.current_selection(vendor)["provinces"] == ["MI"]


@pytest.mark.django_db
def test_selezione_vuota_azzera_la_copertura(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=["MI"], country_codes=["FR"]
    )

    competence.set_vendor_competence(
        vendor, province_codes=[], country_codes=[]
    )

    assert competence.current_selection(vendor) == {
        "provinces": [],
        "countries": [],
    }


# --------------------------------------------------------------------------
# Stato derivato delle regioni
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_region_coverage_tri_stato(geografia_italia):
    lombarde = _province_di("LOM")

    stato_piena = competence.region_coverage(lombarde)
    stato_parziale = competence.region_coverage(lombarde[:1])
    stato_vuoto = competence.region_coverage([])

    assert stato_piena["LOM"] == "full"
    assert stato_parziale["LOM"] == "partial"
    assert stato_vuoto["LOM"] == "none"


@pytest.mark.django_db
def test_regione_piena_ignora_le_province_disattivate(geografia_italia):
    """Una provincia disattivata non deve impedire a una regione di
    risultare coperta per intero: il catalogo attivo e' il riferimento."""
    lombarde = _province_di("LOM")
    Province.objects.filter(code=lombarde[0]).update(is_active=False)

    stato = competence.region_coverage(lombarde[1:])

    assert stato["LOM"] == "full"


# --------------------------------------------------------------------------
# Payload compatto per la dashboard
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_codici_usa_la_sentinella_su_copertura_totale(geografia_italia):
    vendor = VendorFactory()
    tutte = list(
        Province.objects.filter(is_active=True).values_list("code", flat=True)
    )
    competence.set_vendor_competence(
        vendor, province_codes=tutte, country_codes=[]
    )

    codici = competence.vendor_competence_codes(vendor)

    assert codici["provinces"] == [competence.TUTTE]
    assert codici["regions"] == [competence.TUTTE]


@pytest.mark.django_db
def test_codici_derivano_le_regioni_toccate(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=["MI", "RA"], country_codes=["FR"]
    )

    codici = competence.vendor_competence_codes(vendor)

    assert codici["provinces"] == ["MI", "RA"]
    assert codici["regions"] == ["EMR", "LOM"]
    assert codici["countries"] == ["FR"]


# --------------------------------------------------------------------------
# Riepilogo leggibile
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_riepilogo_vuoto(geografia_italia):
    assert competence.summarize_selection([], []) == []
    assert competence.format_selection([], []) == "—"


@pytest.mark.django_db
def test_riepilogo_copertura_totale(geografia_italia):
    tutte = list(
        Province.objects.filter(is_active=True).values_list("code", flat=True)
    )

    righe = competence.summarize_selection(tutte, [])

    assert righe == [f"Italia: tutte le regioni ({len(tutte)} province)"]


@pytest.mark.django_db
def test_riepilogo_regione_intera_e_parziale(geografia_italia):
    selezione = _province_di("LOM") + ["RA", "RN"]

    righe = competence.summarize_selection(selezione, [])

    assert len(righe) == 1
    assert "Lombardia (tutte)" in righe[0]
    assert "Emilia-Romagna: Ravenna, Rimini" in righe[0]


@pytest.mark.django_db
def test_riepilogo_nazioni_estere(geografia_italia):
    righe = competence.summarize_selection([], ["DE", "FR"])

    assert righe == ["Estero: Francia, Germania"]


@pytest.mark.django_db
def test_riepilogo_non_contiene_codici(geografia_italia):
    """Il riepilogo finisce nel diff mostrato al backoffice: deve essere
    leggibile, non un elenco di sigle."""
    testo = competence.format_selection(["MI"], ["FR"])

    assert "Milano" in testo
    assert "Francia" in testo
    assert "MI" not in testo.replace("Milano", "")


# --------------------------------------------------------------------------
# Filtri
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_filtro_per_regione_non_duplica_i_fornitori(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=_province_di("LOM"), country_codes=[]
    )

    trovati = competence.filter_by_competence(
        VendorFactory._meta.model.objects.all(), regions=["LOM"]
    )

    assert trovati.count() == 1


@pytest.mark.django_db
def test_filtro_per_nazione_copre_entrambi_i_lati(geografia_italia):
    modello = VendorFactory._meta.model
    italiano = VendorFactory()
    francese = VendorFactory()
    competence.set_vendor_competence(
        italiano, province_codes=["MI"], country_codes=[]
    )
    competence.set_vendor_competence(
        francese, province_codes=[], country_codes=["FR"]
    )

    per_italia = competence.filter_by_competence(
        modello.objects.all(), countries=["IT"]
    )
    per_francia = competence.filter_by_competence(
        modello.objects.all(), countries=["FR"]
    )

    assert list(per_italia) == [italiano]
    assert list(per_francia) == [francese]


@pytest.mark.django_db
def test_filtro_vuoto_non_tocca_il_queryset(geografia_italia):
    modello = VendorFactory._meta.model
    VendorFactory()

    assert competence.filter_by_competence(modello.objects.all()).count() == 1


# --------------------------------------------------------------------------
# Aggregazioni
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_aggregazione_conta_il_fornitore_una_volta_per_regione(
    geografia_italia,
):
    """Un fornitore su tutte le province lombarde vale 1 in Lombardia,
    non 12: senza `distinct=True` il conteggio sarebbe moltiplicato."""
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=_province_di("LOM"), country_codes=[]
    )

    per_regione = competence.competence_aggregations()["by_region"]

    assert per_regione == [{"region": "Lombardia", "code": "LOM", "count": 1}]


@pytest.mark.django_db
def test_aggregazione_conta_in_ogni_regione_coperta(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=["MI", "RA", "RM"], country_codes=[]
    )

    per_regione = competence.competence_aggregations()["by_region"]

    assert {r["code"] for r in per_regione} == {"LOM", "EMR", "LAZ"}
    assert sum(r["count"] for r in per_regione) == 3


@pytest.mark.django_db
def test_aggregazione_province_e_nazioni(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=["MI"], country_codes=["FR"]
    )

    aggregati = competence.competence_aggregations()

    assert aggregati["by_province"] == [
        {
            "province": "Milano",
            "code": "MI",
            "region": "LOM",
            "region_name": "Lombardia",
            "count": 1,
        }
    ]
    assert aggregati["by_competence_country"] == [
        {"country": "Francia", "code": "FR", "count": 1}
    ]


# --------------------------------------------------------------------------
# Albero per il selettore
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_albero_distingue_nazioni_navigabili_e_foglie(geografia_italia):
    albero = competence.geo_tree_data()
    per_codice = {n["code"]: n for n in albero}

    assert per_codice["IT"]["leaf"] is False
    assert len(per_codice["IT"]["regions"]) == 20
    assert per_codice["FR"]["leaf"] is True
    assert per_codice["FR"]["regions"] == []


@pytest.mark.django_db
def test_albero_esclude_le_righe_disattivate(geografia_italia):
    Province.objects.filter(code="MI").update(is_active=False)

    albero = competence.geo_tree_data()
    lombardia = next(
        reg for naz in albero for reg in naz["regions"] if reg["code"] == "LOM"
    )

    assert "MI" not in {p["code"] for p in lombardia["provinces"]}


@pytest.mark.django_db
def test_albero_con_factory_generiche():
    """L'albero non e' legato all'Italia: una qualunque nazione con
    regioni a catalogo diventa navigabile.

    Nessuna asserzione sul totale: sulla suite Docker le migrazioni sono
    rigiocate, quindi l'Italia e' gia' a catalogo.
    """
    regione = RegionFactory()
    ProvinceFactory(region=regione)
    foglia = CountryFactory()

    albero = {n["code"]: n for n in competence.geo_tree_data()}

    assert albero[regione.country.code]["leaf"] is False
    assert albero[foglia.code]["leaf"] is True


@pytest.mark.django_db
def test_nazioni_foglia_escludono_quelle_con_regioni(geografia_italia):
    foglie = set(competence.leaf_countries_qs().values_list("code", flat=True))

    assert "IT" not in foglie
    assert "FR" in foglie
    assert len(foglie) == Country.objects.count() - 1


@pytest.mark.django_db
def test_regione_disattivata_esclusa_dalle_mappe(geografia_italia):
    Region.objects.filter(code="LOM").update(is_active=False)

    mappe = competence.geo_maps()

    assert "LOM" not in mappe["nome_regione"]
