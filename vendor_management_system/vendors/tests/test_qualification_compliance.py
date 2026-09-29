"""AIDEV-100: obbligatorietà da catalogo (`DocumentCatalog.is_required`,
`Competence.is_mandatory`) e vincolo sullo stato di qualifica del fornitore.

Un fornitore può risultare "Approvato" solo se tutti i documenti contrattuali
e i requisiti professionali OBBLIGATORI assegnati sono caricati, verificati
dal gestore e non scaduti.
"""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    DocumentCatalogFactory,
    DocumentFactory,
    VendorCompetenceFactory,
)
from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db

OGGI = timezone.now().date()
IERI = OGGI - timedelta(days=1)
DOMANI = OGGI + timedelta(days=30)


def _doc_ok(vendor, **extra):
    campi = {"status": "APPROVED", "file": "vendor_documents/a.pdf"}
    campi.update(extra)
    return DocumentFactory(vendor=vendor, **campi)


def _req_ok(vendor, **extra):
    campi = {
        "competence": CompetenceFactory(is_mandatory=True),
        "verified": True,
        "document_file": "vendor_competences/a.pdf",
    }
    campi.update(extra)
    return VendorCompetenceFactory(vendor=vendor, **campi)


class TestApprovazioneFornitore:
    def test_approvato_senza_record_assegnati_resta_approvato(self):
        vendor = VendorFactory(qualification_status="APPROVED")
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"

    def test_documento_obbligatorio_non_approvato_blocca_l_approvazione(self):
        vendor = VendorFactory()
        DocumentFactory(vendor=vendor, status="UPLOADED", file="x.pdf")
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_documento_obbligatorio_senza_file_blocca_l_approvazione(self):
        vendor = VendorFactory()
        DocumentFactory(vendor=vendor, status="APPROVED", file=None)
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_documento_obbligatorio_scaduto_blocca_l_approvazione(self):
        vendor = VendorFactory()
        _doc_ok(vendor, expiry_date=IERI)
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_requisito_obbligatorio_non_verificato_blocca(self):
        vendor = VendorFactory()
        _req_ok(vendor, verified=False)
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_requisito_obbligatorio_senza_file_blocca(self):
        vendor = VendorFactory()
        _req_ok(vendor, document_file=None)
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_requisito_obbligatorio_scaduto_blocca(self):
        vendor = VendorFactory()
        _req_ok(vendor, expiry_date=IERI)
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_record_facoltativi_non_bloccano(self):
        vendor = VendorFactory()
        DocumentFactory(
            vendor=vendor,
            document_type=DocumentCatalogFactory(is_required=False),
            status="PENDING",
        )
        VendorCompetenceFactory(
            vendor=vendor, competence=CompetenceFactory(is_mandatory=False)
        )
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"

    def test_tutto_caricato_verificato_e_valido_permette_l_approvazione(self):
        vendor = VendorFactory()
        _doc_ok(vendor, expiry_date=DOMANI)
        _req_ok(vendor, expiry_date=DOMANI)
        vendor.qualification_status = "APPROVED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"

    def test_stato_diverso_da_approvato_non_viene_toccato(self):
        vendor = VendorFactory()
        DocumentFactory(vendor=vendor, status="PENDING")
        vendor.qualification_status = "REJECTED"
        vendor.save()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "REJECTED"

    def test_e_qualificato_richiede_anche_la_conformita_documentale(self):
        vendor = VendorFactory(qualification_status="APPROVED")
        assert vendor.is_qualified is True
        # Un obbligatorio scade dopo l'approvazione: nessun save() sul
        # fornitore, ma non è più qualificato.
        _doc_ok(vendor, expiry_date=IERI)
        assert vendor.is_qualified is False


