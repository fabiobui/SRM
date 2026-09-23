"""Test per i nuovi valori di Tipo Fornitore (AIDEV-10)."""

import pytest

from vendor_management_system.vendors.models import Vendor


@pytest.mark.django_db
@pytest.mark.parametrize(
    "vendor_type", ["Formatore", "Consulente", "Laboratorio"]
)
def test_new_vendor_type_choice_is_valid(vendor_factory, vendor_type):
    vendor = vendor_factory(vendor_type=vendor_type)

    saved_vendor = Vendor.objects.get(pk=vendor.pk)
    assert saved_vendor.vendor_type == vendor_type


@pytest.mark.django_db
def test_new_vendor_type_listed_in_choices():
    choice_values = dict(Vendor.VENDOR_TYPE_CHOICES)
    for vendor_type in ["Formatore", "Consulente", "Laboratorio"]:
        assert vendor_type in choice_values
