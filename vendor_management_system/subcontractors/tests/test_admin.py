import pytest
from django.contrib import admin
from django.urls import reverse

from vendor_management_system.subcontractors.admin import (
    EquipmentInline,
    TechnicianInline,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors.admin import VendorAdmin
from vendor_management_system.vendors.models import Vendor, VendorCompany


def _inline_classes(rf, user, vendor):
    request = rf.get("/")
    request.user = user
    model_admin = VendorAdmin(Vendor, admin.site)
    return [
        type(inline)
        for inline in model_admin.get_inline_instances(request, vendor)
    ]


def _has(classes, inline):
    return any(issubclass(cls, inline) for cls in classes)


@pytest.mark.django_db
def test_sezioni_tecnici_e_mezzi_visibili_solo_ai_subappaltatori(
    rf, admin_user, vendor_factory
):
    subappaltatore = vendor_factory(vendor_type="Subappaltatore")
    altro = vendor_factory()

    assert _has(
        _inline_classes(rf, admin_user, subappaltatore), TechnicianInline
    )
    assert _has(
        _inline_classes(rf, admin_user, subappaltatore), EquipmentInline
    )
    assert not _has(_inline_classes(rf, admin_user, altro), TechnicianInline)
    assert not _has(_inline_classes(rf, admin_user, altro), EquipmentInline)


def _formset_prefixes(client, vendor, section):
    url = reverse("admin:vendors_vendor_change", args=[vendor.pk])
    response = client.get(f"{url}?sezione={section}")
    assert response.status_code == 200
    return {
        f.formset.prefix for f in response.context["inline_admin_formsets"]
    }


@pytest.mark.django_db
def test_tab_subappaltatori_solo_nella_sezione_sicura(client, vendor_factory):
    vendor = vendor_factory(vendor_type="Subappaltatore")
    VendorCompany.objects.create(vendor=vendor, company_id="SICURA")
    VendorCompany.objects.create(vendor=vendor, company_id="EVIMED")
    # Admin non superuser della società Sicura.
    user = User.objects.create_user(
        email="admin-sicura@example.invalid",
        password="x",
        role="admin",
        company_id="SICURA",
    )
    client.force_login(user)

    assert {"technicians", "equipment_items", "operational_attributes"} <= (
        _formset_prefixes(client, vendor, "SICURA")
    )
    for section in ("COMUNE", "EVIMED"):
        assert "technicians" not in _formset_prefixes(client, vendor, section)
