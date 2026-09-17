# Imports
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError


# Test that the primary key is a string UUID, not an auto-incrementing integer
@pytest.mark.django_db
def test_operational_attributes_id_is_uuid_string(
    db, vendor_operational_attributes_factory
):
    attributes = vendor_operational_attributes_factory()

    assert isinstance(attributes.pk, str)
    uuid.UUID(attributes.pk)  # solleva ValueError se non è un UUID valido


# Test the VendorOperationalAttributes object creation and defaults
@pytest.mark.django_db
def test_operational_attributes_defaults(
    db, vendor_operational_attributes_factory
):
    attributes = vendor_operational_attributes_factory()

    # Campi opzionali: nessun valore di default
    assert attributes.total_operators is None
    assert attributes.standard_hourly_labor_cost is None
    assert attributes.travel_cost is None
    assert attributes.mileage_reimbursement_value is None
    assert attributes.autonomy_category is None
    assert attributes.aerial_platforms_notes is None
    assert attributes.mobile_scaffolding_notes is None
    assert attributes.lifting_equipment_notes is None

    # Booleani: default False
    assert attributes.equipped_vans is False
    assert attributes.aerial_platforms is False
    assert attributes.mobile_scaffolding is False
    assert attributes.equipped_vehicle_for_inspections is False
    assert attributes.lifting_equipment is False
    assert attributes.atex_equipment is False
    assert attributes.mileage_reimbursement is False
    assert attributes.consumable_materials_supply is False
    assert attributes.specialist_materials_supply is False
    assert attributes.site_survey_availability is False
    assert attributes.travel_availability is False
    assert attributes.weekend_holiday_shutdown_availability is False
    assert attributes.night_shutdown_availability is False
    assert attributes.commissioning_support_availability is False
    assert attributes.experience_logistics is False
    assert attributes.experience_data_center is False
    assert attributes.experience_industry_manufacturing is False
    assert attributes.experience_tertiary_offices_hospitality is False
    assert attributes.experience_food_pharma is False
    assert attributes.experience_healthcare is False
    assert attributes.experience_retail is False
    assert attributes.experience_oil_gas is False
    assert attributes.experience_public_administration is False


# Test the one-to-one relationship with Vendor
@pytest.mark.django_db
def test_operational_attributes_linked_to_vendor(
    db, vendor_factory, vendor_operational_attributes_factory
):
    vendor = vendor_factory()
    attributes = vendor_operational_attributes_factory(vendor=vendor)

    assert vendor.operational_attributes == attributes
    assert attributes.vendor == vendor


# Test a vendor cannot have more than one VendorOperationalAttributes record
@pytest.mark.django_db
def test_operational_attributes_one_per_vendor(
    db, vendor_factory, vendor_operational_attributes_factory
):
    vendor = vendor_factory()
    vendor_operational_attributes_factory(vendor=vendor)

    with pytest.raises(IntegrityError):
        vendor_operational_attributes_factory(vendor=vendor)


# Test valid/invalid values for the autonomy category choice field
@pytest.mark.django_db
def test_operational_attributes_autonomy_category_choices(
    db, vendor_operational_attributes_factory
):
    for valid_category in [1, 2, 3]:
        attributes = vendor_operational_attributes_factory(
            autonomy_category=valid_category
        )
        attributes.full_clean()

    with pytest.raises(ValidationError):
        attributes = vendor_operational_attributes_factory(autonomy_category=4)
        attributes.full_clean()


# Test that the mileage reimbursement flag and its value can be set together
@pytest.mark.django_db
def test_operational_attributes_mileage_reimbursement(
    db, vendor_operational_attributes_factory
):
    attributes = vendor_operational_attributes_factory(
        mileage_reimbursement=True,
        mileage_reimbursement_value=0.35,
    )
    attributes.refresh_from_db()

    assert attributes.mileage_reimbursement is True
    assert float(attributes.mileage_reimbursement_value) == 0.35
