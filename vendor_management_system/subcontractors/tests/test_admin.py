import pytest
from django.contrib import admin

from vendor_management_system.subcontractors.admin import (
    EquipmentInline,
    TechnicianInline,
)
from vendor_management_system.vendors.admin import VendorAdmin
from vendor_management_system.vendors.models import Vendor


def _inline_classes(rf, user, vendor):
    request = rf.get("/")
    request.user = user
    model_admin = VendorAdmin(Vendor, admin.site)
    return [
        type(inline)
        for inline in model_admin.get_inline_instances(request, vendor)
    ]


@pytest.mark.django_db
def test_sezioni_tecnici_e_mezzi_visibili_solo_ai_subappaltatori(
    rf, admin_user, vendor_factory
):
    subappaltatore = vendor_factory(vendor_type="Subappaltatore")
    altro = vendor_factory()

    assert TechnicianInline in _inline_classes(rf, admin_user, subappaltatore)
    assert EquipmentInline in _inline_classes(rf, admin_user, subappaltatore)
    assert TechnicianInline not in _inline_classes(rf, admin_user, altro)
    assert EquipmentInline not in _inline_classes(rf, admin_user, altro)
