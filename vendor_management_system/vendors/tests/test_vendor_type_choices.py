"""Formatore, Consulente e Laboratorio non sono più Tipi Fornitore ma
Classificazioni (AIDEV-118; erano stati introdotti in AIDEV-10)."""

import pytest

from vendor_management_system.vendors.models import Vendor


@pytest.mark.parametrize(
    "vendor_type", ["Formatore", "Consulente", "Laboratorio"]
)
def test_removed_vendor_type_not_in_choices(vendor_type):
    assert vendor_type not in dict(Vendor.VENDOR_TYPE_CHOICES)


@pytest.mark.django_db
def test_existing_vendor_type_still_valid(vendor_factory):
    vendor = vendor_factory(vendor_type="Società")

    assert Vendor.objects.get(pk=vendor.pk).vendor_type == "Società"
