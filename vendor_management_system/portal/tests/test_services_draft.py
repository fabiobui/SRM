"""Test del flusso a bozza dei servizi (AIDEV-192).

Aggiunte, modifiche ed eliminazioni non creano subito una richiesta: restano
in una bozza in sessione e "Conferma richieste" le invia tutte insieme con lo
stesso `batch_id`. Il back-office vede l'invio come una richiesta sola e la
decisione (approva/rifiuta) vale per tutte le operazioni.
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
DRAFT_URL = "portal:my-services-draft"


def _login(client):
    user = VendorUserFactory(password=PASSWORD)
    client.login(email=user.email, password=PASSWORD)
    return user


def _leaf_service_type():
    return ServiceTypeFactory(parent=ServiceTypeFactory())


def _confirm(client):
    return client.post(reverse(DRAFT_URL), data={"action": "confirm"})


def _edit(client, service, **data):
    payload = {"is_primary": "", "start_date": "", "end_date": "", "notes": ""}
    payload.update(data)
    return client.post(
        reverse("portal:my-service-change", kwargs={"pk": service.pk}),
        data=payload,
    )


@pytest.mark.django_db
class TestAddServicesToDraft:
    def test_adding_several_services_creates_no_request_until_confirm(
        self, client
    ):
        user = _login(client)
        first, second = _leaf_service_type(), _leaf_service_type()

        response = client.post(
            reverse("portal:my-service-add"),
            data={"service_types": [str(first.pk), str(second.pk)]},
        )

        assert response.status_code == 302
        assert len(client.session["service_draft"]) == 2
        assert not VendorChangeRequest.objects.filter(
            vendor=user.vendor
        ).exists()

    def test_service_already_assigned_is_rejected(self, client):
        user = _login(client)
        assigned = VendorServiceFactory(
            vendor=user.vendor, service_type=_leaf_service_type()
        )

        response = client.post(
            reverse("portal:my-service-add"),
            data={"service_types": [str(assigned.service_type.pk)]},
        )

        assert response.status_code == 200
        assert not client.session.get("service_draft")

    def test_empty_selection_is_rejected(self, client):
        _login(client)

        response = client.post(reverse("portal:my-service-add"), data={})

        assert response.status_code == 200
        assert response.context["form"].errors["service_types"]

    def test_already_staged_service_is_not_offered_again(self, client):
        _login(client)
        leaf = _leaf_service_type()
        client.post(
            reverse("portal:my-service-add"),
            data={"service_types": [str(leaf.pk)]},
        )

        response = client.get(reverse("portal:my-service-add"))

        choices = response.context["form"].fields["service_types"].choices
        offered = [pk for _section, items in choices for pk, _label in items]
        assert str(leaf.pk) not in offered


@pytest.mark.django_db
class TestEditAndDeleteInDraft:
    def test_edit_is_staged_with_iso_dates_and_creates_no_request(
        self, client
    ):
        user = _login(client)
        service = VendorServiceFactory(vendor=user.vendor, start_date=None)

        response = _edit(client, service, start_date="2026-03-01")

        assert response.status_code == 302
        (entry,) = client.session["service_draft"]
        assert entry["changes"] == {
            "start_date": {"old": None, "new": "2026-03-01"}
        }
        assert not VendorChangeRequest.objects.filter(
            vendor=user.vendor
        ).exists()

    def test_hourly_rate_and_contract_are_never_accepted(self, client):
        user = _login(client)
        service = VendorServiceFactory(vendor=user.vendor, hourly_rate="10.00")

        _edit(
            client, service, is_primary="on", hourly_rate="9999", contract="1"
        )

        (entry,) = client.session["service_draft"]
        assert set(entry["changes"]) == {"is_primary"}

    def test_cannot_stage_changes_on_another_vendor_service(self, client):
        _login(client)
        other = VendorServiceFactory()

        assert _edit(client, other, notes="x").status_code == 404
        response = client.post(
            reverse("portal:my-service-delete", kwargs={"pk": other.pk})
        )
        assert response.status_code == 404

    def test_delete_is_post_only_and_staged(self, client):
        user = _login(client)
        service = VendorServiceFactory(vendor=user.vendor)
        url = reverse("portal:my-service-delete", kwargs={"pk": service.pk})

        assert client.get(url).status_code == 405
        assert client.post(url).status_code == 302
        assert client.session["service_draft"][0]["op"] == "delete"

    def test_service_with_pending_request_cannot_be_staged(self, client):
        user = _login(client)
        service = VendorServiceFactory(vendor=user.vendor)
        VendorChangeRequest.objects.create(
            vendor=user.vendor,
            vendor_service=service,
            changes={"notes": {"old": "", "new": "x"}},
        )

        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk})
        )
        _edit(client, service, notes="y")

        assert not client.session.get("service_draft")

    def test_last_choice_on_a_service_replaces_the_previous_one(self, client):
        user = _login(client)
        service = VendorServiceFactory(vendor=user.vendor)
        _edit(client, service, notes="nuova nota")

        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk})
        )

        assert [e["op"] for e in client.session["service_draft"]] == ["delete"]


@pytest.mark.django_db
class TestConfirmDraft:
    def test_confirm_sends_all_operations_with_one_batch_id(self, client):
        user = _login(client)
        to_edit = VendorServiceFactory(vendor=user.vendor, is_primary=False)
        to_delete = VendorServiceFactory(vendor=user.vendor)
        new_type = _leaf_service_type()
        _edit(client, to_edit, is_primary="on")
        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": to_delete.pk})
        )
        client.post(
            reverse("portal:my-service-add"),
            data={"service_types": [str(new_type.pk)]},
        )

        response = _confirm(client)

        assert response.status_code == 302
        requests = list(VendorChangeRequest.objects.filter(vendor=user.vendor))
        assert {r.request_type for r in requests} == {
            VendorChangeRequest.REQUEST_TYPE_EDIT,
            VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE,
            VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
        }
        assert len({r.batch_id for r in requests}) == 1
        assert requests[0].batch_id is not None
        assert not client.session.get("service_draft")

    def test_confirm_skips_service_that_got_a_pending_request_meanwhile(
        self, client
    ):
        user = _login(client)
        service = VendorServiceFactory(vendor=user.vendor)
        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk})
        )
        VendorChangeRequest.objects.create(
            vendor=user.vendor,
            vendor_service=service,
            changes={"notes": {"old": "", "new": "x"}},
        )

        _confirm(client)

        assert (
            VendorChangeRequest.objects.filter(vendor=user.vendor).count() == 1
        )

    def test_remove_and_clear_empty_the_draft(self, client):
        user = _login(client)
        first = VendorServiceFactory(vendor=user.vendor)
        second = VendorServiceFactory(vendor=user.vendor)
        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": first.pk})
        )
        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": second.pk})
        )

        client.post(
            reverse(DRAFT_URL), data={"action": "remove", "index": "0"}
        )
        assert len(client.session["service_draft"]) == 1

        client.post(reverse(DRAFT_URL), data={"action": "clear"})
        assert not client.session.get("service_draft")

    def test_list_shows_draft_preview_and_confirm_button(self, client):
        user = _login(client)
        service = VendorServiceFactory(vendor=user.vendor)
        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk})
        )

        content = client.get(reverse("portal:my-services")).content.decode()

        assert "Richieste da confermare" in content
        assert "Conferma richieste" in content
        assert service.service_type.name in content


def _login_as_bo(client):
    bo_user = User.objects.create_user(
        email="bo-batch@example.invalid", password=PASSWORD, role="bo_user"
    )
    client.login(email=bo_user.email, password=PASSWORD)


def _make_batch(client):
    """Fornitore con modifica + eliminazione + aggiunta confermate insieme."""
    user = _login(client)
    to_edit = VendorServiceFactory(vendor=user.vendor, is_primary=False)
    to_delete = VendorServiceFactory(vendor=user.vendor)
    new_type = _leaf_service_type()
    _edit(client, to_edit, is_primary="on")
    client.post(
        reverse("portal:my-service-delete", kwargs={"pk": to_delete.pk})
    )
    client.post(
        reverse("portal:my-service-add"),
        data={"service_types": [str(new_type.pk)]},
    )
    _confirm(client)
    client.logout()
    return user, to_edit, to_delete, new_type


@pytest.mark.django_db
class TestBoGroupedReview:
    def test_batch_is_one_row_in_the_list(self, client):
        _make_batch(client)
        _login_as_bo(client)

        response = client.get(reverse("portal:bo-service-requests"))

        assert len(response.context["requests"]) == 1
        assert response.context["requests"][0].batch_count == 3
        assert "Richiesta multipla" in response.content.decode()

    def test_detail_lists_every_operation_of_the_batch(self, client):
        _make_batch(client)
        _login_as_bo(client)
        representative = client.get(
            reverse("portal:bo-service-requests")
        ).context["requests"][0]

        response = client.get(
            reverse(
                "portal:bo-service-request-detail",
                kwargs={"pk": representative.pk},
            )
        )

        assert len(response.context["group_requests"]) == 3

    def test_approving_applies_all_operations(self, client):
        user, to_edit, to_delete, new_type = _make_batch(client)
        _login_as_bo(client)
        representative = VendorChangeRequest.objects.filter(
            vendor=user.vendor
        ).first()

        client.post(
            reverse(
                "portal:bo-service-request-review",
                kwargs={"pk": representative.pk},
            ),
            data={"action": "approve"},
        )

        to_edit.refresh_from_db()
        assert to_edit.is_primary is True
        assert not VendorService.objects.filter(pk=to_delete.pk).exists()
        assert VendorService.objects.filter(
            vendor=user.vendor, service_type=new_type
        ).exists()
        assert all(
            r.status == VendorChangeRequest.STATUS_APPROVED
            for r in VendorChangeRequest.objects.filter(vendor=user.vendor)
        )

    def test_rejecting_rejects_all_and_changes_nothing(self, client):
        user, to_edit, to_delete, _new_type = _make_batch(client)
        _login_as_bo(client)
        representative = VendorChangeRequest.objects.filter(
            vendor=user.vendor
        ).first()

        client.post(
            reverse(
                "portal:bo-service-request-review",
                kwargs={"pk": representative.pk},
            ),
            data={"action": "reject"},
        )

        to_edit.refresh_from_db()
        assert to_edit.is_primary is False
        assert VendorService.objects.filter(pk=to_delete.pk).exists()
        assert all(
            r.status == VendorChangeRequest.STATUS_REJECTED
            for r in VendorChangeRequest.objects.filter(vendor=user.vendor)
        )
