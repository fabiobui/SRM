"""Sync con le viste FABRIC_HUB e accorpamento dei fornitori condivisi.

Il sync lavora solo sui fornitori già censiti (non ne crea né aggiunge
sezioni); l'accorpamento unisce per codice SAGE i fornitori censiti per
società diverse, lasciando ogni elemento nella sezione d'origine.
"""

import pytest

from vendor_management_system.documents.models import Document
from vendor_management_system.portal.tests.factories import DocumentFactory
from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import (
    Vendor,
    VendorCompany,
    VendorCompanyAccount,
)
from vendor_management_system.vendors.supplier_merge import (
    merge_shared_suppliers,
    write_reports,
)
from vendor_management_system.vendors.supplier_sync import sync_suppliers
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db


def _row(sage, company, code, status="ATTIVO", conflict=False):
    return {
        "sage_code": sage,
        "company": company,
        "account_code": code,
        "status": status,
        "embyon_active": status == "ATTIVO",
        "in_embyon": True,
        "link_source": "sage",
        "link_conflict": conflict,
    }


def _vendor_in(company, code, **extra):
    """Fornitore censito per una società, come lo crea la migrazione."""
    vendor = VendorFactory(old_code=code, **extra)
    section = VendorCompany.objects.create(vendor=vendor, company_id=company)
    VendorCompanyAccount.objects.create(
        section=section, company_id=company, account_code=code
    )
    return vendor


ROWS = [
    _row("000011", "EVIMED", "F 6546"),
    _row("000011", "SICURA", "F 1792", status="NON ATTIVO/NON MOVIMENTATO"),
    _row("000011", "IGEAM", "F 2327"),
    _row("000022", "IGEAM", "F 10"),
]


class TestSync:
    def test_assegna_sage_e_aggiorna_stato_senza_creare_nulla(self):
        vendor = _vendor_in("SICURA", "F 1792")
        summary = sync_suppliers(company_rows=ROWS)

        vendor.refresh_from_db()
        assert vendor.sage_code == "000011"
        section = vendor.company_sections.get()
        assert section.embyon_active is False
        assert section.vendor_final_evaluation == "NEGATIVO"
        # Nessuna sezione EVIMED/IGEAM aggiunta, nessun fornitore creato.
        assert vendor.company_sections.count() == 1
        assert Vendor.objects.count() == 1
        assert summary["sage_assigned"] == [(vendor, "000011")]

    def test_segnala_candidati_all_accorpamento(self):
        _vendor_in("EVIMED", "F 6546", sage_code="000011")
        other = _vendor_in("SICURA", "F 1792")
        summary = sync_suppliers(company_rows=ROWS)
        other.refresh_from_db()
        assert other.sage_code is None
        assert [(v.pk, s) for v, s, _ in summary["merge_candidates"]] == [
            (other.pk, "000011")
        ]

    def test_dry_run_non_scrive(self):
        vendor = _vendor_in("SICURA", "F 1792")
        sync_suppliers(dry_run=True, company_rows=ROWS)
        vendor.refresh_from_db()
        assert vendor.sage_code is None


class TestAccorpamento:
    def test_accorpa_e_mantiene_le_sezioni_d_origine(self):
        evimed = _vendor_in("EVIMED", "F 6546", email="")
        sicura = _vendor_in("SICURA", "F 1792", email="sicura@example.invalid")
        doc_evimed = DocumentFactory(vendor=evimed, company_id="EVIMED")
        doc_sicura = DocumentFactory(vendor=sicura, company_id="SICURA")
        portal_user = User.objects.create_user(
            email="portale@example.invalid",
            password="x",
            role="vendor",
            vendor=sicura,
        )

        summary = merge_shared_suppliers(
            ROWS,
            apply=True,
            survivor_map={"000011": evimed.pk},
        )

        assert len(summary["merged"]) == 1
        assert Vendor.objects.count() == 1
        survivor = Vendor.objects.get()
        assert survivor.pk == evimed.pk
        assert survivor.sage_code == "000011"
        # Campo vuoto del superstite completato, senza sovrascrivere.
        assert survivor.email == "sicura@example.invalid"
        assert set(
            survivor.company_sections.values_list("company_id", flat=True)
        ) == {"EVIMED", "SICURA"}
        doc_evimed.refresh_from_db()
        doc_sicura.refresh_from_db()
        assert doc_sicura.vendor_id == survivor.pk
        assert (doc_evimed.company_id, doc_sicura.company_id) == (
            "EVIMED",
            "SICURA",
        )
        portal_user.refresh_from_db()
        assert portal_user.vendor_id == survivor.pk

    def test_superstite_e_il_record_modificato_piu_di_recente(self):
        old = _vendor_in("EVIMED", "F 6546")
        recent = _vendor_in("SICURA", "F 1792")
        DocumentFactory(vendor=recent, company_id="SICURA")
        summary = merge_shared_suppliers(ROWS)
        assert summary["merged"][0]["survivor"].pk == recent.pk
        # Simulazione: nulla cambia.
        assert Vendor.objects.filter(pk=old.pk).exists()

    def test_elementi_in_comune_del_donatore_vanno_nella_sua_societa(self):
        evimed = _vendor_in("EVIMED", "F 6546")
        sicura = _vendor_in("SICURA", "F 1792")
        catalog_doc = DocumentFactory(vendor=evimed)
        DocumentFactory(vendor=sicura, document_type=catalog_doc.document_type)
        merge_shared_suppliers(
            ROWS, apply=True, survivor_map={"000011": evimed.pk}
        )
        sections = Document.objects.filter(
            document_type=catalog_doc.document_type
        ).values_list("company_id", flat=True)
        assert sorted(sections) == ["COMUNE", "SICURA"]

    def test_gruppo_con_due_record_della_stessa_societa_saltato(self):
        _vendor_in("IGEAM", "F 2327")
        second = VendorFactory(old_code="F 2328")
        VendorCompany.objects.create(vendor=second, company_id="IGEAM")
        rows = [*ROWS, _row("000011", "IGEAM", "F 2328")]
        VendorCompanyAccount.objects.create(
            section=second.company_sections.get(),
            company_id="IGEAM",
            account_code="F 2328",
        )
        summary = merge_shared_suppliers(rows, apply=True)
        assert summary["merged"] == []
        assert summary["skipped"][0][2].startswith("stessa_societa")
        assert Vendor.objects.count() == 2

    def test_report_dei_codici_non_presenti_nelle_viste(self, tmp_path):
        _vendor_in("EVIMED", "F 6546")
        lost = VendorFactory(old_code="F 999", embyon_company="Igeam")
        VendorFactory(old_code="XLS0001", embyon_company=None)
        summary = merge_shared_suppliers(ROWS)
        reasons = {v.pk: r for v, r, _ in summary["unmatched"]}
        assert reasons[lost.pk] == "non_trovato"
        write_reports(summary, tmp_path)
        content = (tmp_path / "embyon_codes_not_in_views.csv").read_text(
            encoding="utf-8"
        )
        assert "F 999" in content
