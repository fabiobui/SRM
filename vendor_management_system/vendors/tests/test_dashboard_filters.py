"""Filtri a tendina della dashboard (lato server, usati dall'export) e dati
che la pagina passa ai menù."""

import io
import json
import re

import openpyxl
import pytest
from django.test import RequestFactory

from vendor_management_system.portal.tests.factories import (
    CategoryFactory,
    CompetenceFactory,
    ServiceTypeFactory,
    VendorCompetenceFactory,
    VendorServiceFactory,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors import dashboard_filters
from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.tests.factories import VendorFactory


def _qs(**params):
    request = RequestFactory().get("/", params)
    return dashboard_filters.apply_dropdown_filters(
        Vendor.objects.all(), request.GET
    )


@pytest.mark.django_db
def test_dentro_un_campo_i_valori_sono_in_or():
    a = VendorFactory(vendor_type="Società")
    b = VendorFactory(vendor_type="Professionista")
    VendorFactory(vendor_type="Dipendente")

    trovati = _qs(dd_vendor_types="Società,Professionista")

    assert set(trovati) == {a, b}


@pytest.mark.django_db
def test_tra_campi_diversi_vale_l_and():
    giusto = VendorFactory(vendor_type="Società")
    altro_tipo = VendorFactory(vendor_type="Professionista")
    servizio = ServiceTypeFactory()
    VendorServiceFactory(vendor=giusto, service_type=servizio)
    VendorServiceFactory(vendor=altro_tipo, service_type=servizio)

    trovati = _qs(dd_vendor_types="Società", dd_services=servizio.name)

    assert list(trovati) == [giusto]


@pytest.mark.django_db
def test_classificazione_principale_o_aggiuntiva():
    principale = CategoryFactory()
    aggiuntiva = CategoryFactory()
    con_principale = VendorFactory(category=principale)
    con_aggiuntiva = VendorFactory()
    con_aggiuntiva.additional_categories.add(aggiuntiva)
    VendorFactory(category=CategoryFactory())

    trovati = _qs(dd_classifications=f"{principale.name},{aggiuntiva.name}")

    assert set(trovati) == {con_principale, con_aggiuntiva}


@pytest.mark.django_db
def test_qualifica_competenza_e_certificazione_non_si_confondono():
    requisito = CompetenceFactory()
    come_qualifica = VendorFactory()
    come_competenza = VendorFactory()
    certificato = VendorFactory()
    VendorCompetenceFactory(
        vendor=come_qualifica,
        competence=requisito,
        is_qualifica=True,
        has_competence=True,
    )
    VendorCompetenceFactory(
        vendor=come_competenza,
        competence=requisito,
        is_competenza=True,
        has_competence=True,
    )
    VendorCompetenceFactory(
        vendor=certificato, competence=requisito, has_certification=True
    )

    assert list(_qs(dd_qualifiche=requisito.name)) == [come_qualifica]
    assert list(_qs(dd_competenze=requisito.name)) == [come_competenza]
    assert list(_qs(dd_certifications=requisito.name)) == [certificato]


@pytest.mark.django_db
def test_valutazione_finale():
    positivo = VendorFactory()
    Vendor.objects.filter(pk=positivo.pk).update(
        vendor_final_evaluation="POSITIVO"
    )
    VendorFactory()

    assert list(_qs(dd_final_evaluations="POSITIVO")) == [positivo]


@pytest.mark.django_db
def test_ricerca_su_codice_embyon_ragione_sociale_piva_e_cf():
    vendor = VendorFactory(
        name="Rossi Impianti",
        old_code="E1234",
        vat_number="01234567890",
        fiscal_code="RSSMRA80A01H501U",
    )
    VendorFactory(name="Altro", vat_number="99999999999", email="rossi@x.it")

    for termine in ("E1234", "rossi imp", "0123456", "rssmra80"):
        trovati = dashboard_filters.apply_search(Vendor.objects.all(), termine)
        assert list(trovati) == [vendor], termine
    # L'email non fa parte dei campi cercati.
    assert not dashboard_filters.apply_search(
        Vendor.objects.all(), "rossi@x.it"
    ).exists()


@pytest.mark.django_db
def test_export_excel_rispetta_filtri_e_ricerca(client):
    admin = User.objects.create_user(
        email="export@example.invalid", password="x-pass-1234", role="admin"
    )
    giusto = VendorFactory(name="Alfa Srl", vendor_type="Società")
    VendorFactory(name="Alfa Studio", vendor_type="Professionista")
    VendorFactory(name="Beta Srl", vendor_type="Società")
    client.force_login(admin)

    response = client.get(
        "/vendors/export-excel/",
        {"dd_vendor_types": "Società", "search": "alfa"},
    )

    righe = list(
        openpyxl.load_workbook(io.BytesIO(response.content)).active.values
    )
    assert [r[0] for r in righe[1:]] == [giusto.name]


@pytest.mark.django_db
def test_dashboard_espone_codice_embyon_e_classificazioni(client):
    admin = User.objects.create_user(
        email="dash@example.invalid", password="x-pass-1234", role="admin"
    )
    principale = CategoryFactory()
    aggiuntiva = CategoryFactory()
    vendor = VendorFactory(old_code="E777", category=principale)
    vendor.additional_categories.add(aggiuntiva)
    client.force_login(admin)

    html = client.get("/vendors/dashboard/").content.decode()
    dati = re.search(r"const vendorsData = (\[.*?\]);\n", html, re.S).group(1)
    riga = next(v for v in json.loads(dati) if v["vendor_code"] == vendor.pk)

    assert riga["old_code"] == "E777"
    assert riga["classifications"] == [principale.name, aggiuntiva.name]
    assert 'id="dropdown-filters-container"' in html
    assert "Aggiungi fornitore prospetto" in html
