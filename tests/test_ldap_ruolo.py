"""Il login LDAP non deve riscrivere il ruolo assegnato nell'applicazione.

Il ruolo (`User.role`) è la fonte di verità: un Admin non superuser che
accede via LDAP deve restare Admin e quindi staff per `/admin/`.
"""

import pytest

from vendor_management_system.core.simple_ldap_backend import (
    SimpleLDAPBackend,
)
from vendor_management_system.users.models import User

pytestmark = pytest.mark.django_db


def _attrs(email, groups=()):
    return {
        "mail": email,
        "displayName": "Utente LDAP",
        "memberOf": [f"CN={g},OU=Groups,DC=example,DC=com" for g in groups],
    }


@pytest.mark.parametrize("role", ["admin", "buyer", "bo_user"])
def test_utente_esistente_mantiene_il_ruolo_dopo_login_ldap(role):
    email = f"ldap-{role}@example.invalid"
    User.objects.create_user(email=email, password="x", role=role)

    user = SimpleLDAPBackend().get_or_create_user(email, _attrs(email))

    user.refresh_from_db()
    assert user.role == role
    assert user.is_ldap_user
    assert user.is_staff is (role == "admin")


def test_nuovo_utente_riceve_il_ruolo_dai_gruppi_ldap():
    email = "ldap-nuovo@example.invalid"

    user = SimpleLDAPBackend().get_or_create_user(
        email, _attrs(email, ["vms_administrators"])
    )

    assert user.role == "admin"
    assert user.is_staff
    assert not user.is_superuser
