"""Test del flusso "Servizi fornitori" del portale.

I `VendorService` sono pre-assegnati dal back-office. Il fornitore può solo
proporre modifiche ai campi descrittivi (`is_primary`, `start_date`,
`end_date`, `notes`): prezzo orario (`hourly_rate`) e contratto collegato
restano di sola competenza back-office, anche se iniettati nel payload POST
(il `ModelForm` li ignora perché non dichiarati in `Meta.fields`).
"""

import pytest
from django.urls import reverse

from vendor_management_system.portal.models import VendorChangeRequest
from vendor_management_system.portal.tests.factories import (
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
