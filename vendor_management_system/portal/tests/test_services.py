"""Test del flusso "Servizi fornitori" del portale.

I `VendorService` sono pre-assegnati dal back-office, oppure creati
all'approvazione di una richiesta ADD_SERVICE del fornitore (vedi
`TestVendorServiceAddRequestCreateView` e
`test_backoffice_change_requests.py`). Il fornitore può proporre modifiche
ai campi descrittivi (`is_primary`, `start_date`, `end_date`, `notes`),
richiedere l'aggiunta di un nuovo servizio dal catalogo o l'eliminazione di
uno esistente: prezzo orario (`hourly_rate`) e contratto collegato restano
di sola competenza back-office, anche se iniettati nel payload POST (il
`ModelForm` li ignora perché non dichiarati in `Meta.fields`).
"""

import pytest
from django.urls import reverse

from vendor_management_system.portal.forms import (
    available_service_types_for_vendor,
)
from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import (
    CategoryFactory,
    ServiceSetFactory,
    ServiceTypeFactory,
    VendorServiceFactory,
    VendorUserFactory,
)

PASSWORD = "test-pass-1234"


@pytest.mark.django_db
class TestMyServicesView:
    def test_list_only_shows_own_vendor_services(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        own_service = VendorServiceFactory(vendor=user.vendor)
        VendorServiceFactory()  # servizio di un altro vendor

        response = client.get(reverse("portal:my-services"))

        services = list(response.context["services"])
        assert services == [own_service]


@pytest.mark.django_db
class TestVendorServiceChangeRequestCreateView:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_proposing_descriptive_change_creates_pending_request(
        self, client
    ):
        user = self._login(client)
        service = VendorServiceFactory(vendor=user.vendor, is_primary=False)

        response = client.post(
            reverse("portal:my-service-change", kwargs={"pk": service.pk}),
            data={
                "is_primary": "on",
                "start_date": "",
                "end_date": "",
                "notes": "",
            },
        )

        assert response.status_code == 302
        change_request = VendorChangeRequest.objects.get(
            vendor_service=service
        )
        assert change_request.is_pending
        assert change_request.vendor == service.vendor
        assert change_request.changes["is_primary"]["new"] is True

    def test_hourly_rate_and_contract_are_never_accepted(self, client):
        user = self._login(client)
        service = VendorServiceFactory(vendor=user.vendor, hourly_rate="10.00")

        client.post(
            reverse("portal:my-service-change", kwargs={"pk": service.pk}),
            data={
                "is_primary": "on",
                "start_date": "",
                "end_date": "",
                "notes": "",
                "hourly_rate": "9999.00",
                "contract": "1",
            },
        )

        change_request = VendorChangeRequest.objects.get(
            vendor_service=service
        )
        assert "hourly_rate" not in change_request.changes
        assert "contract" not in change_request.changes
        service.refresh_from_db()
        assert str(service.hourly_rate) == "10.00"

    def test_second_pending_request_on_same_service_is_blocked(self, client):
        user = self._login(client)
        service = VendorServiceFactory(vendor=user.vendor)
        payload = {
            "is_primary": "",
            "start_date": "",
            "end_date": "",
            "notes": "prima proposta",
        }
        client.post(
            reverse("portal:my-service-change", kwargs={"pk": service.pk}),
            data=payload,
        )

        response = client.post(
            reverse("portal:my-service-change", kwargs={"pk": service.pk}),
            data={**payload, "notes": "seconda proposta"},
        )

        assert response.status_code == 302
        assert (
            VendorChangeRequest.objects.filter(vendor_service=service).count()
            == 1
        )

    def test_pending_request_on_one_service_does_not_block_another(
        self, client
    ):
        user = self._login(client)
        service_a = VendorServiceFactory(vendor=user.vendor)
        service_b = VendorServiceFactory(vendor=user.vendor)
        client.post(
            reverse("portal:my-service-change", kwargs={"pk": service_a.pk}),
            data={
                "is_primary": "",
                "start_date": "",
                "end_date": "",
                "notes": "modifica A",
            },
        )

        response = client.post(
            reverse("portal:my-service-change", kwargs={"pk": service_b.pk}),
            data={
                "is_primary": "",
                "start_date": "",
                "end_date": "",
                "notes": "modifica B",
            },
        )

        assert response.status_code == 302
        assert VendorChangeRequest.objects.filter(
            vendor_service=service_b
        ).exists()

    def test_cannot_propose_change_on_another_vendor_service(self, client):
        self._login(client)
        other_service = VendorServiceFactory()

        response = client.post(
            reverse(
                "portal:my-service-change", kwargs={"pk": other_service.pk}
            ),
            data={
                "is_primary": "",
                "start_date": "",
                "end_date": "",
                "notes": "",
            },
        )

        assert response.status_code == 404
        assert not VendorChangeRequest.objects.filter(
            vendor_service=other_service
        ).exists()


def _leaf_service_type():
    """Un servizio specifico proponibile (parent valorizzato): le
    "categorie" (parent=None) non sono mai proponibili, vedi
    `available_service_types_for_vendor`."""
    section = ServiceTypeFactory()
    return ServiceTypeFactory(parent=section)


@pytest.mark.django_db
class TestAvailableServiceTypesForVendor:
    def test_categories_are_never_included(self):
        vendor = VendorUserFactory(password=PASSWORD).vendor
        category_only = ServiceTypeFactory()  # parent=None

        available = available_service_types_for_vendor(vendor)

        assert category_only not in available

    def test_no_category_returns_full_active_catalog(self):
        vendor = VendorUserFactory(password=PASSWORD).vendor
        leaf = _leaf_service_type()

        available = available_service_types_for_vendor(vendor)

        assert leaf in available

    def test_already_assigned_service_is_excluded(self):
        vendor = VendorUserFactory(password=PASSWORD).vendor
        leaf = _leaf_service_type()
        VendorServiceFactory(vendor=vendor, service_type=leaf)

        available = available_service_types_for_vendor(vendor)

        assert leaf not in available

    def test_pending_add_request_excludes_service_from_dropdown(self):
        vendor_user = VendorUserFactory(password=PASSWORD)
        leaf = _leaf_service_type()
        VendorChangeRequest.objects.create(
            vendor=vendor_user.vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
            service_type=leaf,
            requested_by=vendor_user,
        )

        available = available_service_types_for_vendor(vendor_user.vendor)

        assert leaf not in available

    def test_category_with_linked_service_set_filters_dropdown(self):
        category = CategoryFactory()
        vendor = VendorUserFactory(password=PASSWORD).vendor
        vendor.category = category
        vendor.save()
        section = ServiceTypeFactory()
        in_set = ServiceTypeFactory(parent=section)
        out_of_set = ServiceTypeFactory(parent=section)
        service_set = ServiceSetFactory(category=category)
        service_set.service_types.add(in_set)

        available = available_service_types_for_vendor(vendor)

        assert in_set in available
        assert out_of_set not in available

    def test_category_scope_includes_ancestor_service_set(self):
        parent_category = CategoryFactory()
        child_category = CategoryFactory(parent=parent_category)
        vendor = VendorUserFactory(password=PASSWORD).vendor
        vendor.category = child_category
        vendor.save()
        in_set = _leaf_service_type()
        service_set = ServiceSetFactory(category=parent_category)
        service_set.service_types.add(in_set)

        available = available_service_types_for_vendor(vendor)

        assert in_set in available

    def test_category_without_linked_service_set_falls_back_to_catalog(self):
        category = CategoryFactory()
        vendor = VendorUserFactory(password=PASSWORD).vendor
        vendor.category = category
        vendor.save()
        leaf = _leaf_service_type()

        available = available_service_types_for_vendor(vendor)

        assert leaf in available


@pytest.mark.django_db
class TestVendorServiceAddRequestCreateView:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_get_renders_form_with_available_service_types(self, client):
        self._login(client)
        leaf = _leaf_service_type()

        response = client.get(reverse("portal:my-service-add"))

        assert response.status_code == 200
        choices = response.context["form"].fields["service_type"].choices
        flattened = [pk for _section, items in choices for pk, _label in items]
        assert str(leaf.pk) in flattened

    def test_post_valid_creates_pending_add_request(self, client):
        user = self._login(client)
        leaf = _leaf_service_type()

        response = client.post(
            reverse("portal:my-service-add"),
            data={
                "service_type": str(leaf.pk),
                "is_primary": "on",
                "start_date": "",
                "end_date": "",
                "notes": "richiesta test",
            },
        )

        assert response.status_code == 302
        change_request = VendorChangeRequest.objects.get(
            vendor=user.vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
        )
        assert change_request.is_pending
        assert change_request.service_type == leaf
        assert change_request.changes["is_primary"]["new"] is True
        assert change_request.changes["notes"]["new"] == "richiesta test"

    def test_cannot_request_already_assigned_service(self, client):
        user = self._login(client)
        leaf = _leaf_service_type()
        VendorServiceFactory(vendor=user.vendor, service_type=leaf)

        response = client.post(
            reverse("portal:my-service-add"),
            data={
                "service_type": str(leaf.pk),
                "is_primary": "",
                "start_date": "",
                "end_date": "",
                "notes": "",
            },
        )

        assert response.status_code == 200
        assert not VendorChangeRequest.objects.filter(
            vendor=user.vendor,
            request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
        ).exists()

    def test_duplicate_pending_add_request_is_blocked(self, client):
        user = self._login(client)
        leaf = _leaf_service_type()
        payload = {
            "service_type": str(leaf.pk),
            "is_primary": "",
            "start_date": "",
            "end_date": "",
            "notes": "prima",
        }
        client.post(reverse("portal:my-service-add"), data=payload)

        response = client.post(
            reverse("portal:my-service-add"),
            data={**payload, "notes": "seconda"},
        )

        assert response.status_code == 200
        assert (
            VendorChangeRequest.objects.filter(
                vendor=user.vendor,
                request_type=VendorChangeRequest.REQUEST_TYPE_ADD_SERVICE,
            ).count()
            == 1
        )

    def test_tampered_service_type_out_of_scope_is_rejected(self, client):
        user = self._login(client)
        category = CategoryFactory()
        user.vendor.category = category
        user.vendor.save()
        section = ServiceTypeFactory()
        in_scope = ServiceTypeFactory(parent=section)
        out_of_scope = ServiceTypeFactory(parent=section)
        service_set = ServiceSetFactory(category=category)
        service_set.service_types.add(in_scope)

        response = client.post(
            reverse("portal:my-service-add"),
            data={
                "service_type": str(out_of_scope.pk),
                "is_primary": "",
                "start_date": "",
                "end_date": "",
                "notes": "",
            },
        )

        assert response.status_code == 200
        assert not VendorChangeRequest.objects.filter(
            vendor=user.vendor, service_type=out_of_scope
        ).exists()


@pytest.mark.django_db
class TestVendorServiceDeleteRequestCreateView:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_get_renders_confirm_page(self, client):
        user = self._login(client)
        service = VendorServiceFactory(vendor=user.vendor)

        response = client.get(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk})
        )

        assert response.status_code == 200
        assert response.context["service"] == service

    def test_post_creates_pending_delete_request(self, client):
        user = self._login(client)
        service = VendorServiceFactory(vendor=user.vendor)

        response = client.post(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk}),
            data={"reason": "non più erogato"},
        )

        assert response.status_code == 302
        change_request = VendorChangeRequest.objects.get(
            vendor_service=service
        )
        assert change_request.is_pending
        assert (
            change_request.request_type
            == VendorChangeRequest.REQUEST_TYPE_DELETE_SERVICE
        )
        assert change_request.changes["motivo"]["new"] == "non più erogato"

    def test_second_pending_delete_request_is_blocked(self, client):
        user = self._login(client)
        service = VendorServiceFactory(vendor=user.vendor)
        client.post(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk}),
            data={"reason": ""},
        )

        response = client.post(
            reverse("portal:my-service-delete", kwargs={"pk": service.pk}),
            data={"reason": ""},
        )

        assert response.status_code == 302
        assert (
            VendorChangeRequest.objects.filter(vendor_service=service).count()
            == 1
        )

    def test_cannot_request_deletion_of_another_vendor_service(self, client):
        self._login(client)
        other_service = VendorServiceFactory()

        response = client.post(
            reverse(
                "portal:my-service-delete", kwargs={"pk": other_service.pk}
            ),
            data={"reason": ""},
        )

        assert response.status_code == 404
        assert not VendorChangeRequest.objects.filter(
            vendor_service=other_service
        ).exists()
