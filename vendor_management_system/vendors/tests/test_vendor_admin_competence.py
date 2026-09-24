"""Test dell'integrazione delle zone di competenza nell'admin.

Copre il form fornitore (selettore territoriale al posto delle vecchie
zone nominate) e le tre tendine a cascata della changelist.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.forms.models import model_to_dict
from django.test import RequestFactory

from vendor_management_system.users.models import User
from vendor_management_system.vendors import competence
from vendor_management_system.vendors.admin import VendorAdmin, VendorAdminForm
from vendor_management_system.vendors.admin_filters import (
    CompetenceCountryFilter,
    CompetenceProvinceFilter,
    CompetenceRegionFilter,
)
from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.tests.factories import VendorFactory


def _admin():
    return VendorAdmin(Vendor, AdminSite())


def _lookups(classe_filtro, querystring=""):
    request = RequestFactory().get(f"/admin/vendors/vendor/{querystring}")
    istanza = classe_filtro(
        request, dict(request.GET.lists()), Vendor, _admin()
    )
    return [codice for codice, _etichetta in istanza.lookup_choices]


PASSWORD = "test-pass-competence"


def _login_admin(client, etichetta):
    """Crea e autentica un superuser (il modello usa l'email come
    identificativo, non uno username)."""
    utente = User.objects.create_superuser(
        email=f"{etichetta}@example.invalid",
        password=PASSWORD,
        role="admin",
    )
    client.login(email=utente.email, password=PASSWORD)
    return utente


def _payload(vendor, **extra):
    """POST minimo per `VendorAdminForm`, a partire dal fornitore."""
    dati = {
        chiave: valore
        for chiave, valore in model_to_dict(vendor).items()
        if valore not in (None, [], "")
    }
    dati.pop("competence_provinces", None)
    dati.pop("competence_countries", None)
    dati.update(extra)
    return dati


# --------------------------------------------------------------------------
# Form fornitore
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_il_form_parte_dalla_copertura_salvata(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=["MI"], country_codes=["FR"]
    )

    form = VendorAdminForm(instance=vendor)

    assert form.fields["competence_areas"].initial == {
        "provinces": ["MI"],
        "countries": ["FR"],
    }


@pytest.mark.django_db
def test_il_form_salva_la_copertura(geografia_italia):
    vendor = VendorFactory()

    form = VendorAdminForm(
        data=_payload(
            vendor,
            competence_areas_provinces=["MI", "RA"],
            competence_areas_countries=["DE"],
        ),
        instance=vendor,
    )

    assert form.is_valid(), form.errors
    form.save()
    vendor.refresh_from_db()
    assert competence.current_selection(vendor) == {
        "provinces": ["MI", "RA"],
        "countries": ["DE"],
    }


@pytest.mark.django_db
def test_il_form_puo_azzerare_la_copertura(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=["MI"], country_codes=["FR"]
    )

    form = VendorAdminForm(data=_payload(vendor), instance=vendor)

    assert form.is_valid(), form.errors
    form.save()
    vendor.refresh_from_db()
    assert competence.current_selection(vendor) == {
        "provinces": [],
        "countries": [],
    }


@pytest.mark.django_db
def test_il_form_rifiuta_una_provincia_inesistente(geografia_italia):
    vendor = VendorFactory()

    form = VendorAdminForm(
        data=_payload(vendor, competence_areas_provinces=["ZZZ"]),
        instance=vendor,
    )

    assert not form.is_valid()
    assert "competence_areas" in form.errors


@pytest.mark.django_db
def test_i_m2m_reali_non_sono_nel_form(geografia_italia):
    """Li gestisce il campo composito: lasciandoli, Django renderizzerebbe
    anche i loro widget di default accanto al selettore."""
    form = VendorAdminForm()

    assert "competence_provinces" not in form.fields
    assert "competence_countries" not in form.fields
    assert "competence_areas" in form.fields


def test_le_vecchie_zone_nominate_non_sono_piu_in_autocomplete():
    assert "competence_zones" not in VendorAdmin.autocomplete_fields


# --------------------------------------------------------------------------
# Filtri a cascata
# --------------------------------------------------------------------------


def test_i_tre_filtri_sono_registrati():
    assert CompetenceCountryFilter in VendorAdmin.list_filter
    assert CompetenceRegionFilter in VendorAdmin.list_filter
    assert CompetenceProvinceFilter in VendorAdmin.list_filter


@pytest.mark.django_db
def test_le_regioni_si_limitano_alla_nazione_scelta(geografia_italia):
    senza_filtro = _lookups(CompetenceRegionFilter)
    con_italia = _lookups(CompetenceRegionFilter, "?comp_country=IT")
    con_francia = _lookups(CompetenceRegionFilter, "?comp_country=FR")

    assert len(senza_filtro) == 20
    assert len(con_italia) == 20
    assert con_francia == []


@pytest.mark.django_db
def test_le_province_si_limitano_alla_regione_scelta(geografia_italia):
    lombarde = _lookups(CompetenceProvinceFilter, "?comp_region=LOM")

    assert "MI" in lombarde
    assert "RM" not in lombarde


@pytest.mark.django_db
def test_le_province_ripiegano_sulla_nazione_se_manca_la_regione(
    geografia_italia,
):
    italiane = _lookups(CompetenceProvinceFilter, "?comp_country=IT")

    assert len(italiane) == 107


@pytest.mark.django_db
def test_il_filtro_provincia_seleziona_i_fornitori(geografia_italia, client):
    coperto = VendorFactory()
    scoperto = VendorFactory()
    competence.set_vendor_competence(
        coperto, province_codes=["MI"], country_codes=[]
    )
    competence.set_vendor_competence(
        scoperto, province_codes=["RM"], country_codes=[]
    )
    _login_admin(client, "filtro-provincia")

    risposta = client.get("/admin/vendors/vendor/?comp_province=MI")

    assert risposta.status_code == 200
    assert list(risposta.context["cl"].result_list) == [coperto]


@pytest.mark.django_db
def test_una_combinazione_incoerente_viene_ignorata(geografia_italia, client):
    """Nazione Francia + regione Lombardia: la regione non e' fra quelle
    ammesse, quindi il filtro regione si disattiva invece di restituire
    zero risultati senza spiegazione."""
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=[], country_codes=["FR"]
    )
    _login_admin(client, "combinazione-incoerente")

    risposta = client.get(
        "/admin/vendors/vendor/?comp_country=FR&comp_region=LOM"
    )

    assert risposta.status_code == 200
    assert list(risposta.context["cl"].result_list) == [vendor]


@pytest.mark.django_db
def test_la_colonna_mostra_il_riepilogo(geografia_italia):
    vendor = VendorFactory()
    competence.set_vendor_competence(
        vendor, province_codes=["MI"], country_codes=[]
    )

    testo = _admin().competence_areas_display(vendor)

    assert "Milano" in testo