class TestSincronizzazioneDaiRecord:
    def test_documento_che_diventa_non_valido_declassa_il_fornitore(self):
        vendor = VendorFactory()
        doc = _doc_ok(vendor)
        vendor.qualification_status = "APPROVED"
        vendor.save()

        doc.status = "REJECTED"
        doc.save()

        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_nuovo_documento_obbligatorio_da_caricare_declassa(self):
        vendor = VendorFactory(qualification_status="APPROVED")
        DocumentFactory(vendor=vendor, status="PENDING")
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_requisito_che_perde_la_verifica_declassa_il_fornitore(self):
        vendor = VendorFactory()
        req = _req_ok(vendor)
        vendor.qualification_status = "APPROVED"
        vendor.save()

        req.verified = False
        req.save()

        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_cancellare_il_requisito_bloccante_non_riapprova_da_solo(self):
        vendor = VendorFactory()
        req = _req_ok(vendor, verified=False)
        vendor.qualification_status = "APPROVED"
        vendor.save()
        req.delete()
        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_documento_facoltativo_non_valido_non_declassa(self):
        vendor = VendorFactory(qualification_status="APPROVED")
        DocumentFactory(
            vendor=vendor,
            document_type=DocumentCatalogFactory(is_required=False),
            status="REJECTED",
        )
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"


class TestAzioneAdminApprova:
    def test_azione_approva_rispetta_il_vincolo(self, rf):
        from django.contrib import admin

        from vendor_management_system.vendors.admin import VendorAdmin
        from vendor_management_system.vendors.models import Vendor

        conforme = VendorFactory()
        non_conforme = VendorFactory()
        DocumentFactory(vendor=non_conforme, status="PENDING")

        model_admin = VendorAdmin(Vendor, admin.site)
        messaggi = []
        model_admin.message_user = lambda request, msg, *a: messaggi.append(
            msg
        )
        model_admin.approve_vendors(
            rf.get("/"),
            Vendor.objects.filter(pk__in=[conforme.pk, non_conforme.pk]),
        )

        conforme.refresh_from_db()
        non_conforme.refresh_from_db()
        assert conforme.qualification_status == "APPROVED"
        assert non_conforme.qualification_status != "APPROVED"
        assert any(non_conforme.name in m for m in messaggi)


class TestModificaFlagCatalogo:
    def test_documento_che_diventa_obbligatorio_declassa_i_fornitori(self):
        tipo = DocumentCatalogFactory(is_required=False)
        vendor = VendorFactory(qualification_status="APPROVED")
        DocumentFactory(vendor=vendor, document_type=tipo, status="PENDING")
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"

        tipo.is_required = True
        tipo.save()

        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_requisito_che_diventa_obbligatorio_declassa_i_fornitori(self):
        competence = CompetenceFactory(is_mandatory=False)
        vendor = VendorFactory(qualification_status="APPROVED")
        VendorCompetenceFactory(vendor=vendor, competence=competence)
        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"

        competence.is_mandatory = True
        competence.save()

        vendor.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"

    def test_fornitori_non_coinvolti_restano_approvati(self):
        tipo = DocumentCatalogFactory(is_required=False)
        altro = VendorFactory(qualification_status="APPROVED")
        tipo.is_required = True
        tipo.save()
        altro.refresh_from_db()
        assert altro.qualification_status == "APPROVED"


class TestComandoRiallineamento:
    def _non_conforme(self):
        vendor = VendorFactory(qualification_status="APPROVED")
        # Riga inserita in bypass dei segnali, come dati storici.
        doc = DocumentFactory(vendor=vendor, status="PENDING")
        Vendor.objects.filter(pk=vendor.pk).update(
            qualification_status="APPROVED"
        )
        return vendor, doc

    def test_declassa_gli_approvati_non_conformi(self):
        vendor, _ = self._non_conforme()
        conforme = VendorFactory(qualification_status="APPROVED")

        call_command("sync_qualification_status")

        vendor.refresh_from_db()
        conforme.refresh_from_db()
        assert vendor.qualification_status == "TO_REVIEW"
        assert conforme.qualification_status == "APPROVED"

    def test_dry_run_non_modifica_nulla(self):
        vendor, _ = self._non_conforme()

        call_command("sync_qualification_status", "--dry-run")

        vendor.refresh_from_db()
        assert vendor.qualification_status == "APPROVED"
