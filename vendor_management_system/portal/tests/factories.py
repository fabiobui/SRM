"""Factory di supporto per i test dell'app portal.

Riusa `VendorFactory`/`AddressFactory` da `vendors.tests.factories` (vedi
CLAUDE.md, sezione Test) e aggiunge le factory specifiche del portale
fornitore: un utente con ruolo "vendor", e i record che il back-office
pre-crea per il fornitore (Document, VendorCompetence, VendorService).
"""

import factory
from faker import Faker

from vendor_management_system.documents.models import Document, DocumentCatalog
from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import (
    Category,
    Competence,
    ServiceSet,
    ServiceType,
    VendorCompetence,
    VendorService,
)
from vendor_management_system.vendors.tests.factories import VendorFactory

faker = Faker()


class VendorUserFactory(factory.django.DjangoModelFactory):
    """Utente con ruolo "vendor", collegato a un Vendor (proprio o nuovo)."""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"vendor-user-{n}@example.invalid")
    name = factory.LazyFunction(faker.name)
    role = "vendor"
    vendor = factory.SubFactory(VendorFactory)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "test-pass-1234")
        if create:
            self.save()


class DocumentCatalogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentCatalog

    code = factory.Sequence(lambda n: f"DOCTYPE{n}")
    name = factory.LazyFunction(faker.word)


class DocumentFactory(factory.django.DjangoModelFactory):
    """Document pre-creato dal BO per un vendor (status PENDING di default)."""

    class Meta:
        model = Document

    vendor = factory.SubFactory(VendorFactory)
    document_type = factory.SubFactory(DocumentCatalogFactory)
    status = "PENDING"


class CompetenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Competence

    code = factory.Sequence(lambda n: f"COMP{n}")
    name = factory.LazyFunction(faker.word)


class VendorCompetenceFactory(factory.django.DjangoModelFactory):
    """VendorCompetence pre-assegnata dal BO a un vendor."""

    class Meta:
        model = VendorCompetence

    vendor = factory.SubFactory(VendorFactory)
    competence = factory.SubFactory(CompetenceFactory)


class ServiceTypeFactory(factory.django.DjangoModelFactory):
    """Per default è una categoria (`parent=None`). Per un servizio
    specifico (l'unico tipo proponibile in "Aggiungi servizio"), passare
    `parent=ServiceTypeFactory()`."""

    class Meta:
        model = ServiceType

    code = factory.Sequence(lambda n: f"SVC{n}")
    name = factory.LazyFunction(faker.word)


class VendorServiceFactory(factory.django.DjangoModelFactory):
    """VendorService pre-assegnato dal BO a un vendor."""

    class Meta:
        model = VendorService

    vendor = factory.SubFactory(VendorFactory)
    service_type = factory.SubFactory(ServiceTypeFactory)


class CategoryFactory(factory.django.DjangoModelFactory):
    """Classificazione fornitore (`Vendor.category`)."""

    class Meta:
        model = Category

    code = factory.Sequence(lambda n: f"CAT{n}")
    name = factory.LazyFunction(faker.word)


class ServiceSetFactory(factory.django.DjangoModelFactory):
    """Set di servizi collegabile a una Category, usato per filtrare la
    tendina "Aggiungi servizio" in base alla classificazione del vendor."""

    class Meta:
        model = ServiceSet

    name = factory.LazyFunction(faker.word)
