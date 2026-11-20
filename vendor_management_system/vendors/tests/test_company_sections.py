"""Fornitori condivisi tra società: società, sezioni e qualifica per società.

Un fornitore ha una sezione Comune e una sezione per ogni società con cui
lavora. La qualifica di una sezione considera i documenti/requisiti
obbligatori della sezione Comune più quelli della società; il fornitore
riporta l'aggregato delle sezioni.
"""

import importlib

import pytest
from django.apps import apps
from django.db import IntegrityError, transaction

from vendor_management_system.documents.models import Document
from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    DocumentCatalogFactory,
    DocumentFactory,
    VendorCompetenceFactory,
)
from vendor_management_system.vendors.models import (
    COMMON_SECTION,
    Company,
    VendorCompany,
    VendorCompanyAccount,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db

migrazione = importlib.import_module(
    "vendor_management_system.vendors.migrations.0058_popola_sezioni"
)


def _approved_doc(vendor, company=COMMON_SECTION, **extra):
    fields = {"status": "APPROVED", "file": "vendor_documents/a.pdf"}
    fields.update(extra)
    return DocumentFactory(vendor=vendor, company_id=company, **fields)


class TestCompany:
    def test_societa_seminate_con_sezione_comune(self):
        codes = set(Company.objects.values_list("code", flat=True))
        assert {COMMON_SECTION, "SICURA", "EVIMED", "IGEAM"} <= codes
        assert Company.objects.get(code=COMMON_SECTION).is_common
        assert COMMON_SECTION not in Company.objects.real().values_list(
            "code", flat=True
        )

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("SICURA", "SICURA"),
            ("Sicura S.p.A.", "SICURA"),
            ("gs protec", "GSPROTEC"),
            ("Società sconosciuta", None),
            ("", None),
        ],
    )
    def test_match_ldap(self, value, expected):
        company = Company.objects.match_ldap(value)
        assert (company.code if company else None) == expected

    def test_match_ldap_usa_gli_alias(self):
        Company.objects.filter(code="IGEAM").update(ldap_aliases="Gruppo X")
        assert Company.objects.match_ldap("gruppo x").code == "IGEAM"


class TestUnicitaPerSezione:
    def test_stesso_documento_in_sezioni_diverse_ammesso(self):
        vendor = VendorFactory()
        catalog = DocumentCatalogFactory()
        DocumentFactory(vendor=vendor, document_type=catalog)
        DocumentFactory(
            vendor=vendor, document_type=catalog, company_id="SICURA"
        )
        assert Document.objects.filter(vendor=vendor).count() == 2

    def test_stesso_documento_nella_stessa_sezione_rifiutato(self):
        vendor = VendorFactory()
        catalog = DocumentCatalogFactory()
        DocumentFactory(
            vendor=vendor, document_type=catalog, company_id="SICURA"
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            DocumentFactory(
                vendor=vendor, document_type=catalog, company_id="SICURA"
            )

    def test_conto_con_spazi_collassati(self):
        vendor = VendorFactory()
        section = VendorCompany.objects.create(
            vendor=vendor, company_id="EVIMED"
        )
        account = VendorCompanyAccount.objects.create(
            section=section, company_id="EVIMED", account_code="F  6546"
        )
        assert account.account_code == "F 6546"


class TestQualificaPerSocieta:
    def test_lacune_di_una_sezione_ignorano_le_altre_societa(self):
        vendor = VendorFactory()
        sicura = VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA"
        )
        evimed = VendorCompany.objects.create(
            vendor=vendor, company_id="EVIMED"
        )
        DocumentFactory(vendor=vendor, company_id="EVIMED", status="PENDING")
        _approved_doc(vendor)

        assert sicura.qualification_blockers == []
        assert len(evimed.qualification_blockers) == 1

    def test_documento_comune_blocca_tutte_le_sezioni(self):
        vendor = VendorFactory()
        sicura = VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA"
        )
        evimed = VendorCompany.objects.create(
            vendor=vendor, company_id="EVIMED"
        )
        DocumentFactory(vendor=vendor, status="PENDING")
        assert sicura.qualification_blockers
        assert evimed.qualification_blockers

    def test_approvazione_bloccata_solo_nella_sezione_non_in_regola(self):
        vendor = VendorFactory()
        DocumentFactory(vendor=vendor, company_id="EVIMED", status="PENDING")
        sicura = VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA", qualification_status="APPROVED"
        )
        evimed = VendorCompany.objects.create(
            vendor=vendor, company_id="EVIMED", qualification_status="APPROVED"
        )
        sicura.refresh_from_db()
        evimed.refresh_from_db()
        assert sicura.qualification_status == "APPROVED"
        assert sicura.vendor_final_evaluation == "POSITIVO"
        assert evimed.qualification_status == "TO_REVIEW"

    def test_documento_scaduto_declassa_solo_la_sua_sezione(self):
        vendor = VendorFactory()
        doc = _approved_doc(vendor, company="SICURA")
        sicura = VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA", qualification_status="APPROVED"
        )
        evimed = VendorCompany.objects.create(
            vendor=vendor, company_id="EVIMED", qualification_status="APPROVED"
        )
        doc.status = "REJECTED"
        doc.save()
        sicura.refresh_from_db()
        evimed.refresh_from_db()
        assert sicura.qualification_status == "TO_REVIEW"
        assert evimed.qualification_status == "APPROVED"

    def test_aggregato_sul_fornitore(self):
        vendor = VendorFactory(qualification_status="PENDING")
        VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA", qualification_status="APPROVED"
        )
        VendorCompany.objects.create(
            vendor=vendor,
            company_id="EVIMED",
            qualification_status="REJECTED",
            embyon_active=False,
        )
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"
        assert vendor.vendor_final_evaluation == "POSITIVO"
        assert vendor.embyon_active is True

    def test_salvataggio_del_fornitore_non_altera_l_aggregato(self):
        vendor = VendorFactory()
        VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA", qualification_status="APPROVED"
        )
        vendor.refresh_from_db()
        vendor.name = "Nuovo nome"
        vendor.qualification_status = "REJECTED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"

    def test_upload_completo_manda_in_revisione_la_sezione(self):
        vendor = VendorFactory()
        section = VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA"
        )
        DocumentFactory(
            vendor=vendor, company_id="SICURA", status="UPLOADED", file="a.pdf"
        )
        vendor.submit_for_review_if_complete()
        section.refresh_from_db()
        assert section.qualification_status == "TO_REVIEW"

    def test_requisito_di_altra_societa_non_blocca(self):
        vendor = VendorFactory()
        VendorCompetenceFactory(
            vendor=vendor,
            company_id="EVIMED",
            competence=CompetenceFactory(is_mandatory=True),
            verified=False,
        )
        section = VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA", qualification_status="APPROVED"
        )
        section.refresh_from_db()
        assert section.qualification_status == "APPROVED"


