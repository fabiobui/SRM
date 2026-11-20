"""Chi può modificare o rivedere le sezioni del fornitore.

La sezione Comune è modificabile da tutti gli Admin, quella di una società
solo dagli Admin di quella società; il superuser modifica tutto. I BO User
rivedono Comune e propria società.
"""

import pytest

from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import (
    COMMON_SECTION,
    SCOPE_COMMON,
    SCOPE_COMPANY,
    VendorCompany,
)
from vendor_management_system.vendors.sections import (
    can_edit_section,
    can_review_section,
    default_section_for,
    resolve_section,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db


def _user(role, company=None, **extra):
    return User.objects.create_user(
        email=f"{role}-{company}-{extra}@example.invalid",
        password="x",
        role=role,
        company_id=company,
        **extra,
    )


@pytest.mark.parametrize(
    ("role", "company", "section", "expected"),
    [
        ("admin", "SICURA", COMMON_SECTION, True),
        ("admin", "SICURA", "SICURA", True),
        ("admin", "SICURA", "EVIMED", False),
        ("admin", None, COMMON_SECTION, True),
        ("admin", None, "SICURA", False),
        ("bo_user", "SICURA", "SICURA", False),
        ("buyer", "SICURA", COMMON_SECTION, False),
    ],
)
def test_can_edit_section(role, company, section, expected):
    assert can_edit_section(_user(role, company), section) is expected


def test_superuser_modifica_tutto():
    user = User.objects.create_superuser(
        email="super@example.invalid", password="x"
    )
    assert can_edit_section(user, "EVIMED")
    assert can_review_section(user, "EVIMED")


@pytest.mark.parametrize(
    ("role", "section", "expected"),
    [
        ("bo_user", COMMON_SECTION, True),
        ("bo_user", "IGEAM", True),
        ("bo_user", "SICURA", False),
        ("buyer", "IGEAM", False),
    ],
)
def test_can_review_section(role, section, expected):
    assert can_review_section(_user(role, "IGEAM"), section) is expected


def test_resolve_section_solo_per_sezioni_del_fornitore():
    vendor = VendorFactory()
    VendorCompany.objects.create(vendor=vendor, company_id="SICURA")
    assert resolve_section(vendor, "comune").code == COMMON_SECTION
    assert resolve_section(vendor, "SICURA").code == "SICURA"
    assert resolve_section(vendor, "EVIMED") is None


class TestSezioneDiDefault:
    def test_tipo_comune_va_in_comune(self):
        vendor = VendorFactory()
        VendorCompany.objects.create(vendor=vendor, company_id="SICURA")
        assert default_section_for(vendor, SCOPE_COMMON) == (
            COMMON_SECTION,
            True,
        )

    def test_unica_societa(self):
        vendor = VendorFactory()
        VendorCompany.objects.create(vendor=vendor, company_id="SICURA")
        assert default_section_for(vendor, SCOPE_COMPANY) == ("SICURA", True)

    def test_piu_societa_da_assegnare(self):
        vendor = VendorFactory()
        VendorCompany.objects.create(vendor=vendor, company_id="SICURA")
        VendorCompany.objects.create(vendor=vendor, company_id="EVIMED")
        assert default_section_for(vendor, SCOPE_COMPANY) == (
            COMMON_SECTION,
            False,
        )
