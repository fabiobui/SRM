"""Test dell'area back-office di revisione delle richieste di modifica.

Copre l'approvazione/rifiuto delle richieste anagrafica (target=Vendor),
di modifica su un servizio esistente (target=VendorService), di aggiunta
(ADD_SERVICE, crea un nuovo VendorService) e di eliminazione (DELETE_SERVICE,
cancella il VendorService), verificando che `apply_to_vendor()` agisca
correttamente in tutti i casi.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import (
    ServiceTypeFactory,
    VendorServiceFactory,
    VendorUserFactory,
)
from vendor_management_system.vendors.models import VendorService

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

    def test_bo_change_requests_list_excludes_service_requests(self, client):
        """Le richieste sui servizi hanno una lista BO dedicata (vedi
        `TestBoServiceRequestListView`): la lista "Richieste anagrafica"
        mostra solo le richieste di sola anagrafica."""
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
        assert change_request not in requests


@pytest.mark.django_db
class TestBoChangeRequestReviewAddService:
    def _login_as_bo(self, client):
        bo_user = User.objects.create_user(
            email="bo-reviewer-add@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        client.login(email=bo_user.email, password=PASSWORD)
        return bo_user

    def _leaf_service_type(self):
        section = ServiceTypeFactory()
        return ServiceTypeFactory(parent=section)

    def test_approve_creates_vendor_service(self, client):
        bo_user = self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service_type = self._leaf_service_type()
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
            service_type=service_type,
            requested_by=vendor_user,
            changes={
                "is_primary": {"old": None, "new": True},
                "notes": {"old": None, "new": "richiesta test"},
            },
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        change_request.refresh_from_db()
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED
        assert change_request.reviewed_by.email == bo_user.email
        created = VendorService.objects.get(
            vendor=vendor_user.vendor, service_type=service_type
        )
        assert created.is_primary is True
        assert created.notes == "richiesta test"

    def test_reject_does_not_create_vendor_service(self, client):
        self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service_type = self._leaf_service_type()
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
            service_type=service_type,
            requested_by=vendor_user,
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "reject", "review_notes": "non necessario"},
        )

        assert response.status_code == 302
        change_request.refresh_from_db()
        assert change_request.status == VendorChangeRequest.STATUS_REJECTED
        assert not VendorService.objects.filter(
            vendor=vendor_user.vendor, service_type=service_type
        ).exists()


@pytest.mark.django_db
class TestBoChangeRequestReviewDeleteService:
    def _login_as_bo(self, client):
        bo_user = User.objects.create_user(
            email="bo-reviewer-delete@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        client.login(email=bo_user.email, password=PASSWORD)
        return bo_user

    def test_approve_deletes_service_and_keeps_request_history(self, client):
        bo_user = self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor)
        service_pk = service.pk
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            request_type=VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE,
            requested_by=vendor_user,
            changes={
                "service_type": {
                    "old": str(service.service_type),
                    "new": None,
                }
            },
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        assert not VendorService.objects.filter(pk=service_pk).exists()
        # la richiesta sopravvive alla cancellazione del servizio (con lo
        # storico intatto) grazie a vendor_service.on_delete=SET_NULL
        change_request.refresh_from_db()
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED
        assert change_request.reviewed_by.email == bo_user.email
        assert change_request.vendor_service_id is None

    def test_reject_leaves_service_intact(self, client):
        self._login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor)
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            request_type=VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE,
            requested_by=vendor_user,
        )

        response = client.post(
            reverse(
                "portal:bo-change-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "reject", "review_notes": "mantieni servizio"},
        )

        assert response.status_code == 302
        assert VendorService.objects.filter(pk=service.pk).exists()
        change_request.refresh_from_db()
        assert change_request.status == VendorChangeRequest.STATUS_REJECTED
        assert change_request.vendor_service_id == service.pk
