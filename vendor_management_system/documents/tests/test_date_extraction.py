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
        (
            "Valido dal 12/03/2025 al 11/03/2026",
            date(2025, 3, 12),
            date(2026, 3, 11),
        ),
        (
            "In vigore dal 12/03/2025\nScade il 11/03/2026",
            date(2025, 3, 12),
            date(2026, 3, 11),
        ),
        # Accordo quadro: data nell'intestazione, durata nell'articolo finale
        (
            "Rev. 2 del 08/06/2020\nN. 202014012 DEL 14/07/2020\nTRA\n"
            "11.1 Il presente Accordo è valido ed efficace dalla data di\n"
            "sottoscrizione come in calce riportata fino al 31/12/2020; alla",
            date(2020, 7, 14),
            date(2020, 12, 31),
        ),
        (
            "Emissione: 12.03.2025 - Scadenza: 11.03.2026",
            date(2025, 3, 12),
            date(2026, 3, 11),
        ),
        (
            "Emesso in data 12 marzo 2025, valido fino al 11 marzo 2026",
            date(2025, 3, 12),
            date(2026, 3, 11),
        ),
    ],
)
def test_estrae_date_da_testo(testo, rilascio, scadenza):
    assert extract_dates_from_text(testo) == {
        "issue_date": rilascio,
        "expiry_date": scadenza,
    }


# Formulazioni diverse di documenti reali (certificati, polizze, contratti,
# testi in inglese): le regole non devono dipendere da un solo esempio.
FORMULAZIONI = [
    (
        "Data di emissione: 01/02/2025\nData di scadenza: 01/02/2026",
        date(2025, 2, 1),
        date(2026, 2, 1),
    ),
    (
        "Rilasciato il 1° febbraio 2025 - Scade il 1 febbraio 2027",
        date(2025, 2, 1),
        date(2027, 2, 1),
    ),
    (
        "Date of issue: 2025-02-01  Expiry date: 2027-02-01",
        date(2025, 2, 1),
        date(2027, 2, 1),
    ),
    (
        "Issued on 1 February 2025. Valid until 31 January 2027.",
        date(2025, 2, 1),
        date(2027, 1, 31),
    ),
    (
        "ATTESTATO valido dal 01-02-2025 al 31-01-2027",
        date(2025, 2, 1),
        date(2027, 1, 31),
    ),
    (
        "Periodo di validità: dal 1 gennaio 2024 al 31 dicembre 2026",
        date(2024, 1, 1),
        date(2026, 12, 31),
    ),
    (
        "Contratto n. 2021/45 del 03/05/2021\n"
        "art. 3 valido fino al 02/05/2024",
        date(2021, 5, 3),
        date(2024, 5, 2),
    ),
    (
        "Decorrenza: 15/03/2024  Scadenza: 15/03/2025",
        date(2024, 3, 15),
        date(2025, 3, 15),
    ),
    (
        "Certificato n. 123 emesso il 12 lug 2023. "
        "Validità fino al 11 lug 2026",
        date(2023, 7, 12),
        date(2026, 7, 11),
    ),
    (
        "Data emissione 05.06.23 Data scadenza 04.06.26",
        date(2023, 6, 5),
        date(2026, 6, 4),
    ),
    (
        "Il presente accordo decorre dal 01/09/2022 e scade il 31/08/2025",
        date(2022, 9, 1),
        date(2025, 8, 31),
    ),
    (
        "con efficacia dal 01/01/2024 fino al 31/12/2024",
        date(2024, 1, 1),
        date(2024, 12, 31),
    ),
    (
        "Data di emissione : 12 / 03 / 2025  "
        "Data di scadenza : 11 / 03 / 2026",
        date(2025, 3, 12),
        date(2026, 3, 11),
    ),
    (
        "Emesso a Roma il 12/03/2025. Scadenza 11/03/2027",
        date(2025, 3, 12),
        date(2027, 3, 11),
    ),
    (
        "Scad. 30/06/2027  Emissione 01/07/2024",
        date(2024, 7, 1),
        date(2027, 6, 30),
    ),
    ("Data di scadenza\n\n31/12/2026", None, date(2026, 12, 31)),
    ("Valido fino al 31/12/2026", None, date(2026, 12, 31)),
    # senza rinnovo tacito la data "fino al" resta una vera scadenza
    (
        "Rev. 2 del 08/06/2020\nN. 202014012 DEL 14/07/2020\nTRA\n"
        "11.1 valido ed efficace dalla data di sottoscrizione come in calce "
        "riportata fino al 31/12/2020; alla scadenza cessa ogni effetto",
        date(2020, 7, 14),
        date(2020, 12, 31),
    ),
]
# Testi che NON devono produrre date: riferimenti normativi, revisioni,
# codici, prosa con la parola "scadenza".
SENZA_DATE = [
    "Ai sensi del D.P.R. n. 1234 del 26/04/1986 si dispone",
    "Rev. 2 del 08/06/2020 - Pagina 1 di 13",
    "fatture in scadenza.\n4) CORRISPETTIVO\nRev. 2 del 08/06/2020",
    "Protocollo 12345/07/2020 verbale",
    "Testo senza alcuna data utile",
]


