# Imports
import uuid

import factory
from faker import Faker

from vendor_management_system.vendors.models import (
    Address,
    Country,
    Province,
    Region,
    Vendor,
    VendorOperationalAttributes,
)

# Initialize the Faker library
faker = Faker()


# Sigle e nomi reali, coerenti con il catalogo geografico seminato da
# `seed_geography`: servono perche' i test su sede, ricerca ed export
# lavorino su dati plausibili.
SIGLE_PROVINCIA_IT = [
    "MI",
    "RM",
    "TO",
    "NA",
    "BO",
    "FI",
    "VE",
    "BA",
    "PA",
    "GE",
]
NOMI_REGIONE_IT = [
    "Lombardia",
    "Lazio",
    "Piemonte",
    "Campania",
    "Emilia-Romagna",
    "Toscana",
    "Veneto",
    "Puglia",
    "Sicilia",
    "Liguria",
]


# Factory to create an Address object
class AddressFactory(factory.django.DjangoModelFactory):
    # Set the Address model
    class Meta:
        model = Address

    # Set the fields for the Address model
    street_address = factory.LazyFunction(faker.street_address)
    city = factory.LazyFunction(faker.city)
    # `faker.state_abbr` genera sigle di stati USA e `region` restava
    # vuoto: cosi' ogni fornitore di test finiva nel bucket
    # "Non specificato" dei grafici geografici.
    state_province = factory.LazyFunction(
        lambda: faker.random_element(SIGLE_PROVINCIA_IT)
    )
    region = factory.LazyFunction(
        lambda: faker.random_element(NOMI_REGIONE_IT)
    )
    postal_code = factory.LazyFunction(faker.postcode)


# Factory to create a Vendor object
class VendorFactory(factory.django.DjangoModelFactory):
    # Set the Vendor model
    class Meta:
        model = Vendor

    # Set the fields for the Vendor model
    vendor_code = factory.LazyFunction(
        lambda: str(uuid.uuid4()).replace("-", "")[:10].upper()
    )
    name = factory.LazyFunction(faker.company)
    contact_details = factory.LazyFunction(
        lambda: f"{faker.email()}, {faker.phone_number()}"
    )
    address = factory.SubFactory(AddressFactory)
    on_time_delivery_rate = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=100, right_digits=4)
    )
    quality_rating_avg = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=5, right_digits=4)
    )
    average_response_time = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, right_digits=4)
    )
    fulfillment_rate = factory.LazyFunction(
        lambda: faker.pyfloat(min_value=0, max_value=100, right_digits=4)
    )


# Factory to create a VendorOperationalAttributes object
class VendorOperationalAttributesFactory(factory.django.DjangoModelFactory):
    # Set the VendorOperationalAttributes model
    class Meta:
        model = VendorOperationalAttributes

    # Set the fields for the VendorOperationalAttributes model
    vendor = factory.SubFactory(VendorFactory)


# Factory per il catalogo geografico. Utili ai test che non
# hanno bisogno dei codici veri del catalogo: per quelli c'e' la fixture
# `geografia_italia` in `vendors/tests/conftest.py`, che semina l'Italia
# reale con i suoi codici (`IT`, `LOM`, `MI`).
class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country

    # `Country.code` e' max_length=3 e unique.
    code = factory.Sequence(lambda n: f"C{n:02d}")
    name = factory.Sequence(lambda n: f"Nazione {n}")


class RegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Region

    code = factory.Sequence(lambda n: f"REG{n:03d}")
    name = factory.Sequence(lambda n: f"Regione {n}")
    country = factory.SubFactory(CountryFactory)


class ProvinceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Province

    code = factory.Sequence(lambda n: f"P{n:03d}")
    name = factory.Sequence(lambda n: f"Provincia {n}")
    region = factory.SubFactory(RegionFactory)
