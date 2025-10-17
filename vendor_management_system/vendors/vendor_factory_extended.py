# Imports
import uuid
from datetime import date, timedelta

import factory
from faker import Faker

from vendor_management_system.vendors.models import Vendor


# Initialize the Faker library
faker = Faker()


# Factory to create a Vendor object
class VendorFactory(factory.django.DjangoModelFactory):
    # Set the Vendor model
    class Meta:
        model = Vendor

    # Core fields
    vendor_code = factory.LazyFunction(
        lambda: str(uuid.uuid4()).replace("-", "")[:10].upper()
    )
    name = factory.LazyFunction(faker.company)
    contact_details = factory.LazyFunction(
        lambda: f"{faker.email()}, {faker.phone_number()}"
    )
    address = factory.LazyFunction(faker.address)
    
    # General information fields
    vat_number = factory.LazyFunction(
        lambda: f"IT{faker.numerify('##########')}"
    )
    fiscal_code = factory.LazyFunction(
        lambda: faker.lexify('????????##?##???')  # Italian fiscal code pattern
    )
    email = factory.LazyFunction(faker.company_email)
    reference_contact = factory.LazyFunction(faker.name)
    phone = factory.LazyFunction(faker.phone_number)
    website = factory.LazyFunction(faker.url)
    
    # Performance fields
    on_time_delivery_rate = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=100, right_digits=2)
    )
    quality_rating_avg = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=5, right_digits=2)
    )
    average_response_time = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=168, right_digits=2)  # Max 1 week
    )
    fulfillment_rate = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=100, right_digits=2)
    )
    
    # Qualification/Compliance fields
    qualification_status = factory.LazyFunction(
        lambda: faker.random_element(elements=['PENDING', 'APPROVED', 'REJECTED'])
    )
    qualification_score = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=100, right_digits=2)
    )
    qualification_date = factory.LazyFunction(
        lambda: faker.date_between(start_date='-2y', end_date='today')
    )
    qualification_expiry = factory.LazyFunction(
        lambda: faker.date_between(start_date='today', end_date='+2y')
    )
    
    # Evaluation and operational capacity fields
    category = factory.LazyFunction(
        lambda: faker.random_element(elements=[
            'Servizi',
            'Forniture',
            'Manutenzione',
            'Consulenza',
            'Logistica',
            'IT & Software',
            'Costruzioni',
            'Alimentari',
            'Energia',
            'Altro'
        ])
    )
    risk_level = factory.LazyFunction(
        lambda: faker.random_element(elements=['LOW', 'MEDIUM', 'HIGH'])
    )
    country = factory.LazyFunction(
        lambda: faker.random_element(elements=[
            'Italia',
            'Germania',
            'Francia',
            'Spagna',
            'Regno Unito',
            'Paesi Bassi',
            'Belgio',
            'Austria',
            'Svizzera',
            'Stati Uniti'
        ])
    )
    iso_certifications = factory.LazyFunction(
        lambda: faker.random_element(elements=[
            'ISO 9001:2015, ISO 14001:2015',
            'ISO 9001:2015',
            'ISO 14001:2015, ISO 45001:2018',
            'ISO 27001:2013',
            'ISO 9001:2015, ISO 27001:2013',
            None,  # Some vendors might not have certifications
            '',
        ])
    )
    
    # Audit and management fields
    last_audit_date = factory.LazyFunction(
        lambda: faker.date_between(start_date='-1y', end_date='today') 
        if faker.boolean(chance_of_getting_true=70) else None
    )
    next_audit_due = factory.LazyFunction(
        lambda: faker.date_between(start_date='today', end_date='+1y')
        if faker.boolean(chance_of_getting_true=80) else None
    )
    review_notes = factory.LazyFunction(
        lambda: faker.text(max_nb_chars=500) 
        if faker.boolean(chance_of_getting_true=60) else None
    )


# Specialized factories for different scenarios
class ApprovedVendorFactory(VendorFactory):
    """Factory for creating approved vendors with good performance"""
    qualification_status = 'APPROVED'
    qualification_score = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=70, max_value=100, right_digits=2)
    )
    risk_level = factory.LazyFunction(
        lambda: faker.random_element(elements=['LOW', 'MEDIUM'])
    )
    on_time_delivery_rate = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=80, max_value=100, right_digits=2)
    )
    quality_rating_avg = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=3.5, max_value=5, right_digits=2)
    )


class PendingVendorFactory(VendorFactory):
    """Factory for creating vendors with pending qualification"""
    qualification_status = 'PENDING'
    qualification_score = None
    qualification_date = None
    qualification_expiry = None
    last_audit_date = None
    next_audit_due = None


class HighRiskVendorFactory(VendorFactory):
    """Factory for creating high-risk vendors"""
    risk_level = 'HIGH'
    qualification_status = factory.LazyFunction(
        lambda: faker.random_element(elements=['PENDING', 'REJECTED'])
    )
    qualification_score = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=60, right_digits=2)
    )
    on_time_delivery_rate = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=70, right_digits=2)
    )
    quality_rating_avg = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=3, right_digits=2)
    )