@pytest.mark.parametrize("testo, rilascio, scadenza", FORMULAZIONI)
def test_formulazioni_diverse(testo, rilascio, scadenza):
    assert extract_dates_from_text(testo) == {
        "issue_date": rilascio,
        "expiry_date": scadenza,
    }


@pytest.mark.parametrize("testo", SENZA_DATE)
def test_testi_senza_date_utili(testo):
    assert extract_dates_from_text(testo) == {
        "issue_date": None,
        "expiry_date": None,
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


def test_ocr_fallito_segnala_errore_invece_di_nessuna_data():
    with patch.object(date_extraction, "read_text", return_value=None):
        risultato = date_extraction.extract_dates(None, "a.pdf")

    assert risultato["error"] == "ocr_non_riuscito"
    assert risultato["issue_date"] is None


def test_suggested_dates_propaga_l_errore_ocr():
    upload = SimpleUploadedFile("a.pdf", b"%PDF-1.4")

    with patch.object(date_extraction, "read_text", return_value=None):
        risultato = date_extraction.suggested_dates(upload)

    assert risultato == {
        "issue_date": None,
        "expiry_date": None,
        "error": "ocr_non_riuscito",
    }


def test_pdf_con_testo_nativo_non_passa_dall_ocr():
    testo = "Data di emissione: 01/02/2025 " * 5
    upload = SimpleUploadedFile("a.pdf", b"%PDF-1.4")

    with (
        patch.object(date_extraction, "_pdf_native_text", return_value=testo),
        patch("pytesseract.image_to_string", side_effect=AssertionError),
    ):
        assert date_extraction.read_text(upload, "a.pdf") == testo


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


# Rinnovo tacito o durata indeterminata: nessuna scadenza, segnalata all'utente
RINNOVO = [
    # accordo quadro reale: "fino al 31/12/2020; alla scadenza si rinnoverà
    # tacitamente, per dodici mesi, e così di seguito"
    (
        "Rev. 2 del 08/06/2020\nN. 202014012 DEL 14/07/2020\nTRA\n"
        "11.1 valido ed efficace dalla data di sottoscrizione come in calce "
        "riportata fino al 31/12/2020; alla scadenza, il Contratto si "
        "rinnoverà tacitamente, per dodici mesi, e così di seguito",
        date(2020, 7, 14),
    ),
    (
        "Data di emissione 01/01/2024. Data di scadenza 31/12/2024, con "
        "tacito rinnovo annuale",
        date(2024, 1, 1),
    ),
    (
        "Emesso il 01/01/2024. Il contratto è a tempo indeterminato.",
        date(2024, 1, 1),
    ),
    ("Auto-renewal: expires 31/12/2030, renews automatically", None),
]


@pytest.mark.parametrize("testo, rilascio", RINNOVO)
def test_rinnovo_tacito_lascia_vuota_la_scadenza(testo, rilascio):
    assert extract_dates_from_text(testo) == {
        "issue_date": rilascio,
        "expiry_date": None,
        "auto_renewal": True,
    }


def test_personale_a_tempo_indeterminato_non_cancella_la_scadenza():
    testo = (
        "Data di scadenza 31/12/2026. Il personale è assunto a tempo "
        "indeterminato."
    )

    assert extract_dates_from_text(testo) == {
        "issue_date": None,
        "expiry_date": date(2026, 12, 31),
    }


def test_suggested_dates_riporta_il_rinnovo_tacito():
    upload = SimpleUploadedFile("a.pdf", b"%PDF-1.4")
    letto = {
        "issue_date": date(2020, 7, 14),
        "expiry_date": None,
        "auto_renewal": True,
    }

    with patch.object(date_extraction, "extract_dates", return_value=letto):
        risultato = date_extraction.suggested_dates(upload)

    assert risultato == {
        "issue_date": "2020-07-14",
        "expiry_date": None,
        "auto_renewal": True,
    }
