"""Test della dashboard consolidata back-office.

Copre il layout ibrido: KPI globali (tutto il sistema, indipendenti dal
gestore) + sezioni personali (fornitori con `managed_by == request.user`)
per gli aggiornamenti da revisionare e i fornitori senza documenti/
requisiti assegnati.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import (
    DocumentFactory,
    VendorCompetenceFactory,
    VendorUserFactory,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

User = get_user_model()
PASSWORD = "test-pass-1234"


def _login_as_bo(client, email="bo-reviewer@example.invalid"):
    bo_user = User.objects.create_user(
        email=email, password=PASSWORD, role="bo_user"
    )
    client.login(email=bo_user.email, password=PASSWORD)
    return bo_user


@pytest.mark.django_db
class TestBoDashboardPermissions:
    def test_vendor_user_cannot_access(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:bo-dashboard"))
        assert response.status_code == 302

    def test_bo_user_can_access(self, client):
        _login_as_bo(client)
        response = client.get(reverse("portal:bo-dashboard"))
        assert response.status_code == 200

    def test_navbar_links_back_to_admin(self, client):
        """AIDEV-45: la navbar deve avere un link per tornare a /admin/."""
        _login_as_bo(client)
        response = client.get(reverse("portal:bo-dashboard"))
        assert reverse("admin:index").encode() in response.content


@pytest.mark.django_db
class TestBoDashboardGlobalKpis:
    def test_totals_are_system_wide_not_scoped_to_manager(self, client):
        bo_user = _login_as_bo(client)
        other_manager = User.objects.create_user(
            email="other-manager@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        my_vendor = VendorFactory(managed_by=bo_user)
        other_vendor = VendorFactory(managed_by=other_manager)

        DocumentFactory(vendor=my_vendor, status="UPLOADED")
        DocumentFactory(vendor=other_vendor, status="UPLOADED")
        VendorCompetenceFactory(
            vendor=my_vendor,
            document_file="vendor_competences/2026/09/a.pdf",
            verified=False,
        )
        VendorCompetenceFactory(
            vendor=other_vendor,
            document_file="vendor_competences/2026/09/b.pdf",
            verified=False,
        )
        VendorChangeRequest.objects.create(
            vendor=my_vendor, changes={"name": {"old": "a", "new": "b"}}
        )
        VendorChangeRequest.objects.create(
            vendor=other_vendor, changes={"name": {"old": "a", "new": "b"}}
        )

        response = client.get(reverse("portal:bo-dashboard"))

        assert response.context["documents_pending_review"] == 2
        assert response.context["requirements_pending_review"] == 2
        assert response.context["change_requests_pending"] == 2


@pytest.mark.django_db
class TestBoDashboardPersonalSections:
    def test_pending_items_scoped_to_logged_in_manager(self, client):
        bo_user = _login_as_bo(client)
        other_manager = User.objects.create_user(
            email="other-manager-2@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        my_vendor = VendorFactory(managed_by=bo_user)
        other_vendor = VendorFactory(managed_by=other_manager)

        my_document = DocumentFactory(vendor=my_vendor, status="UPLOADED")
        DocumentFactory(vendor=other_vendor, status="UPLOADED")
        my_requirement = VendorCompetenceFactory(
            vendor=my_vendor,
            document_file="vendor_competences/2026/09/c.pdf",
            verified=False,
        )
        VendorCompetenceFactory(
            vendor=other_vendor,
            document_file="vendor_competences/2026/09/d.pdf",
            verified=False,
        )
        my_request = VendorChangeRequest.objects.create(
            vendor=my_vendor, changes={"name": {"old": "a", "new": "b"}}
        )
        VendorChangeRequest.objects.create(
            vendor=other_vendor, changes={"name": {"old": "a", "new": "b"}}
        )

        response = client.get(reverse("portal:bo-dashboard"))

        assert list(response.context["my_pending_documents"]) == [my_document]
        assert list(response.context["my_pending_requirements"]) == [
            my_requirement
        ]
        assert list(response.context["my_pending_change_requests"]) == [
            my_request
        ]

    def test_vendors_without_documents_scoped_to_manager(self, client):
        bo_user = _login_as_bo(client)
        other_manager = User.objects.create_user(
            email="other-manager-3@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        vendor_without_docs = VendorFactory(managed_by=bo_user)
        vendor_with_docs = VendorFactory(managed_by=bo_user)
        DocumentFactory(vendor=vendor_with_docs)
        other_vendor_without_docs = VendorFactory(managed_by=other_manager)

        response = client.get(reverse("portal:bo-dashboard"))

        vendors = list(response.context["my_vendors_without_documents"])
        assert vendor_without_docs in vendors
        assert vendor_with_docs not in vendors
        assert other_vendor_without_docs not in vendors

    def test_vendors_without_requirements_scoped_to_manager(self, client):
        bo_user = _login_as_bo(client)
        vendor_without_reqs = VendorFactory(managed_by=bo_user)
        vendor_with_reqs = VendorFactory(managed_by=bo_user)
        VendorCompetenceFactory(vendor=vendor_with_reqs)

        response = client.get(reverse("portal:bo-dashboard"))

        vendors = list(response.context["my_vendors_without_requirements"])
        assert vendor_without_reqs in vendors
        assert vendor_with_reqs not in vendors


@pytest.mark.django_db
class TestBoDashboardExpired:
    """I conteggi/liste "scaduti" guardano `expiry_date` direttamente, non
    lo stato salvato (che si aggiorna solo al prossimo save(), vedi
    `documents/tasks.py` vuoto — nessun job periodico lo tiene allineato)."""

    def test_global_expired_counts_are_system_wide(self, client):
        bo_user = _login_as_bo(client)
        other_manager = User.objects.create_user(
            email="other-manager-4@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        yesterday = timezone.now().date() - timedelta(days=1)
        my_vendor = VendorFactory(managed_by=bo_user)
        other_vendor = VendorFactory(managed_by=other_manager)
        DocumentFactory(vendor=my_vendor, expiry_date=yesterday)
        DocumentFactory(vendor=other_vendor, expiry_date=yesterday)
        VendorCompetenceFactory(vendor=my_vendor, expiry_date=yesterday)
        VendorCompetenceFactory(vendor=other_vendor, expiry_date=yesterday)

        response = client.get(reverse("portal:bo-dashboard"))

        assert response.context["documents_expired"] == 2
        assert response.context["requirements_expired"] == 2

    def test_personal_expired_lists_scoped_to_manager(self, client):
        bo_user = _login_as_bo(client)
        other_manager = User.objects.create_user(
            email="other-manager-5@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        yesterday = timezone.now().date() - timedelta(days=1)
        tomorrow = timezone.now().date() + timedelta(days=1)
        my_vendor = VendorFactory(managed_by=bo_user)
        other_vendor = VendorFactory(managed_by=other_manager)

        my_expired_document = DocumentFactory(
            vendor=my_vendor, expiry_date=yesterday
        )
        DocumentFactory(vendor=my_vendor, expiry_date=tomorrow)
        DocumentFactory(vendor=other_vendor, expiry_date=yesterday)

        my_expired_requirement = VendorCompetenceFactory(
            vendor=my_vendor, expiry_date=yesterday
        )
        VendorCompetenceFactory(vendor=my_vendor, expiry_date=tomorrow)
        VendorCompetenceFactory(vendor=other_vendor, expiry_date=yesterday)

        response = client.get(reverse("portal:bo-dashboard"))

        assert list(response.context["my_expired_documents"]) == [
            my_expired_document
        ]
        assert list(response.context["my_expired_requirements"]) == [
            my_expired_requirement
        ]
