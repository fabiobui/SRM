"""Dashboard e API con le sezioni società dei fornitori.

Filtri e ricerca della dashboard (usati anche dall'export) e API REST
espongono qualifica e Valutazione Finale per società.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from vendor_management_system.vendors.dashboard_filters import (
    apply_dropdown_filters,
    apply_search,
)
from vendor_management_system.vendors.models import (
    Vendor,
    VendorCompany,
    VendorCompanyAccount,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def vendors():
    shared = VendorFactory(sage_code="000011", name="Condiviso")
    VendorCompany.objects.create(
        vendor=shared, company_id="SICURA", qualification_status="APPROVED"
    )
    evimed = VendorCompany.objects.create(vendor=shared, company_id="EVIMED")
    VendorCompanyAccount.objects.create(
        section=evimed, company_id="EVIMED", account_code="F 6546"
    )
    legacy = VendorFactory(
        name="Senza sezioni", qualification_status="PENDING"
    )
    return shared, legacy


def _filtered(**params):
    return set(
        apply_dropdown_filters(Vendor.objects.all(), params).values_list(
            "name", flat=True
        )
    )


def test_filtro_societa_e_valutazione_sulla_stessa_sezione(vendors):
    assert _filtered(
        dd_companies="Sicura", dd_final_evaluations="POSITIVO"
    ) == {"Condiviso"}
    assert (
        _filtered(dd_companies="Evimed", dd_final_evaluations="POSITIVO")
        == set()
    )


def test_filtro_valutazione_usa_sezioni_o_fornitore(vendors):
    assert _filtered(dd_final_evaluations="DA VALUTARE") == {
        "Condiviso",
        "Senza sezioni",
    }


def test_ricerca_per_codice_sage_e_conto(vendors):
    def found(term):
        return set(
            apply_search(Vendor.objects.all(), term).values_list(
                "name", flat=True
            )
        )

    assert found("000011") == {"Condiviso"}
    assert found("F 6546") == {"Condiviso"}


@pytest.fixture
def api():
    user = get_user_model().objects.create_user(
        email="api-sezioni@example.invalid", password="x", role="admin"
    )
    client = APIClient()
    client.token = Token.objects.create(user=user).key
    return client


def test_api_qualifica_per_societa(api, vendors):
    shared, _legacy = vendors
    url = (
        reverse("vendors--qualification", args=[shared.pk])
        + f"?token={api.token}"
    )
    data = api.get(url).data
    assert {s["company"] for s in data["sections"]} == {"SICURA", "EVIMED"}

    response = api.patch(url, {"qualification_status": "REJECTED"})
    assert response.status_code == 400
    assert "company" in response.data

    response = api.patch(
        url,
        {"company": "EVIMED", "qualification_status": "REJECTED"},
        format="json",
    )
    assert response.status_code == 200, response.data
    section = shared.company_sections.get(company_id="EVIMED")
    assert section.qualification_status == "REJECTED"
    assert section.vendor_final_evaluation == "NEGATIVO"
