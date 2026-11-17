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

    def test_list_shows_service_description_not_rate_or_contract(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        service_type = ServiceTypeFactory(description="Pulizia ordinaria")
        VendorServiceFactory(
            vendor=user.vendor, service_type=service_type, hourly_rate="10.00"
        )

        content = client.get(reverse("portal:my-services")).content.decode()

        assert "Pulizia ordinaria" in content
        assert "Prezzo orario" not in content
        assert "gestito dal back-office" not in content


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

    def test_additional_category_service_set_is_included(self):
        main_category = CategoryFactory()
        extra_category = CategoryFactory()
        vendor = VendorUserFactory(password=PASSWORD).vendor
        vendor.category = main_category
        vendor.save()
        vendor.additional_categories.add(extra_category)
        section = ServiceTypeFactory()
        main_service = ServiceTypeFactory(parent=section)
        extra_service = ServiceTypeFactory(parent=section)
        out_of_set = ServiceTypeFactory(parent=section)
        ServiceSetFactory(category=main_category).service_types.add(
            main_service
        )
        ServiceSetFactory(category=extra_category).service_types.add(
            extra_service
        )

        available = available_service_types_for_vendor(vendor)

        assert main_service in available
        assert extra_service in available
        assert out_of_set not in available

    def test_category_without_linked_service_set_falls_back_to_catalog(self):
        category = CategoryFactory()
        vendor = VendorUserFactory(password=PASSWORD).vendor
        vendor.category = category
        vendor.save()
        leaf = _leaf_service_type()

        available = available_service_types_for_vendor(vendor)

        assert leaf in available
