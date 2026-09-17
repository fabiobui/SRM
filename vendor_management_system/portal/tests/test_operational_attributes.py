"""Test del flusso "Attributi operativi" del portale fornitore.

A differenza di anagrafica e servizi, qui non c'è approvazione back-office:
il fornitore scrive direttamente su `VendorOperationalAttributes` (get-or-
create sul record OneToOne, che può non esistere ancora al primo accesso).
"""

import pytest
from django.urls import reverse

from vendor_management_system.portal.tests.factories import VendorUserFactory
from vendor_management_system.vendors.models import VendorOperationalAttributes

PASSWORD = "test-pass-1234"


@pytest.mark.django_db
class TestMyOperationalAttributesView:
    def _login(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        return user

    def test_get_creates_record_when_missing(self, client):
        user = self._login(client)
        assert not VendorOperationalAttributes.objects.filter(
            vendor=user.vendor
        ).exists()

        response = client.get(reverse("portal:my-operational-attributes"))

        assert response.status_code == 200
        assert VendorOperationalAttributes.objects.filter(
            vendor=user.vendor
        ).exists()

    def test_post_saves_directly_without_approval(self, client):
        user = self._login(client)

        response = client.post(
            reverse("portal:my-operational-attributes"),
            data={
                "total_operators": 12,
                "equipped_vans": "on",
                "aerial_platforms": "on",
                "aerial_platforms_notes": "Piattaforma 12m",
                "autonomy_category": 3,
                "experience_logistics": "on",
                "mileage_reimbursement": "on",
                "mileage_reimbursement_value": "0.35",
            },
        )

        assert response.status_code == 302
        attributes = VendorOperationalAttributes.objects.get(
            vendor=user.vendor
        )
        assert attributes.total_operators == 12
        assert attributes.equipped_vans is True
        assert attributes.aerial_platforms is True
        assert attributes.aerial_platforms_notes == "Piattaforma 12m"
        assert attributes.autonomy_category == 3
        assert attributes.experience_logistics is True
        # Un campo booleano non inviato nel POST (checkbox non selezionata)
        # deve tornare a False, non restare com'era prima.
        assert attributes.experience_data_center is False

    def test_each_vendor_gets_its_own_record(self, client):
        user_a = self._login(client)
        client.post(
            reverse("portal:my-operational-attributes"),
            data={"total_operators": 5},
        )

        client_b_user = VendorUserFactory(password=PASSWORD)
        from django.test import Client

        client_b = Client()
        client_b.login(email=client_b_user.email, password=PASSWORD)
        client_b.post(
            reverse("portal:my-operational-attributes"),
            data={"total_operators": 99},
        )

        attrs_a = VendorOperationalAttributes.objects.get(vendor=user_a.vendor)
        attrs_b = VendorOperationalAttributes.objects.get(
            vendor=client_b_user.vendor
        )
        assert attrs_a.total_operators == 5
        assert attrs_b.total_operators == 99
        assert attrs_a.pk != attrs_b.pk
