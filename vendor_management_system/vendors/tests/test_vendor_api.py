"""Test dell'API REST dei fornitori (`/api/vendors/`).

Coprono i serializer `VendorSerializer`/`VendorCreateUpdateSerializer`,
rimasti non funzionanti dopo la rimozione dai modelli dei campi
`service_type`, `service_additional` e `service_note`, e le
classificazioni aggiuntive (AIDEV-84).
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from vendor_management_system.portal.tests.factories import (
    CategoryFactory,
    ServiceTypeFactory,
)
from vendor_management_system.vendors.models import VendorService
from vendor_management_system.vendors.tests.factories import VendorFactory

User = get_user_model()


@pytest.fixture
def api():
    user = User.objects.create_user(
        email="api-user@example.invalid", password="x", role="admin"
    )
    token = Token.objects.create(user=user)
    client = APIClient()
    client.token = token.key
    return client


def _url(name, *args, token):
    return f"{reverse(name, args=args)}?token={token}"


@pytest.mark.django_db
def test_retrieve_vendor_lists_services_and_additional_categories(api):
    main = CategoryFactory()
    extra = CategoryFactory()
    vendor = VendorFactory(category=main)
    vendor.additional_categories.add(extra)
    service = ServiceTypeFactory()
    VendorService.objects.create(
        vendor=vendor, service_type=service, is_primary=True
    )

    response = api.get(
        _url("vendors--detail-vendor", vendor.vendor_code, token=api.token)
    )

    assert response.status_code == 200
    assert response.data["services"] == [
        {"id": str(service.pk), "name": service.name, "is_primary": True}
    ]
    assert [c["id"] for c in response.data["additional_categories"]] == [
        str(extra.pk)
    ]


@pytest.mark.django_db
def test_create_and_update_vendor_with_additional_categories(api):
    main = CategoryFactory()
    extra = CategoryFactory()

    response = api.post(
        _url("vendors--list-create-vendor", token=api.token),
        {
            "name": "Fornitore API",
            "category_id": str(main.pk),
            "additional_category_ids": [str(extra.pk)],
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert [c["id"] for c in response.data["additional_categories"]] == [
        str(extra.pk)
    ]

    # La classificazione principale non può essere anche aggiuntiva.
    vendor_code = response.data["vendor_code"]
    response = api.put(
        _url("vendors--detail-vendor", vendor_code, token=api.token),
        {"additional_category_ids": [str(main.pk)]},
        format="json",
    )
    assert response.status_code == 400
    assert "additional_category_ids" in response.data