class TestMigrazioneSezioni:
    def test_crea_sezione_conto_e_sposta_gli_elementi(self):
        vendor = VendorFactory(
            embyon_company="Igeam",
            old_code="F  2327",
            qualification_status="APPROVED",
            embyon_active=True,
        )
        doc = _approved_doc(vendor)
        legacy = VendorFactory(embyon_company=None, old_code="XLS0001")
        legacy_doc = DocumentFactory(vendor=legacy)

        migrazione.forward_sections(apps, None)

        section = VendorCompany.objects.get(vendor=vendor)
        assert section.company_id == "IGEAM"
        assert section.qualification_status == "APPROVED"
        assert list(
            section.accounts.values_list("account_code", flat=True)
        ) == ["F 2327"]
        doc.refresh_from_db()
        legacy_doc.refresh_from_db()
        assert doc.company_id == "IGEAM"
        assert legacy_doc.company_id == COMMON_SECTION
        assert not VendorCompany.objects.filter(vendor=legacy).exists()

    def test_codice_xls_non_diventa_conto(self):
        vendor = VendorFactory(embyon_company="Sicura", old_code="XLS0002")
        migrazione.forward_sections(apps, None)
        section = VendorCompany.objects.get(vendor=vendor)
        assert not section.accounts.exists()

    def test_ambito_comune_su_catalogo(self):
        durc = DocumentCatalogFactory(code="DURC")
        contratto = DocumentCatalogFactory(code="ACQ-CONT")
        migrazione.forward_sections(apps, None)
        durc.refresh_from_db()
        contratto.refresh_from_db()
        assert durc.scope == "COMMON"
        assert contratto.scope == "COMPANY"


class TestSyncGiornaliero:
    def test_declassa_solo_la_sezione_con_documento_scaduto(self):
        from datetime import timedelta

        from django.utils import timezone

        from vendor_management_system.vendors.qualification_sync import (
            sync_all,
        )

        vendor = VendorFactory()
        doc = _approved_doc(vendor, company="SICURA")
        sicura = VendorCompany.objects.create(
            vendor=vendor, company_id="SICURA", qualification_status="APPROVED"
        )
        evimed = VendorCompany.objects.create(
            vendor=vendor, company_id="EVIMED", qualification_status="APPROVED"
        )
        # Scadenza passata "da sola", senza salvataggi che scatenano i signal.
        Document.objects.filter(pk=doc.pk).update(
            expiry_date=timezone.now().date() - timedelta(days=1)
        )

        summary = sync_all()

        sicura.refresh_from_db()
        evimed.refresh_from_db()
        assert sicura.qualification_status == "TO_REVIEW"
        assert evimed.qualification_status == "APPROVED"
        assert [(v.pk, c) for v, c, _ in summary["downgraded"]] == [
            (vendor.pk, "Sicura")
        ]
