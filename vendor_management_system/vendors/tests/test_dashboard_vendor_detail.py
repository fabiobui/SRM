"""Scheda fornitore in sola lettura aperta dalla dashboard."""

import pytest

from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    ServiceTypeFactory,
    VendorCompetenceFactory,
    VendorServiceFactory,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors.tests.factories import (
    VendorFactory,
    VendorOperationalAttributesFactory,
)


@pytest.fixture
def operatore(db):
    return User.objects.create_user(
        email="bo-detail@example.invalid",
        password="x-pass-1234",
        role="bo_user",
    )


def _url(vendor):
    return f"/vendors/dashboard/vendor/{vendor.pk}/"


@pytest.mark.django_db
def test_scheda_mostra_le_sezioni_censite(client, operatore):
    vendor = VendorFactory(
        name="Verdi & Figli <Srl>",
        old_code="E55",
        vat_number="01234567890",
        email="verdi@example.invalid",
    )
    servizio = ServiceTypeFactory()
    VendorServiceFactory(vendor=vendor, service_type=servizio)
    requisito = CompetenceFactory()
    VendorCompetenceFactory(
        vendor=vendor, competence=requisito, is_qualifica=True
    )
    VendorOperationalAttributesFactory(vendor=vendor, total_operators=12)
    client.force_login(operatore)

    html = client.get(_url(vendor)).content.decode()

    for titolo in (
        "Informazioni base",
        "Contatti",
        "Servizi erogati",
        "Abilitazioni e requisiti professionali",
        "Documenti contrattuali",
        "Contratti",
        "Qualifica e audit",
        "Valutazioni",
        "Attributi operativi",
    ):
        assert titolo in html
    assert "E55" in html
    assert "01234567890" in html
    assert "verdi@example.invalid" in html
    assert servizio.name in html
    assert requisito.name in html
    # Il nome viene escapato: niente HTML iniettato.
    assert "Verdi &amp; Figli &lt;Srl&gt;" in html
    assert "<Srl>" not in html


@pytest.mark.django_db
def test_scheda_e_solo_lettura(client, operatore):
    vendor = VendorFactory()
    client.force_login(operatore)

    html = client.get(_url(vendor)).content.decode()

    assert "<form" not in html
    assert "<input" not in html
    assert "/admin/" not in html


@pytest.mark.django_db
def test_scheda_senza_dati_non_si_rompe(client, operatore):
    vendor = VendorFactory(address=None)
    client.force_login(operatore)

    response = client.get(_url(vendor))

    assert response.status_code == 200
    assert "Nessun dato censito" in response.content.decode()


@pytest.mark.django_db
def test_scheda_fornitore_inesistente_da_404(client, operatore):
    client.force_login(operatore)

    assert (
        client.get("/vendors/dashboard/vendor/NONESISTE/").status_code == 404
    )


@pytest.mark.django_db
def test_scheda_anonimo_non_autorizzato(client):
    vendor = VendorFactory()

    assert client.get(_url(vendor)).status_code == 401
