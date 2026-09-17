"""Test dell'area back-office di revisione delle richieste di modifica.

Copre l'approvazione/rifiuto sia delle richieste anagrafica (target=Vendor)
sia di quelle sui servizi (target=VendorService), verificando che
`apply_to_vendor()` scriva sul target corretto in entrambi i casi.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import (
    VendorServiceFactory,
    VendorUserFactory,
)

User = get_user_model()
PASSWORD = "test-pass-1234"


@pytest.mark.django_db
class TestBoChangeRequestReviewProfile:
    def _login_as_bo(self, client):
        bo_user = User.objects.create_user(
            email="bo-reviewer@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        client.login(email=bo_user.email, password=PASSWORD)
        return bo_user

    def test_approve_applies_diff_to_vendor(self, client):
        bo_user = self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        vendor = vendor_user.vendor
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=vendor_user,
            changes={"name": {"old": vendor.name, "new": "Nuovo Nome SRL"}},
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "approve", "review_notes": "ok"},
        )

        assert response.status_code == 302
        vendor.refresh_from_db()
        change_request.refresh_from_db()
        assert vendor.name == "Nuovo Nome SRL"
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED
        assert change_request.reviewed_by.email == bo_user.email
        assert change_request.reviewed_at is not None

    def test_reject_does_not_apply_diff(self, client):
        self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        vendor = vendor_user.vendor
        original_name = vendor.name
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=vendor_user,
            changes={"name": {"old": original_name, "new": "Nome Scartato"}},
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "reject", "review_notes": "non conforme"},
        )

        assert response.status_code == 302
        vendor.refresh_from_db()
        change_request.refresh_from_db()
        assert vendor.name == original_name
        assert change_request.status == VendorChangeRequest.STATUS_REJECTED
        assert change_request.review_notes == "non conforme"

    def test_already_reviewed_request_cannot_be_reviewed_again(self, client):
        self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        vendor = vendor_user.vendor
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=vendor_user,
            changes={"name": {"old": vendor.name, "new": "X"}},
            status=VendorChangeRequest.STATUS_APPROVED,
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "reject", "review_notes": "troppo tardi"},
        )

        assert response.status_code == 302
        change_request.refresh_from_db()
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED


@pytest.mark.django_db
class TestBoChangeRequestReviewService:
    def _login_as_bo(self, client):
        bo_user = User.objects.create_user(
            email="bo-reviewer-2@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        client.login(email=bo_user.email, password=PASSWORD)
        return bo_user

    def test_approve_applies_diff_to_service_not_vendor(self, client):
        bo_user = self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(
            vendor=vendor_user.vendor, is_primary=False
        )
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=vendor_user,
            changes={"is_primary": {"old": False, "new": True}},
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        service.refresh_from_db()
        change_request.refresh_from_db()
        assert service.is_primary is True
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED
        assert change_request.reviewed_by.email == bo_user.email

    def test_bo_change_requests_list_includes_service_requests(self, client):
        self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor)
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=vendor_user,
            changes={"notes": {"old": "", "new": "nuova nota"}},
        )

        response = client.get(reverse("portal:bo-change-requests"))

        assert response.status_code == 200
        requests = list(response.context["requests"])
        assert change_request in requests
