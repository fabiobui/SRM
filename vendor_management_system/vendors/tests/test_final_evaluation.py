"""Valutazione Finale del Fornitore calcolata in automatico (bollino).

Verde (POSITIVO) se il fornitore è Approvato e attivo in Embyon, rosso
(NEGATIVO) se è Respinto o non attivo in Embyon, grigio (DA VALUTARE) se la
qualifica è ancora in corso. Non è modificabile a mano.
"""

import importlib
import json
from datetime import timedelta

import pytest
from django.apps import apps
from django.contrib import admin
from django.urls import reverse
from django.utils import timezone

from vendor_management_system.documents.models import Document
from vendor_management_system.portal.tests.factories import DocumentFactory
from vendor_management_system.vendors.admin import (
    VendorAdmin,
    VendorAdminForm,
)
from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.serializers import (
    VendorQualificationSerializer,
)
from vendor_management_system.vendors.tasks import (
    sync_qualification_status_task,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db


def _evaluation(vendor):
    vendor.refresh_from_db()
    return vendor.vendor_final_evaluation


@pytest.mark.parametrize(
    ("status", "embyon_active", "expected"),
    [
        ("APPROVED", True, "POSITIVO"),
        ("APPROVED", False, "NEGATIVO"),
        ("REJECTED", True, "NEGATIVO"),
        ("PENDING", True, "DA VALUTARE"),
        ("TO_REVIEW", True, "DA VALUTARE"),
        ("PENDING", False, "NEGATIVO"),
    ],
)
def test_bollino_calcolato_al_salvataggio(status, embyon_active, expected):
    vendor = VendorFactory(embyon_active=embyon_active)
    vendor.qualification_status = status
    vendor.save()
    assert _evaluation(vendor) == expected


def test_save_con_update_fields_salva_anche_il_bollino():
    vendor = VendorFactory(qualification_status="APPROVED")
    assert _evaluation(vendor) == "POSITIVO"

    vendor.embyon_active = False
    vendor.save(update_fields=["embyon_active"])

    assert _evaluation(vendor) == "NEGATIVO"


def test_documento_obbligatorio_non_valido_rende_grigio_il_bollino():
    vendor = VendorFactory(qualification_status="APPROVED")
    assert _evaluation(vendor) == "POSITIVO"

    DocumentFactory(vendor=vendor, status="UPLOADED", file="x.pdf")

    vendor.refresh_from_db()
    assert vendor.qualification_status == "TO_REVIEW"
    assert vendor.vendor_final_evaluation == "DA VALUTARE"


def test_campo_non_modificabile_da_admin_e_api():
    vendor = VendorFactory(qualification_status="PENDING")
    assert "vendor_final_evaluation" not in VendorAdminForm.base_fields

    serializer = VendorQualificationSerializer(
        vendor, data={"vendor_final_evaluation": "POSITIVO"}, partial=True
    )
    assert serializer.is_valid()
    serializer.save()
    assert _evaluation(vendor) == "DA VALUTARE"


def test_bollino_ultima_colonna_della_lista_admin():
    colonne = VendorAdmin.list_display
    assert colonne[-1] == "final_evaluation_badge"
    assert colonne.index("embyon_active") < colonne.index(
        "final_evaluation_badge"
    )
    assert "qualification_score" not in colonne
    assert "competence_areas_display" not in colonne


def test_scheda_admin_mostra_il_bollino(admin_client):
    vendor = VendorFactory(qualification_status="APPROVED")

    risposta = admin_client.get(
        reverse("admin:vendors_vendor_change", args=[vendor.pk])
    )

    assert risposta.status_code == 200
    assert "&#9679; Positivo" in risposta.content.decode()


def test_azione_respingi_rende_rosso_il_bollino(rf):
    vendor = VendorFactory(qualification_status="APPROVED")
    model_admin = VendorAdmin(Vendor, admin.site)
    model_admin.message_user = lambda *args, **kwargs: None

    model_admin.reject_vendors(
        rf.get("/"), Vendor.objects.filter(pk=vendor.pk)
    )

    assert _evaluation(vendor) == "NEGATIVO"


def test_dashboard_espone_e_conta_il_bollino(admin_client):
    positivo = VendorFactory(qualification_status="APPROVED")
    VendorFactory(qualification_status="APPROVED", embyon_active=False)

    risposta = admin_client.get(reverse("vendor-dashboard"))

    righe = {
        riga["vendor_code"]: riga["vendor_final_evaluation"]
        for riga in json.loads(risposta.context["vendors_data_json"])
    }
    assert righe[positivo.vendor_code] == "POSITIVO"
    assert risposta.context["positive_vendors"] == 1


def test_job_giornaliero_declassa_gli_approvati_con_documenti_scaduti():
    vendor = VendorFactory(qualification_status="APPROVED")
    doc = DocumentFactory(
        vendor=vendor,
        status="APPROVED",
        file="a.pdf",
        expiry_date=timezone.now().date() + timedelta(days=10),
    )
    assert _evaluation(vendor) == "POSITIVO"
    # La scadenza arriva col passare del tempo, senza alcun salvataggio.
    Document.objects.filter(pk=doc.pk).update(
        expiry_date=timezone.now().date() - timedelta(days=1)
    )
    # Bollino disallineato da una scrittura che salta save().
    altro = VendorFactory(qualification_status="PENDING")
    Vendor.objects.filter(pk=altro.pk).update(vendor_final_evaluation="X")

    risultato = sync_qualification_status_task.apply().get()

    vendor.refresh_from_db()
    assert vendor.qualification_status == "TO_REVIEW"
    assert vendor.vendor_final_evaluation == "DA VALUTARE"
    assert _evaluation(altro) == "DA VALUTARE"
    assert risultato["downgraded"] == 1


def test_migrazione_ricalcola_le_vecchie_valutazioni_manuali():
    vendor = VendorFactory(qualification_status="APPROVED")
    in_attesa = VendorFactory(qualification_status="PENDING")
    Vendor.objects.update(vendor_final_evaluation="MOLTO POSITIVO")
    migrazione = importlib.import_module(
        "vendor_management_system.vendors.migrations."
        "0053_valutazione_finale_automatica"
    )

    migrazione.ricalcola_valutazione_finale(apps, None)

    assert _evaluation(vendor) == "POSITIVO"
    assert _evaluation(in_attesa) == "DA VALUTARE"
