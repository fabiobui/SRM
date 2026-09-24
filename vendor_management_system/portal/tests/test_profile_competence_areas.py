"""Zone di competenza nel flusso di proposta modifiche.

Il fornitore propone la propria copertura territoriale; il back-office la
approva. La copertura vive in due M2M, quindi non passa dal `setattr`
generico di `apply_to_vendor`: il test che conta davvero e'
`test_approvazione_applica_le_zone`, perche' se il ramo dedicato finisse
dopo la guardia `hasattr` la richiesta risulterebbe APPROVED senza che le
zone cambino, e senza alcun errore.
"""

import json

import pytest
from django.urls import reverse

from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import VendorUserFactory
from vendor_management_system.portal.tests.test_profile_change_request import (
    PASSWORD,
    _valid_profile_payload,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors import competence
from vendor_management_system.vendors.models import Province

BO_PASSWORD = "test-pass-bo-competence"


def _login_vendor(client):
    utente = VendorUserFactory(password=PASSWORD)
    client.login(email=utente.email, password=PASSWORD)
    return utente


def _login_bo(client, etichetta="bo-competence"):
    utente = User.objects.create_user(
        email=f"{etichetta}@example.invalid",
        password=BO_PASSWORD,
        role="bo_user",
    )
    client.login(email=utente.email, password=BO_PASSWORD)
    return utente


def _proponi(client, vendor, **overrides):
    risposta = client.post(
        reverse("portal:my-profile-change"),
        _valid_profile_payload(vendor, **overrides),
    )
    return risposta


# --------------------------------------------------------------------------
# Creazione della proposta
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_nessuna_modifica_nessuna_chiave_nel_diff(geografia_italia, client):
    utente = _login_vendor(client)
    competence.set_vendor_competence(
        utente.vendor, province_codes=["MI"], country_codes=[]
    )

    _proponi(client, utente.vendor, name="Nome diverso")

    richiesta = VendorChangeRequest.objects.get()
    assert "competence_areas" not in richiesta.changes


@pytest.mark.django_db
def test_la_proposta_congela_frasi_leggibili_e_codici(
    geografia_italia, client
):
    utente = _login_vendor(client)

    _proponi(
        client,
        utente.vendor,
        competence_areas_provinces=["MI", "RA"],
        competence_areas_countries=["DE"],
    )

    payload = VendorChangeRequest.objects.get().changes["competence_areas"]
    assert isinstance(payload["new"], str)
    assert "Milano" in payload["new"]
    assert "Germania" in payload["new"]
    assert payload["new_codes"] == {
        "provinces": ["MI", "RA"],
        "countries": ["DE"],
    }
    assert payload["old"] == "—"


@pytest.mark.django_db
def test_il_diff_e_serializzabile_in_json(geografia_italia, client):
    """`VendorChangeRequest.changes` e' un JSONField senza
    DjangoJSONEncoder: un UUID o un QuerySet che ci finisse dentro farebbe
    esplodere il salvataggio."""
    utente = _login_vendor(client)

    _proponi(client, utente.vendor, competence_areas_provinces=["MI"])

    json.dumps(VendorChangeRequest.objects.get().changes)


@pytest.mark.django_db
def test_una_provincia_inesistente_viene_rifiutata(geografia_italia, client):
    utente = _login_vendor(client)

    risposta = _proponi(
        client, utente.vendor, competence_areas_provinces=["ZZZ"]
    )

    assert risposta.status_code == 200
    assert not VendorChangeRequest.objects.exists()


@pytest.mark.django_db
def test_l_italia_fra_le_nazioni_viene_rifiutata(geografia_italia, client):
    utente = _login_vendor(client)

    risposta = _proponi(
        client, utente.vendor, competence_areas_countries=["IT"]
    )

    assert risposta.status_code == 200
    assert not VendorChangeRequest.objects.exists()


@pytest.mark.django_db
def test_la_proposta_non_tocca_il_fornitore(geografia_italia, client):
    utente = _login_vendor(client)

    _proponi(client, utente.vendor, competence_areas_provinces=["MI"])

    utente.vendor.refresh_from_db()
    assert competence.current_selection(utente.vendor)["provinces"] == []


# --------------------------------------------------------------------------
# Approvazione
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_approvazione_applica_le_zone(geografia_italia, client):
    utente = _login_vendor(client)
    _proponi(
        client,
        utente.vendor,
        name="Nome nuovo",
        competence_areas_provinces=["MI", "RA"],
        competence_areas_countries=["FR"],
    )
    richiesta = VendorChangeRequest.objects.get()
    revisore = _login_bo(client)

    richiesta.apply_to_vendor(reviewer=revisore)

    utente.vendor.refresh_from_db()
    assert competence.current_selection(utente.vendor) == {
        "provinces": ["MI", "RA"],
        "countries": ["FR"],
    }
    # Il `continue` del ramo dedicato non deve interrompere il resto del
    # diff: anche il campo scalare della stessa richiesta va applicato.
    assert utente.vendor.name == "Nome nuovo"


@pytest.mark.django_db
def test_approvazione_puo_azzerare_le_zone(geografia_italia, client):
    utente = _login_vendor(client)
    competence.set_vendor_competence(
        utente.vendor, province_codes=["MI"], country_codes=[]
    )
    _proponi(
        client,
        utente.vendor,
        competence_areas_provinces=[],
        competence_areas_countries=[],
    )
    richiesta = VendorChangeRequest.objects.get()
    revisore = _login_bo(client)

    richiesta.apply_to_vendor(reviewer=revisore)

    utente.vendor.refresh_from_db()
    assert competence.current_selection(utente.vendor)["provinces"] == []


@pytest.mark.django_db
def test_approvazione_ignora_province_sparite_nel_frattempo(
    geografia_italia, client
):
    utente = _login_vendor(client)
    _proponi(client, utente.vendor, competence_areas_provinces=["MI", "RA"])
    richiesta = VendorChangeRequest.objects.get()
    Province.objects.filter(code="RA").delete()
    revisore = _login_bo(client)

    richiesta.apply_to_vendor(reviewer=revisore)

    utente.vendor.refresh_from_db()
    assert competence.current_selection(utente.vendor)["provinces"] == ["MI"]


# --------------------------------------------------------------------------
# Visualizzazione
# --------------------------------------------------------------------------


@pytest.mark.django_db
def test_la_scheda_mostra_il_riepilogo(geografia_italia, client):
    utente = _login_vendor(client)
    competence.set_vendor_competence(
        utente.vendor,
        province_codes=list(
            Province.objects.filter(region__code="LOM").values_list(
                "code", flat=True
            )
        ),
        country_codes=[],
    )

    risposta = client.get(reverse("portal:my-profile"))

    contenuto = risposta.content.decode()
    assert "Lombardia (tutte)" in contenuto
    assert "Zone di competenza" in contenuto


@pytest.mark.django_db
def test_il_form_di_proposta_carica_il_selettore(geografia_italia, client):
    _login_vendor(client)

    risposta = client.get(reverse("portal:my-profile-change"))

    contenuto = risposta.content.decode()
    assert "data-vms-geo" in contenuto
    assert "geo/js/competence_area_selector.js" in contenuto
    assert "geo/css/competence_area_selector.css" in contenuto


@pytest.mark.django_db
def test_il_backoffice_vede_il_diff_in_chiaro(geografia_italia, client):
    utente = _login_vendor(client)
    _proponi(client, utente.vendor, competence_areas_provinces=["MI"])
    richiesta = VendorChangeRequest.objects.get()
    client.logout()
    _login_bo(client)

    risposta = client.get(
        reverse("portal:bo-change-request-detail", kwargs={"pk": richiesta.pk})
    )

    contenuto = risposta.content.decode()
    assert "Milano" in contenuto
    # Nel diff deve comparire la frase leggibile, non la lista grezza di
    # codici che sta in `new_codes`.
    assert "['MI']" not in contenuto
    assert "new_codes" not in contenuto


@pytest.mark.django_db
def test_avviso_se_le_zone_sono_cambiate_dopo_la_proposta(
    geografia_italia, client
):
    utente = _login_vendor(client)
    _proponi(client, utente.vendor, competence_areas_provinces=["MI"])
    richiesta = VendorChangeRequest.objects.get()
    # Un admin tocca le zone mentre la richiesta e' in attesa.
    competence.set_vendor_competence(
        utente.vendor, province_codes=["RM"], country_codes=[]
    )
    client.logout()
    _login_bo(client)

    risposta = client.get(
        reverse("portal:bo-change-request-detail", kwargs={"pk": richiesta.pk})
    )

    assert "Le zone di competenza del fornitore sono cambiate" in (
        risposta.content.decode()
    )


@pytest.mark.django_db
def test_nessun_avviso_se_nulla_e_cambiato(geografia_italia, client):
    utente = _login_vendor(client)
    _proponi(client, utente.vendor, competence_areas_provinces=["MI"])
    richiesta = VendorChangeRequest.objects.get()
    client.logout()
    _login_bo(client)

    risposta = client.get(
        reverse("portal:bo-change-request-detail", kwargs={"pk": richiesta.pk})
    )

    assert "Le zone di competenza del fornitore sono cambiate" not in (
        risposta.content.decode()
    )


@pytest.mark.django_db
def test_approvazione_dalla_vista_backoffice(geografia_italia, client):
    utente = _login_vendor(client)
    _proponi(client, utente.vendor, competence_areas_provinces=["MI"])
    richiesta = VendorChangeRequest.objects.get()
    client.logout()
    _login_bo(client)

    client.post(
        reverse(
            "portal:bo-change-request-review", kwargs={"pk": richiesta.pk}
        ),
        {"action": "approve", "review_notes": ""},
    )

    utente.vendor.refresh_from_db()
    assert competence.current_selection(utente.vendor)["provinces"] == ["MI"]
