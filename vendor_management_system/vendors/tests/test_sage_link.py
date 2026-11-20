"""Lente e collegamento SAGE: fornitori condivisi tra società.

Le viste FABRIC_HUB servono solo a predisporre i collegamenti: un fornitore
già censito (per codice SAGE o per conto Embyon) non viene duplicato, si
aggiunge la sezione della società; un fornitore nuovo nasce con la sezione
Comune più quella della società scelta. Chiamate HTTP mockate.
"""

import json
from unittest.mock import patch

import pytest
from django.urls import reverse

from vendor_management_system.users.models import User
from vendor_management_system.vendors import fabric_hub
from vendor_management_system.vendors.models import (
    Vendor,
    VendorCompany,
    VendorCompanyAccount,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db

SUPPLIER = {
    "sage_code": "000011",
    "business_name": "ACME SRL",
    "vat_number": "01234567890",
    "tax_code": "01234567890",
    "province": "MI",
    "is_active_somewhere": True,
    "has_link_conflict": False,
}
ACCOUNTS = [
    {
        "sage_code": "000011",
        "company": "EVIMED",
        "account_code": "F  6546",
        "status": "ATTIVO",
        "link_source": "sage",
        "link_conflict": False,
        "in_embyon": True,
    },
    {
        "sage_code": "000011",
        "company": "SICURA",
        "account_code": "F  1792",
        "status": "NON ATTIVO/NON MOVIMENTATO",
        "link_source": "sage",
        "link_conflict": False,
        "in_embyon": True,
    },
]


@pytest.fixture(autouse=True)
def _clean_cache():
    fabric_hub._shared_cache.clear()
    yield
    fabric_hub._shared_cache.clear()


def _fake_entity(filter_expr, page_size=1000, entity=None):
    if entity == "v_supplier_companies":
        return iter(ACCOUNTS)
    return iter([SUPPLIER])


@pytest.fixture
def dab():
    with patch.object(fabric_hub, "_iter_entity", side_effect=_fake_entity):
        yield


def _admin(client, company="SICURA", superuser=False):
    if superuser:
        user = User.objects.create_superuser(
            email="super-sage@example.invalid", password="x"
        )
    else:
        user = User.objects.create_user(
            email=f"admin-{company}@example.invalid",
            password="x",
            role="admin",
            company_id=company,
        )
    client.force_login(user)
    return user


class TestRicercaViste:
    def test_ricerca_per_nome_con_conti_per_societa(self, dab):
        (row,) = fabric_hub.search_shared_suppliers(name="acme")
        assert row["sage_code"] == "000011"
        assert row["name"] == "ACME SRL"
        assert [
            (c["company"], c["account_code"]) for c in row["companies"]
        ] == [
            ("EVIMED", "F 6546"),
            ("SICURA", "F 1792"),
        ]
        assert row["companies"][1]["embyon_active"] is False

    def test_conto_embyon_filtrato_lato_server_con_padding(self):
        with patch.object(
            fabric_hub, "_iter_entity", return_value=iter([])
        ) as fetch:
            fabric_hub.search_shared_suppliers(account_code="F 6546")
        assert fetch.call_args.args[0] == "account_code eq 'F  6546'"
        assert fetch.call_args.kwargs["entity"] == "v_supplier_companies"


class TestLenteAdmin:
    def test_risultato_segnala_fornitore_gia_censito_per_sage(
        self, client, dab
    ):
        _admin(client)
        vendor = VendorFactory(sage_code="000011")
        url = reverse("admin:vendors_vendor_embyon_search")
        data = client.get(url, {"sage_code": "000011"}).json()
        assert data["user_company"] == "SICURA"
        assert data["results"][0]["existing_vendor"]["pk"] == vendor.pk

    def test_risultato_segnala_fornitore_censito_col_vecchio_codice(
        self, client, dab
    ):
        _admin(client)
        vendor = VendorFactory(old_code="F 6546", embyon_company="Evimed")
        url = reverse("admin:vendors_vendor_embyon_search")
        data = client.get(url, {"name": "acme"}).json()
        assert data["results"][0]["existing_vendor"]["pk"] == vendor.pk

    def test_collega_sage_aggiunge_solo_la_sezione_della_societa(self, client):
        _admin(client, "SICURA")
        vendor = VendorFactory(old_code="F 6546", embyon_company="Evimed")
        VendorCompany.objects.create(vendor=vendor, company_id="EVIMED")
        normalized = [fabric_hub.normalize_company_row(r) for r in ACCOUNTS]

        response = client.post(
            reverse("admin:vendors_vendor_link_sage"),
            {
                "vendor": vendor.pk,
                "sage_code": "000011",
                "company": "SICURA",
                "accounts": json.dumps(normalized),
            },
        )

        assert response.status_code == 200
        assert "sezione=SICURA" in response.json()["url"]
        vendor.refresh_from_db()
        assert vendor.sage_code == "000011"
        assert Vendor.objects.count() == 1
        section = VendorCompany.objects.get(vendor=vendor, company_id="SICURA")
        assert list(
            section.accounts.values_list("account_code", flat=True)
        ) == ["F 1792"]
        assert section.embyon_active is False

    def test_collega_sage_non_aggiunge_societa_di_altri(self, client):
        _admin(client, "SICURA")
        vendor = VendorFactory()
        client.post(
            reverse("admin:vendors_vendor_link_sage"),
            {"vendor": vendor.pk, "sage_code": "000099", "company": "IGEAM"},
        )
        assert not VendorCompany.objects.filter(vendor=vendor).exists()


class TestNuovoFornitore:
    def _post_add(self, client, **extra):
        data = {
            "name": "Nuovo Fornitore",
            "vendor_type": "Società",
            "risk_level": "MEDIUM",
            "is_active": "on",
            "expiry_notifications_enabled": "on",
            "_save": "Salva",
        }
        data.update(extra)
        return client.post(reverse("admin:vendors_vendor_add"), data)

    def test_crea_comune_e_sezione_della_societa_dell_utente(self, client):
        user = _admin(client, "IGEAM")
        normalized = [fabric_hub.normalize_company_row(r) for r in ACCOUNTS]
        response = self._post_add(
            client,
            sage_code="000077",
            sage_accounts=json.dumps(normalized),
        )
        assert response.status_code == 302, response.content[:2000]
        vendor = Vendor.objects.get(name="Nuovo Fornitore")
        assert response.url == reverse(
            "admin:vendors_vendor_sections", args=[vendor.pk]
        )
        assert list(
            vendor.company_sections.values_list("company_id", flat=True)
        ) == ["IGEAM"]
        # I conti di altre società non vengono agganciati.
        assert not VendorCompanyAccount.objects.exists()
        # Chi censisce il fornitore ne diventa il primo utente di gestione.
        assert vendor.managed_by.email == user.email

    def test_sage_gia_censito_blocca_il_doppione(self, client):
        _admin(client, "IGEAM")
        existing = VendorFactory(sage_code="000011")
        response = self._post_add(client, sage_code="000011")
        assert response.status_code == 200
        assert Vendor.objects.count() == 1
        sections_url = reverse(
            "admin:vendors_vendor_sections", args=[existing.pk]
        )
        assert sections_url in response.content.decode()

    def test_controllo_duplicati_piva_risolve_il_sage(self, client, dab):
        _admin(client, "IGEAM")
        existing = VendorFactory(sage_code="000011")
        data = client.get(
            reverse("admin:vendors_vendor_duplicate_check"),
            {"field": "vat_number", "value": "01234567890"},
        ).json()
        assert data["duplicate"] is True
        assert data["sage"] is True
        assert data["vendor_code"] == existing.pk
