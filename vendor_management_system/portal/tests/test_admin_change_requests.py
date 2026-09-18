"""Test dell'admin Django per `VendorChangeRequest`
(`/admin/portal/vendorchangerequest/`, registrato ma nascosto dal menu —
vedi JAZZMIN_SETTINGS["hide_models"] in config/settings.py), distinto
dalla vista BO del portale (`portal:bo-change-request-review`, coperta in
`test_backoffice_change_requests.py`).

Copre:
- `changes_pretty()`: deve produrre HTML reale (non escapato).
- `save_model()`: cambiare Stato in Approvata/Respinta da qui deve
  applicare/rifiutare la richiesta esattamente come la vista BO del
  portale (altrimenti l'anagrafica del Vendor non si aggiorna mai).
- il filtro per `vendor__managed_by` (utente gestione fornitore).
"""

from types import SimpleNamespace

import pytest
from django.contrib import admin as admin_site
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse

from vendor_management_system.portal.admin import VendorChangeRequestAdmin
from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import VendorUserFactory

User = get_user_model()
PASSWORD = "test-pass-1234"


@pytest.fixture
def admin_instance():
    return VendorChangeRequestAdmin(VendorChangeRequest, admin_site.site)


@pytest.mark.django_db
class TestChangesPrettyFormatting:
    def test_renders_real_html_table_not_escaped(self, admin_instance):
        change_request = VendorChangeRequest(
            changes={"reference_person": {"old": None, "new": "Sofia Frau"}}
        )

        result = str(admin_instance.changes_pretty(change_request))

        assert "<table" in result
        assert "&lt;table" not in result
        assert "<td><strong>Sofia Frau</strong></td>" in result

    def test_empty_changes_shows_dash(self, admin_instance):
        change_request = VendorChangeRequest(changes={})
        assert admin_instance.changes_pretty(change_request) == "—"


@pytest.mark.django_db
class TestSaveModelAutoApply:
    def _make_request(self, user):
        request = RequestFactory().post(
            "/admin/portal/vendorchangerequest/x/change/"
        )
        request.user = user
        return request

    def test_approving_via_admin_updates_vendor(self, admin_instance):
        bo_user = User.objects.create_user(
            email="bo-admin@example.invalid", password=PASSWORD, role="bo_user"
        )
        vendor_user = VendorUserFactory(password=PASSWORD)
        vendor = vendor_user.vendor
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=vendor_user,
            changes={"name": {"old": vendor.name, "new": "Nuovo Nome SRL"}},
        )
        change_request.status = VendorChangeRequest.STATUS_APPROVED
        change_request.review_notes = "ok da admin"
        form = SimpleNamespace(
            initial={"status": VendorChangeRequest.STATUS_PENDING}
        )

        admin_instance.save_model(
            self._make_request(bo_user), change_request, form, change=True
        )

        vendor.refresh_from_db()
        change_request.refresh_from_db()
        assert vendor.name == "Nuovo Nome SRL"
        assert change_request.status == VendorChangeRequest.STATUS_APPROVED
        assert change_request.reviewed_by.email == bo_user.email
        assert change_request.reviewed_at is not None

    def test_rejecting_via_admin_does_not_apply_diff(self, admin_instance):
        bo_user = User.objects.create_user(
            email="bo-admin-2@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        vendor_user = VendorUserFactory(password=PASSWORD)
        vendor = vendor_user.vendor
        original_name = vendor.name
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=vendor_user,
            changes={"name": {"old": original_name, "new": "Scartato"}},
        )
        change_request.status = VendorChangeRequest.STATUS_REJECTED
        form = SimpleNamespace(
            initial={"status": VendorChangeRequest.STATUS_PENDING}
        )

        admin_instance.save_model(
            self._make_request(bo_user), change_request, form, change=True
        )

        vendor.refresh_from_db()
        change_request.refresh_from_db()
        assert vendor.name == original_name
        assert change_request.status == VendorChangeRequest.STATUS_REJECTED

    def test_saving_without_status_change_does_not_touch_vendor(
        self, admin_instance
    ):
        bo_user = User.objects.create_user(
            email="bo-admin-3@example.invalid",
            password=PASSWORD,
            role="bo_user",
        )
        vendor_user = VendorUserFactory(password=PASSWORD)
        vendor = vendor_user.vendor
        change_request = VendorChangeRequest.objects.create(
            vendor=vendor,
            requested_by=vendor_user,
            changes={"name": {"old": vendor.name, "new": "Non applicato"}},
        )
        # Stato resta PENDING: solo le note di revisione cambiano.
        change_request.review_notes = "nota preliminare"
        form = SimpleNamespace(
            initial={"status": VendorChangeRequest.STATUS_PENDING}
        )

        admin_instance.save_model(
            self._make_request(bo_user), change_request, form, change=True
        )

        vendor.refresh_from_db()
        change_request.refresh_from_db()
        assert vendor.name != "Non applicato"
        assert change_request.status == VendorChangeRequest.STATUS_PENDING
        assert change_request.review_notes == "nota preliminare"


@pytest.mark.django_db
class TestManagedByFilter:
    def test_list_filter_includes_managed_by(self):
        assert "vendor__managed_by" in VendorChangeRequestAdmin.list_filter

    def test_changelist_filters_by_managed_by(self, client):
        superuser = User.objects.create_superuser(
            email="super@example.invalid", password=PASSWORD, role="admin"
        )
        client.login(email=superuser.email, password=PASSWORD)

        bo_user_a = User.objects.create_user(
            email="bo-a@example.invalid", password=PASSWORD, role="bo_user"
        )
        bo_user_b = User.objects.create_user(
            email="bo-b@example.invalid", password=PASSWORD, role="bo_user"
        )
        vendor_user_a = VendorUserFactory(password=PASSWORD)
        vendor_user_a.vendor.managed_by = bo_user_a
        vendor_user_a.vendor.save()
        vendor_user_b = VendorUserFactory(password=PASSWORD)
        vendor_user_b.vendor.managed_by = bo_user_b
        vendor_user_b.vendor.save()
        request_a = VendorChangeRequest.objects.create(
            vendor=vendor_user_a.vendor,
            requested_by=vendor_user_a,
            changes={"name": {"old": "x", "new": "y"}},
        )
        request_b = VendorChangeRequest.objects.create(
            vendor=vendor_user_b.vendor,
            requested_by=vendor_user_b,
            changes={"name": {"old": "x", "new": "y"}},
        )

        url = reverse("admin:portal_vendorchangerequest_changelist")
        response = client.get(
            url, {"vendor__managed_by__id__exact": bo_user_a.pk}
        )

        assert response.status_code == 200
        results = list(response.context["cl"].result_list)
        assert request_a in results
        assert request_b not in results
