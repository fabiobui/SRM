"""Creazione rapida di un fornitore prospetto dalla dashboard."""

from unittest import mock

import pytest
from django.core import mail

from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.tests.factories import VendorFactory

URL = "/vendors/dashboard/prospect/"


@pytest.fixture(autouse=True)
def _email_non_inviate_davvero(settings):
    settings.EMAIL_REDIRECT_TO = []


@pytest.fixture
def operatore(db):
    return User.objects.create_user(
        email="bo-prospect@example.invalid",
        password="x-pass-1234",
        role="bo_user",
    )


def _dati(**extra):
    dati = {
        "name": "Nuovo Fornitore Srl",
        "vat_number": "01234567890",
        "fiscal_code": "",
        "email": "nuovo@example.invalid",
    }
    dati.update(extra)
    return dati


@pytest.mark.django_db
def test_crea_fornitore_utenza_portale_e_invito(client, operatore):
    client.force_login(operatore)

    response = client.post(URL, _dati())

    assert response.status_code == 201
    vendor = Vendor.objects.get(name="Nuovo Fornitore Srl")
    assert str(vendor.managed_by_id) == str(operatore.pk)
    assert vendor.qualification_status == "PENDING"
    assert vendor.email == "nuovo@example.invalid"
    utente = vendor.users.get()
    assert utente.role == "vendor"
    assert not utente.has_usable_password()
    assert [m.to for m in mail.outbox] == [["nuovo@example.invalid"]]
    assert response.json()["vendor_code"] == vendor.pk


@pytest.mark.django_db
def test_basta_il_codice_fiscale(client, operatore):
    client.force_login(operatore)

    response = client.post(
        URL, _dati(vat_number="", fiscal_code="RSSMRA80A01H501U")
    )

    assert response.status_code == 201
    assert Vendor.objects.get(name="Nuovo Fornitore Srl").vat_number is None


@pytest.mark.django_db
def test_senza_piva_e_codice_fiscale_non_crea_nulla(client, operatore):
    client.force_login(operatore)

    response = client.post(URL, _dati(vat_number=""))

    assert response.status_code == 400
    assert "__all__" in response.json()["errors"]
    assert not Vendor.objects.exists()


@pytest.mark.django_db
def test_ragione_sociale_ed_email_obbligatorie(client, operatore):
    client.force_login(operatore)

    response = client.post(URL, _dati(name="", email="non-una-email"))

    assert response.status_code == 400
    assert set(response.json()["errors"]) == {"name", "email"}


@pytest.mark.django_db
def test_codice_fiscale_duplicato_blocca(client, operatore):
    VendorFactory(fiscal_code="RSSMRA80A01H501U")
    client.force_login(operatore)

    response = client.post(
        URL, _dati(vat_number="", fiscal_code="rssmra80a01h501u")
    )

    assert response.status_code == 400
    assert "fiscal_code" in response.json()["errors"]


@pytest.mark.django_db
def test_email_gia_usata_da_un_utente_non_lascia_anagrafiche_orfane(
    client, operatore
):
    client.force_login(operatore)

    response = client.post(URL, _dati(email=operatore.email))

    assert response.status_code == 400
    assert "email" in response.json()["errors"]
    assert not Vendor.objects.exists()


@pytest.mark.django_db
def test_piva_duplicata_crea_comunque_con_avviso(client, operatore):
    VendorFactory(vat_number="01234567890")
    client.force_login(operatore)

    response = client.post(URL, _dati())

    assert response.status_code == 201
    assert len(response.json()["warnings"]) == 1


@pytest.mark.django_db
def test_invito_non_inviato_non_annulla_la_creazione(client, operatore):
    client.force_login(operatore)

    with mock.patch(
        "vendor_management_system.vendors.prospect.send_portal_invite",
        side_effect=RuntimeError("smtp giu"),
    ):
        response = client.post(URL, _dati())

    assert response.status_code == 201
    assert Vendor.objects.filter(name="Nuovo Fornitore Srl").exists()
    assert "Reinvia" in response.json()["warnings"][0]


@pytest.mark.django_db
def test_solo_post(client, operatore):
    client.force_login(operatore)

    assert client.get(URL).status_code == 405
