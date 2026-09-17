"""Test dei mixin di permesso del portale fornitore.

Copre `VendorRequiredMixin`/`BackOfficeRequiredMixin` (chi può accedere alle
varie aree) e la protezione IDOR sui singoli oggetti (un fornitore non deve
poter leggere/modificare documenti, requisiti o servizi di un altro
fornitore cambiando il pk nell'URL).
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.portal.tests.factories import (
    DocumentFactory,
    VendorCompetenceFactory,
    VendorServiceFactory,
    VendorUserFactory,
)

User = get_user_model()
PASSWORD = "test-pass-1234"


@pytest.mark.django_db
class TestVendorRequiredMixin:
    def test_anonymous_is_redirected(self, client):
        response = client.get(reverse("portal:dashboard"))
        assert response.status_code == 302

    def test_non_vendor_user_is_redirected(self, client):
        user = User.objects.create_user(
            email="bo-user@example.invalid", password=PASSWORD, role="bo_user"
        )
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:dashboard"))
        assert response.status_code == 302

    def test_vendor_user_can_access_dashboard(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:dashboard"))
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "url_name",
        [
            "my-documents",
            "my-requirements",
            "my-services",
            "my-profile",
            "my-operational-attributes",
            "my-qualification",
            "my-change-requests",
        ],
    )
    def test_portal_pages_require_authentication(self, client, url_name):
        response = client.get(reverse(f"portal:{url_name}"))
        assert response.status_code == 302

    @pytest.mark.parametrize(
        "url_name",
        [
            "my-documents",
            "my-requirements",
            "my-services",
            "my-profile",
            "my-operational-attributes",
            "my-qualification",
            "my-change-requests",
        ],
    )
    def test_portal_pages_accessible_by_vendor(self, client, url_name):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse(f"portal:{url_name}"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestBackOfficeRequiredMixin:
    def test_vendor_user_cannot_access_bo_area(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:bo-change-requests"))
        assert response.status_code == 302

    def test_bo_user_can_access_bo_area(self, client):
        user = User.objects.create_user(
            email="bo-user-2@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:bo-change-requests"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestIDOR:
    """Un fornitore autenticato non deve poter toccare oggetti di un altro
    fornitore cambiando il pk nell'URL, anche quando la route non usa
    esplicitamente `VendorOwnerRequiredMixin` (le view filtrano il queryset
    su `vendor=request.user.vendor`, vedi `portal/views.py`)."""

    def _login_as_vendor(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_cannot_view_another_vendor_document(self, client):
        self._login_as_vendor(client)
        other_document = DocumentFactory()
        response = client.get(
            reverse(
                "portal:my-document-detail", kwargs={"pk": other_document.pk}
            )
        )
        assert response.status_code == 404

    def test_cannot_upload_to_another_vendor_document(self, client):
        self._login_as_vendor(client)
        other_document = DocumentFactory()
        response = client.post(
            reverse(
                "portal:my-document-upload", kwargs={"pk": other_document.pk}
            ),
            data={},
        )
        assert response.status_code == 404

    def test_cannot_view_another_vendor_requirement(self, client):
        self._login_as_vendor(client)
        other_requirement = VendorCompetenceFactory()
        response = client.get(
            reverse(
                "portal:my-requirement-detail",
                kwargs={"pk": other_requirement.pk},
            )
        )
        assert response.status_code == 404

    def test_cannot_upload_to_another_vendor_requirement(self, client):
        self._login_as_vendor(client)
        other_requirement = VendorCompetenceFactory()
        response = client.post(
            reverse(
                "portal:my-requirement-upload",
                kwargs={"pk": other_requirement.pk},
            ),
            data={},
        )
        assert response.status_code == 404

    def test_cannot_propose_change_on_another_vendor_service(self, client):
        self._login_as_vendor(client)
        other_service = VendorServiceFactory()
        response = client.get(
            reverse(
                "portal:my-service-change", kwargs={"pk": other_service.pk}
            )
        )
        assert response.status_code == 404
