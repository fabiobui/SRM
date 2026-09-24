"""Test del selettore territoriale delle zone di competenza.

Due test qui valgono piu' degli altri e non vanno mai rilassati:

* `test_hanno_un_name_solo_le_foglie` fissa l'invariante da cui dipende il
  fatto che un errore nella logica tri-stato del JavaScript non possa
  corrompere i dati salvati;
* `test_ogni_bottone_ha_type_button` evita che un click su "Seleziona
  tutto" salvi il fornitore, perche' un <button> senza `type` e' `submit`
  e `vendor_form_guard.js` lo lascia passare.
"""

import re

import pytest
from django import forms
from django.http import QueryDict

from vendor_management_system.vendors.models import Country, Province
from vendor_management_system.vendors.widgets import (
    CompetenceAreaField,
    CompetenceAreaSelectorWidget,
)

NOME = "competence_areas"


def _render(value=None):
    widget = CompetenceAreaSelectorWidget()
    return widget.render(NOME, value, attrs={})


def _post(province=(), nazioni=()):
    dati = QueryDict(mutable=True)
    dati.setlist(NOME + "_provinces", list(province))
    dati.setlist(NOME + "_countries", list(nazioni))
    return dati


# --------------------------------------------------------------------------
# Invarianti strutturali del markup
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_hanno_un_name_solo_le_foglie(geografia_italia):
    html = _render()

    attesi_province = Province.objects.filter(is_active=True).count()
    attese_nazioni = Country.objects.filter(
        is_active=True, regions__isnull=True
    ).count()

    assert html.count(f'name="{NOME}_provinces"') == attesi_province
    assert html.count(f'name="{NOME}_countries"') == attese_nazioni

    # Nessuna checkbox derivata (regione / nazione navigabile) deve avere
    # un name: non devono mai raggiungere il server.
    for tag in re.findall(r"<input[^>]*data-geo-derived[^>]*>", html):
        assert "name=" not in tag


@pytest.mark.django_db
def test_ogni_bottone_ha_type_button(geografia_italia):
    html = _render()

    bottoni = re.findall(r"<button[^>]*>", html)
    assert bottoni
    for tag in bottoni:
        assert 'type="button"' in tag, tag


@pytest.mark.django_db
def test_fallback_senza_javascript(geografia_italia):
    html = _render()

    assert "<noscript>" in html
    assert "is-collapsed { display: block !important; }" in html


@pytest.mark.django_db
def test_nazioni_estere_in_una_sezione_separata(geografia_italia):
    html = _render()

    assert 'data-geo-section="foreign"' in html
    assert "Altre nazioni" in html
    # L'Italia e' navigabile, quindi sta nell'albero, non fra le foglie.
    assert 'data-geo-node="country" data-geo-id="IT"' in html


@pytest.mark.django_db
def test_la_selezione_iniziale_e_gia_spuntata(geografia_italia):
    html = _render({"provinces": ["MI"], "countries": ["FR"]})

    spuntate = re.findall(r'<input[^>]*value="([A-Z]+)"[^>]*checked', html)
    assert set(spuntate) == {"MI", "FR"}


@pytest.mark.django_db
def test_messaggio_se_il_catalogo_e_vuoto():
    """Il catalogo va svuotato esplicitamente: sulla suite Docker le
    migrazioni sono rigiocate e lo hanno gia' popolato."""
    Country.objects.all().delete()

    html = _render()

    assert "seed_geography" in html


@pytest.mark.django_db
def test_albero_renderizzato_in_poche_query(
    geografia_italia, django_assert_num_queries
):
    with django_assert_num_queries(3):
        _render()


# --------------------------------------------------------------------------
# Lettura del POST
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_legge_entrambi_i_gruppi_dal_post():
    widget = CompetenceAreaSelectorWidget()

    valore = widget.value_from_datadict(_post(["MI", "BG"], ["FR"]), {}, NOME)

    assert valore == {"provinces": ["MI", "BG"], "countries": ["FR"]}


@pytest.mark.django_db
def test_post_vuoto_significa_nessuna_selezione():
    """Deselezionare tutto non invia nulla: non va interpretato come
    "campo non toccato", altrimenti la copertura non si potrebbe mai
    azzerare."""
    widget = CompetenceAreaSelectorWidget()

    assert widget.value_from_datadict(QueryDict(), {}, NOME) == {
        "provinces": [],
        "countries": [],
    }
    assert widget.value_omitted_from_data(QueryDict(), {}, NOME) is False


# --------------------------------------------------------------------------
# Validazione
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_clean_restituisce_codici_ordinati(geografia_italia):
    campo = CompetenceAreaField(required=False)

    pulito = campo.clean({"provinces": ["RM", "BG"], "countries": ["FR"]})

    assert pulito == {"provinces": ["BG", "RM"], "countries": ["FR"]}
    assert all(isinstance(c, str) for c in pulito["provinces"])


@pytest.mark.django_db
def test_clean_rifiuta_una_provincia_inesistente(geografia_italia):
    campo = CompetenceAreaField(required=False)

    with pytest.raises(forms.ValidationError):
        campo.clean({"provinces": ["ZZZ"], "countries": []})


@pytest.mark.django_db
def test_clean_rifiuta_una_provincia_disattivata(geografia_italia):
    Province.objects.filter(code="MI").update(is_active=False)
    campo = CompetenceAreaField(required=False)

    with pytest.raises(forms.ValidationError):
        campo.clean({"provinces": ["MI"], "countries": []})


@pytest.mark.django_db
def test_clean_rifiuta_l_italia_fra_le_nazioni(geografia_italia):
    """La copertura italiana si esprime solo con le province: accettare
    `IT` qui creerebbe una seconda verita' in contraddizione."""
    campo = CompetenceAreaField(required=False)

    with pytest.raises(forms.ValidationError):
        campo.clean({"provinces": [], "countries": ["IT"]})


@pytest.mark.django_db
def test_clean_accetta_selezione_vuota_se_non_obbligatorio(geografia_italia):
    campo = CompetenceAreaField(required=False)

    assert campo.clean(None) == {"provinces": [], "countries": []}


@pytest.mark.django_db
def test_clean_rifiuta_selezione_vuota_se_obbligatorio(geografia_italia):
    campo = CompetenceAreaField(required=True)

    with pytest.raises(forms.ValidationError):
        campo.clean({"provinces": [], "countries": []})


# --------------------------------------------------------------------------
# has_changed
# --------------------------------------------------------------------------


def test_has_changed_ignora_l_ordine():
    campo = CompetenceAreaField(required=False)
    prima = {"provinces": ["MI", "BG"], "countries": []}
    dopo = {"provinces": ["BG", "MI"], "countries": []}

    assert campo.has_changed(prima, dopo) is False


def test_has_changed_rileva_una_differenza():
    campo = CompetenceAreaField(required=False)

    assert campo.has_changed(
        {"provinces": ["MI"], "countries": []},
        {"provinces": ["MI"], "countries": ["FR"]},
    )


def test_has_changed_confronta_vuoto_e_none():
    campo = CompetenceAreaField(required=False)

    assert campo.has_changed(None, {"provinces": [], "countries": []}) is False
