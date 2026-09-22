"""Test dell'area back-office dedicata alle richieste sui servizi.

`BoServiceRequestListView`/`DetailView`/`ReviewView` sono l'equivalente,
per i servizi, di `BoChangeRequestListView`/`DetailView`/`ReviewView` per
l'anagrafica: stessa struttura (lista con filtro stato, dettaglio con form
di approvazione/rifiuto), ma ristretta alle `VendorChangeRequest` con
`vendor_service` o `service_type` valorizzato (modifica, aggiunta o
eliminazione di un servizio) — le richieste di sola anagrafica restano
fuori da questa area, vedi `test_backoffice_change_requests.py`.
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


def _login_as_bo(client, email="bo-reviewer-svc@example.invalid"):
    bo_user = User.objects.create_user(
        email=email, password=PASSWORD, role="bo_user"
    )
    client.login(email=bo_user.email, password=PASSWORD)
    return bo_user


def _leaf_service_type():
    section = ServiceTypeFactory()
    return ServiceTypeFactory(parent=section)


@pytest.mark.django_db
class TestBoServiceRequestListPermissions:
    def test_vendor_user_cannot_access(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:bo-service-requests"))
        assert response.status_code == 302

    def test_bo_user_can_access(self, client):
        _login_as_bo(client)
        response = client.get(reverse("portal:bo-service-requests"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestBoServiceRequestListFiltering:
    def test_includes_edit_add_and_delete_requests(self, client):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor)
        edit_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=vendor_user,
            changes={"notes": {"old": "", "new": "nuova nota"}},
        )
        add_request = VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
            service_type=_leaf_service_type(),
            requested_by=vendor_user,
        )
        delete_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            request_type=VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE,
            requested_by=vendor_user,
        )

        response = client.get(reverse("portal:bo-service-requests"))

        requests = list(response.context["requests"])
        assert edit_request in requests
        assert add_request in requests
        assert delete_request in requests

    def test_excludes_profile_only_requests(self, client):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        profile_request = VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            requested_by=vendor_user,
            changes={"name": {"old": "a", "new": "b"}},
        )

        response = client.get(reverse("portal:bo-service-requests"))

        assert profile_request not in list(response.context["requests"])

    def test_status_filter(self, client):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor)
        approved_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=vendor_user,
            status=VendorChangeRequest.STATUS_APPROVED,
            changes={},
        )

        response = client.get(
            reverse("portal:bo-service-requests"), {"status": "APPROVED"}
        )

        assert approved_request in list(response.context["requests"])


@pytest.mark.django_db
class TestBoServiceRequestDetail:
    def test_profile_only_request_is_not_reachable(self, client):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        profile_request = VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            requested_by=vendor_user,
            changes={"name": {"old": "a", "new": "b"}},
        )

        response = client.get(
            reverse(
                "portal:bo-service-request-detail",
                kwargs={"pk": profile_request.pk},
            )
        )

        assert response.status_code == 404

    def test_service_request_renders_with_dedicated_review_action(
        self, client
    ):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor)
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=vendor_user,
            changes={"notes": {"old": "", "new": "nuova nota"}},
        )

        response = client.get(
            reverse(
                "portal:bo-service-request-detail",
                kwargs={"pk": change_request.pk},
            )
        )

        assert response.status_code == 200
        expected_review_url = reverse(
            "portal:bo-service-request-review",
            kwargs={"pk": change_request.pk},
        )
        assert expected_review_url.encode() in response.content


@pytest.mark.django_db
class TestBoServiceRequestReview:
    def test_approve_add_service_creates_vendor_service(self, client):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service_type = _leaf_service_type()
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
            service_type=service_type,
            requested_by=vendor_user,
            changes={"is_primary": {"old": None, "new": True}},
        )

        response = client.post(
            reverse(
                "portal:bo-service-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        change_request.refresh_from_db()
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED
        assert VendorService.objects.filter(
            vendor=vendor_user.vendor, service_type=service_type
        ).exists()

    def test_approve_delete_service_removes_it(self, client):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor)
        service_pk = service.pk
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            request_type=VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE,
            requested_by=vendor_user,
        )

        response = client.post(
            reverse(
                "portal:bo-service-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        assert not VendorService.objects.filter(pk=service_pk).exists()
        change_request.refresh_from_db()
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED

    def test_reject_leaves_vendor_service_untouched(self, client):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=vendor_user.vendor, notes="")
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=vendor_user,
            changes={"notes": {"old": "", "new": "nuova nota"}},
        )

        response = client.post(
            reverse(
                "portal:bo-service-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "reject", "review_notes": "non necessario"},
        )

        assert response.status_code == 302
        service.refresh_from_db()
        change_request.refresh_from_db()
        assert service.notes == ""
        assert change_request.status == VendorChangeRequest.STATUS_REJECTED

    def test_cannot_review_profile_only_request_from_this_endpoint(
        self, client
    ):
        _login_as_bo(client)
        vendor_user = VendorUserFactory(password=PASSWORD)
        profile_request = VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            requested_by=vendor_user,
            changes={"name": {"old": "a", "new": "b"}},
        )

        response = client.post(
            reverse(
                "portal:bo-service-request-review",
                kwargs={"pk": profile_request.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 404
        profile_request.refresh_from_db()
        assert profile_request.is_pending

    def test_vendor_user_cannot_review(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        other_vendor_user = VendorUserFactory(password=PASSWORD)
        service = VendorServiceFactory(vendor=other_vendor_user.vendor)
        change_request = VendorChangeRequest.objects.create(
            vendor=service.vendor,
            vendor_service=service,
            requested_by=other_vendor_user,
            changes={"notes": {"old": "", "new": "x"}},
        )

        response = client.post(
            reverse(
                "portal:bo-service-request-review",
                kwargs={"pk": change_request.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        change_request.refresh_from_db()
        assert change_request.is_pending
