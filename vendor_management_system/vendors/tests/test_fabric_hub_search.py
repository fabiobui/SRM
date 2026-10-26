"""Ricerca fornitori (lente nel form admin) sull'API FABRIC_HUB (DAB).

Le chiamate HTTP sono mockate: nessuna richiesta reale parte durante i test.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.vendors import fabric_hub

User = get_user_model()
PASSWORD = "test-pass-1234"


def _row(**over):
    row = {
        "Ditta": "CMASRL",
        "CODCONTO": "F   463",
        "DSCCONTO1": " IL CASTELLO COOP ",
        "PARTITAIVA": "02044860985",
        "CODFISCALE": "02044860985",
        "INDIRIZZO": "VIA BRODOLINI 3",
        "CAP": "25043",
        "LOCALITA": "BRENO",
        "PROVINCIA": "BS",
        "Mail": None,
        "StatoFornitore": "ATTIVO",
    }
    row.update(over)
    return row


@pytest.fixture(autouse=True)
def _clean_cache():
    fabric_hub._suppliers_cache.update(rows=None, exp=0.0)
    yield
    fabric_hub._suppliers_cache.update(rows=None, exp=0.0)


def _patch_rows(rows):
    return patch.object(fabric_hub, "_iter_entity", return_value=iter(rows))


def test_name_search_filters_active_list_in_memory_and_caches():
    rows = [_row(), _row(CODCONTO="F 9", DSCCONTO1="ALTRO SRL")]
    with _patch_rows(rows) as fetch:
        results = fabric_hub.search_suppliers(name="castello")
        fabric_hub.search_suppliers(name="altro")

    assert fetch.call_count == 1  # seconda ricerca servita dalla cache
    assert fetch.call_args.args == (fabric_hub.ACTIVE_FILTER,)
    assert results == [
        {
            "old_code": "F 463",
            "company": "CmaSrl",
            "name": "IL CASTELLO COOP",
            "vat_number": "02044860985",
            "fiscal_code": "02044860985",
            "province": "BS",
            "status": "ATTIVO",
            "address": "VIA BRODOLINI 3",
            "postal_code": "25043",
            "city": "BRENO",
            "email": "",
        }
    ]


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"old_code": "F 463"}, "CODCONTO eq 'F   463'"),
        ({"old_code": "17777"}, "CODCONTO eq 'F 17777'"),
        ({"vat": "02044860985"}, "PARTITAIVA eq '02044860985'"),
        ({"fiscal_code": "O'BRIEN"}, "CODFISCALE eq 'O''BRIEN'"),
    ],
)
def test_exact_criteria_use_server_side_filter(kwargs, expected):
    with _patch_rows([]) as fetch:
        fabric_hub.search_suppliers(**kwargs)

    assert fetch.call_args.args == (
        f"{fabric_hub.ACTIVE_FILTER} and {expected}",
    )


@pytest.fixture
def admin_client_logged(client, db):
    admin = User.objects.create_superuser(
        email="fabric-hub-admin@example.invalid",
        password=PASSWORD,
        role="admin",
    )
    client.force_login(admin)
    return client


@pytest.mark.django_db
def test_admin_search_view_returns_rows_with_active_flag(admin_client_logged):
    url = reverse("admin:vendors_vendor_embyon_search")
    with _patch_rows([_row()]):
        resp = admin_client_logged.get(url, {"vat_number": "02044860985"})

    assert resp.status_code == 200
    (row,) = resp.json()["results"]
    assert row["company"] == "CmaSrl"
    assert row["embyon_active"] is True


@pytest.mark.django_db
def test_admin_search_view_validates_input(admin_client_logged):
    url = reverse("admin:vendors_vendor_embyon_search")
    assert admin_client_logged.get(url).json()["results"] == []
    assert "error" in admin_client_logged.get(url, {"name": "ab"}).json()
