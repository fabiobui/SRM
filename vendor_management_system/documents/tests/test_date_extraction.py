"""Estrazione automatica delle date dal testo OCR dei documenti."""

from datetime import date
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.documents import date_extraction
from vendor_management_system.documents.date_extraction import (
    extract_dates_from_text,
)
from vendor_management_system.portal.tests.factories import VendorUserFactory


@pytest.mark.parametrize(
    "testo, rilascio, scadenza",
    [
        (
            "Data di emissione: 01/02/2025\nData di scadenza: 31/01/2026",
            date(2025, 2, 1),
            date(2026, 1, 31),
        ),
        (
            "Rilasciato il 5 marzo 2024. Valido fino al 05.03.2027",
            date(2024, 3, 5),
            date(2027, 3, 5),
        ),
        # L'OCR spesso manda a capo tra etichetta e valore.
        ("Scadenza\n 10-12-2026", None, date(2026, 12, 10)),
        ("Nessuna data utile qui", None, None),
    ],
)
def test_estrae_date_da_testo(testo, rilascio, scadenza):
    assert extract_dates_from_text(testo) == {
        "issue_date": rilascio,
        "expiry_date": scadenza,
    }


def test_scadenza_prima_del_rilascio_viene_scartata():
    risultato = extract_dates_from_text(
        "Data di emissione 01/01/2026 Data di scadenza 01/01/2020"
    )

    assert risultato == {"issue_date": None, "expiry_date": None}


def test_ocr_non_disponibile_restituisce_nessuna_data():
    with patch.object(date_extraction, "read_text", return_value=""):
        risultato = date_extraction.extract_dates(None, "a.pdf")

    assert risultato == {"issue_date": None, "expiry_date": None}


@pytest.mark.django_db
class TestEndpointEstraiDate:
    PASSWORD = "test-pass-1234"

    def _login(self, client):
        user = VendorUserFactory(password=self.PASSWORD)
        client.login(email=user.email, password=self.PASSWORD)

    def test_restituisce_le_date_lette(self, client):
        self._login(client)
        letto = {
            "issue_date": date(2025, 2, 1),
            "expiry_date": date(2026, 1, 31),
        }

        with patch(
            "vendor_management_system.documents.date_extraction.extract_dates",
            return_value=letto,
        ):
            response = client.post(
                reverse("portal:extract-dates"),
                {"file": SimpleUploadedFile("a.pdf", b"%PDF-1.4")},
            )

        assert response.json() == {
            "issue_date": "2025-02-01",
            "expiry_date": "2026-01-31",
        }

    def test_senza_file_nessuna_data(self, client):
        self._login(client)

        response = client.post(reverse("portal:extract-dates"))

        assert response.json() == {"issue_date": None, "expiry_date": None}

    def test_richiede_login_fornitore(self, client):
        response = client.post(
            reverse("portal:extract-dates"),
            {"file": SimpleUploadedFile("a.pdf", b"%PDF-1.4")},
        )

        assert response.status_code in (302, 403)


@pytest.mark.django_db
class TestEndpointAdminEstraiDate:
    def _url(self):
        return reverse("admin:vendors_vendor_extract_dates")

    def test_staff_riceve_le_date_lette(self, admin_client):
        letto = {"issue_date": date(2025, 2, 1), "expiry_date": None}

        with patch(
            "vendor_management_system.documents.date_extraction.extract_dates",
            return_value=letto,
        ):
            response = admin_client.post(
                self._url(),
                {"file": SimpleUploadedFile("a.pdf", b"%PDF-1.4")},
            )

        assert response.json() == {
            "issue_date": "2025-02-01",
            "expiry_date": None,
        }

    def test_get_non_ammesso(self, admin_client):
        assert admin_client.get(self._url()).status_code == 405

    def test_senza_login_staff_reindirizza(self, client):
        response = client.post(self._url())

        assert response.status_code == 302
