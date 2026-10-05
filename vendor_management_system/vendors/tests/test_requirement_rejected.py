"""Un requisito respinto dall'ufficio si distingue da uno non ancora
verificato (`VendorCompetence.rejected`), come già avviene per i documenti."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from vendor_management_system.portal.tests.factories import (
    CompetenceFactory,
    VendorCompetenceFactory,
    VendorUserFactory,
)
from vendor_management_system.vendors.models import Vendor

pytestmark = pytest.mark.django_db

User = get_user_model()
PASSWORD = "test-pass-1234"


def _file():
    return SimpleUploadedFile("nuovo.pdf", b"contenuto", "application/pdf")


def _req(**extra):
    campi = {"document_file": "vendor_competences/a.pdf"}
    campi.update(extra)
    return VendorCompetenceFactory(**campi)


def _login_bo(client):
    user = User.objects.create_user(
        email="bo-rej@example.invalid", password=PASSWORD, role="bo_user"
    )
    client.login(email=user.email, password=PASSWORD)


def _review(client, req, action):
    return client.post(
        reverse("portal:bo-requirement-review", kwargs={"pk": req.pk}),
        {"action": action},
    )


class TestModello:
    def test_rifiutare_dal_backoffice_segna_il_requisito_come_respinto(
        self, client
    ):
        _login_bo(client)
        req = _req()

        _review(client, req, "reject")

        req.refresh_from_db()
        assert req.rejected is True
        assert req.verified is False

    def test_verificare_azzera_il_rifiuto(self, client):
        _login_bo(client)
        req = _req(rejected=True)

        _review(client, req, "approve")

        req.refresh_from_db()
        assert req.verified is True
        assert req.rejected is False

    def test_spuntare_verificato_da_admin_azzera_il_rifiuto(self):
        req = _req(rejected=True)

        req.verified = True
        req.save()

        req.refresh_from_db()
        assert req.rejected is False

    def test_un_nuovo_upload_azzera_il_rifiuto(self):
        req = _req(rejected=True)

        req.submit_upload(document_file=_file())

        req.refresh_from_db()
        assert req.rejected is False

    def test_un_requisito_respinto_non_e_consegnato(self):
        assert _req(rejected=True).is_delivered is False
        assert _req(rejected=False).is_delivered is True

    def test_rifiutare_una_revisione_in_attesa_non_respinge_il_requisito(
        self, client
    ):
        _login_bo(client)
        req = _req(verified=True)
        req.submit_upload(document_file=_file())

        _review(client, req, "reject")

        req.refresh_from_db()
        assert req.verified is True
        assert req.rejected is False


class TestStatoFornitore:
    def _setup(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        Vendor.objects.filter(pk=user.vendor.pk).update(
            qualification_status="REJECTED"
        )
        respinto = _req(
            vendor=user.vendor,
            competence=CompetenceFactory(is_mandatory=True),
            rejected=True,
        )
        return user, respinto

    def _stato(self, user):
        user.vendor.refresh_from_db()
        return user.vendor.qualification_status

    def test_il_requisito_respinto_ricaricato_porta_a_da_revisionare(
        self, client
    ):
        user, respinto = self._setup(client)

        client.post(
            reverse(
                "portal:my-requirement-upload", kwargs={"pk": respinto.pk}
            ),
            {"document_file": _file()},
        )

        assert self._stato(user) == "TO_REVIEW"

    def test_un_altro_upload_non_basta_se_resta_un_respinto(self, client):
        user, _ = self._setup(client)
        altro = _req(
            vendor=user.vendor,
            competence=CompetenceFactory(is_mandatory=True),
            document_file=None,
        )

        client.post(
            reverse("portal:my-requirement-upload", kwargs={"pk": altro.pk}),
            {"document_file": _file()},
        )

        assert self._stato(user) == "REJECTED"


class TestListeEViste:
    def test_la_coda_di_default_esclude_i_respinti(self, client):
        _login_bo(client)
        da_verificare = _req()
        respinto = _req(rejected=True)

        response = client.get(reverse("portal:bo-requirements"))

        requisiti = list(response.context["requirements"])
        assert da_verificare in requisiti
        assert respinto not in requisiti

    def test_il_filtro_respinti_li_mostra(self, client):
        _login_bo(client)
        da_verificare = _req()
        respinto = _req(rejected=True)

        response = client.get(
            reverse("portal:bo-requirements"), {"verified": "rejected"}
        )

        requisiti = list(response.context["requirements"])
        assert respinto in requisiti
        assert da_verificare not in requisiti

    def test_il_kpi_requisiti_da_revisionare_esclude_i_respinti(self, client):
        _login_bo(client)
        _req()
        _req(rejected=True)

        response = client.get(reverse("portal:bo-dashboard"))

        assert response.context["requirements_pending_review"] == 1

    def test_il_fornitore_vede_il_requisito_come_respinto(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        req = _req(vendor=user.vendor, rejected=True)

        dettaglio = client.get(
            reverse("portal:my-requirement-detail", kwargs={"pk": req.pk})
        )
        elenco = client.get(reverse("portal:my-requirements"))

        assert "Respinto" in dettaglio.content.decode()
        assert "Respinto" in elenco.content.decode()
