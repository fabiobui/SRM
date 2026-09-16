"""
Test per le funzioni di ricerca anagrafica aziendale via l'API esterna
openapi.com (usata come riferimento per precompilare dati fornitore).

Nota: la versione precedente di questo file era in realtà uno script, non un
test — girava a livello di modulo, eseguiva vere chiamate HTTP verso l'API
reale ad ogni raccolta di pytest, e conteneva una API key reale hardcoded
(già committata in git: se non è già stata ruotata, va considerata
compromessa). Qui le chiamate HTTP sono mockate: nessuna richiesta reale
parte durante i test, e la chiave usata è un valore fittizio solo per
verificare che venga inclusa nell'header Authorization.
"""

from unittest.mock import MagicMock, patch

import requests

API_KEY = "test-api-key"
BASE_URL = "https://company.openapi.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def cerca_azienda(nome, provincia=None, forma=None):
    params = {
        "dryRun": 0,
        "dataEnrichment": "name",
        "autocomplete": nome,
        "activityStatus": "ATTIVA",
        "limit": 30,
    }
    if provincia and len(provincia) >= 2:
        params["province"] = provincia[:2].upper()
    if forma and forma[:2].upper() in ("SP", "SR"):
        params["legalFormCode"] = forma[:2].upper()

    r = requests.get(f"{BASE_URL}/IT-search", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json().get("data", [])


def get_address(company_id):
    r = requests.get(f"{BASE_URL}/IT-address/{company_id}", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    if data.get("success") and data.get("data"):
        office = data["data"][0]["address"]["registeredOffice"]
        indirizzo = (
            f"{office.get('toponym', '')} {office.get('street', '')}".strip()
        )
        return {
            "indirizzo": indirizzo,
            "numcivico": office.get("streetNumber"),
            "città": office.get("town"),
            "cap": office.get("zipCode"),
            "provincia": office.get("province"),
            "regione": office.get("region", {}).get("description"),
            "nazione": "IT",
        }
    return None


def _mock_response(json_data, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = MagicMock()
    return response


@patch("tests.test_ricerca_anagrafica.requests.get")
def test_cerca_azienda_returns_matches(mock_get):
    mock_get.return_value = _mock_response(
        {
            "data": [
                {
                    "id": 1,
                    "companyName": "AUDIRAI SRL",
                    "vatCode": "12345678901",
                }
            ]
        }
    )

    risultati = cerca_azienda("AUDIRAI", provincia="MI")

    assert risultati == [
        {"id": 1, "companyName": "AUDIRAI SRL", "vatCode": "12345678901"}
    ]
    called_url, called_kwargs = mock_get.call_args[0][0], mock_get.call_args[1]
    assert called_url == f"{BASE_URL}/IT-search"
    assert called_kwargs["headers"]["Authorization"] == f"Bearer {API_KEY}"
    assert called_kwargs["params"]["province"] == "MI"


@patch("tests.test_ricerca_anagrafica.requests.get")
def test_cerca_azienda_no_matches_returns_empty_list(mock_get):
    mock_get.return_value = _mock_response({"data": []})

    assert cerca_azienda("NOME INESISTENTE") == []


@patch("tests.test_ricerca_anagrafica.requests.get")
def test_get_address_parses_registered_office(mock_get):
    mock_get.return_value = _mock_response(
        {
            "success": True,
            "data": [
                {
                    "address": {
                        "registeredOffice": {
                            "toponym": "Via",
                            "street": "Roma",
                            "streetNumber": "10",
                            "town": "Milano",
                            "zipCode": "20100",
                            "province": "MI",
                            "region": {"description": "Lombardia"},
                        }
                    }
                }
            ],
        }
    )

    indirizzo = get_address(company_id=1)

    assert indirizzo == {
        "indirizzo": "Via Roma",
        "numcivico": "10",
        "città": "Milano",
        "cap": "20100",
        "provincia": "MI",
        "regione": "Lombardia",
        "nazione": "IT",
    }


@patch("tests.test_ricerca_anagrafica.requests.get")
def test_get_address_returns_none_when_not_found(mock_get):
    mock_get.return_value = _mock_response({"success": False, "data": []})

    assert get_address(company_id=999) is None
