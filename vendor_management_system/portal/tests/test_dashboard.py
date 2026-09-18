"""Test della dashboard fornitore (home ``/portale/``).

Copre il fix AIDEV-44: le card KPI mescolavano ``Document`` e
``VendorCompetence`` sotto un'unica etichetta generica — es. "in
revisione" mostrava solo i ``Document`` in stato ``UPLOADED``, nascondendo
i ``VendorCompetence`` (requisiti) in revisione — e non separava le
richieste di modifica servizio da quelle anagrafica (le prime non erano
mostrate da nessuna parte).
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import (
    DocumentFactory,
    VendorCompetenceFactory,
    VendorServiceFactory,
    VendorUserFactory,
)

PASSWORD = "test-pass-1234"


@pytest.mark.django_db
class TestPortalDashboardStats:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user.vendor

    def test_doc_and_req_in_review_are_counted_separately(self, client):
        """Bug segnalato: 2 documenti + 2 requisiti in revisione devono
        restare visibili come 2 e 2, non collassare in un unico "2"."""
        vendor = self._login(client)
        DocumentFactory(vendor=vendor, status="UPLOADED")
        DocumentFactory(vendor=vendor, status="UPLOADED")
        VendorCompetenceFactory(
            vendor=vendor, document_file="reqs/a.pdf", verified=False
        )
        VendorCompetenceFactory(
            vendor=vendor, document_file="reqs/b.pdf", verified=False
        )

        response = client.get(reverse("portal:dashboard"))

        assert response.context["doc_stats"]["in_review"] == 2
        assert response.context["req_stats"]["in_review"] == 2

    def test_doc_stats_breakdown(self, client):
        vendor = self._login(client)
        DocumentFactory(vendor=vendor, status="PENDING")
        DocumentFactory(vendor=vendor, status="UPLOADED")
        DocumentFactory(vendor=vendor, status="APPROVED")
        DocumentFactory(vendor=vendor, status="EXPIRED")

        response = client.get(reverse("portal:dashboard"))

        assert response.context["doc_stats"] == {
            "to_upload": 1,
            "in_review": 1,
            "approved": 1,
            "expired": 1,
        }

    def test_req_stats_breakdown(self, client):
        vendor = self._login(client)
        VendorCompetenceFactory(vendor=vendor, document_file="")  # da caricare
        VendorCompetenceFactory(
            vendor=vendor, document_file="reqs/b.pdf", verified=False
        )  # in revisione
        VendorCompetenceFactory(
            vendor=vendor, document_file="reqs/c.pdf", verified=True
        )  # approvato
        VendorCompetenceFactory(
            vendor=vendor,
            document_file="reqs/d.pdf",
            verified=True,
            expiry_date=timezone.now().date() - timedelta(days=1),
        )  # approvato ma ormai scaduto

        response = client.get(reverse("portal:dashboard"))
        stats = response.context["req_stats"]

        assert stats["to_upload"] == 1
        assert stats["in_review"] == 1
        assert stats["approved"] == 2
        assert stats["expired"] == 1

    def test_anagrafica_and_servizi_change_requests_not_mixed(self, client):
        vendor = self._login(client)
        service = VendorServiceFactory(vendor=vendor)

        VendorChangeRequest.objects.create(vendor=vendor, changes={})
        VendorChangeRequest.objects.create(
            vendor=vendor,
            changes={},
            status=VendorChangeRequest.STATUS_APPROVED,
        )
        VendorChangeRequest.objects.create(
            vendor=vendor, vendor_service=service, changes={}
        )
        VendorChangeRequest.objects.create(
            vendor=vendor,
            vendor_service=service,
            changes={},
            status=VendorChangeRequest.STATUS_REJECTED,
        )

        response = client.get(reverse("portal:dashboard"))

        assert response.context["anagrafica_stats"] == {
            "pending": 1,
            "approved": 1,
            "rejected": 0,
        }
        assert response.context["servizi_stats"] == {
            "pending": 1,
            "approved": 0,
            "rejected": 1,
        }
