"""Società dell'utente dall'attributo AD "company" al login LDAP.

Decide quale sezione società dei fornitori l'utente può modificare.
"""

import pytest

from vendor_management_system.core.simple_ldap_backend import (
    SimpleLDAPBackend,
)
from vendor_management_system.users.models import User

pytestmark = pytest.mark.django_db


def _attrs(email, company):
    return {
        "mail": email,
        "displayName": "Utente LDAP",
        "memberOf": [],
        "company": company,
    }


def test_login_imposta_la_societa_da_ldap():
    email = "ldap-sicura@example.invalid"
    user = SimpleLDAPBackend().get_or_create_user(
        email, _attrs(email, "Sicura S.p.A.")
    )
    user.refresh_from_db()
    assert user.company_id == "SICURA"


def test_login_aggiorna_la_societa_cambiata_in_ad():
    email = "ldap-cambio@example.invalid"
    User.objects.create_user(email=email, password="x", company_id="SICURA")
    user = SimpleLDAPBackend().get_or_create_user(
        email, _attrs(email, "EVIMED")
    )
    user.refresh_from_db()
    assert user.company_id == "EVIMED"


def test_valore_non_riconosciuto_mantiene_la_societa_manuale():
    email = "ldap-ignota@example.invalid"
    User.objects.create_user(email=email, password="x", company_id="IGEAM")
    user = SimpleLDAPBackend().get_or_create_user(
        email, _attrs(email, "Holding sconosciuta")
    )
    user.refresh_from_db()
    assert user.company_id == "IGEAM"
