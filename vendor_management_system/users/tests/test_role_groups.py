"""Gruppi di ruolo: il gruppo e lo staff seguono il ruolo a ogni salvataggio,
e i permessi Django stanno nei gruppi (non nei singoli utenti)."""

import importlib

import pytest
from django.apps import apps as django_apps
from django.contrib.auth.models import Group

from vendor_management_system.users.models import User
from vendor_management_system.users.roles import (
    ROLE_GROUP_NAMES,
    ensure_role_groups,
)

PASSWORD = "test-pass-1234"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "gruppo"),
    [
        ("admin", "Admin"),
        ("bo_user", "BO User"),
        ("vendor", "Vendors"),
    ],
)
def test_il_gruppo_segue_il_ruolo(role, gruppo):
    user = User.objects.create_user(
        email=f"{role}@example.invalid", password=PASSWORD, role=role
    )

    assert list(user.groups.values_list("name", flat=True)) == [gruppo]


@pytest.mark.django_db
def test_cambio_ruolo_sposta_utente_nel_nuovo_gruppo_e_aggiorna_lo_staff():
    user = User.objects.create_user(
        email="cambio@example.invalid", password=PASSWORD, role="bo_user"
    )
    user.role = "admin"
    user.save()

    assert list(user.groups.values_list("name", flat=True)) == ["Admin"]
    assert user.is_staff is True


@pytest.mark.django_db
def test_gruppo_assegnato_a_mano_viene_riallineato_al_salvataggio():
    user = User.objects.create_user(
        email="manuale@example.invalid", password=PASSWORD, role="bo_user"
    )
    user.groups.add(Group.objects.get(name=ROLE_GROUP_NAMES["admin"]))

    user.save()

    assert list(user.groups.values_list("name", flat=True)) == ["BO User"]


@pytest.mark.django_db
def test_staff_solo_per_admin_e_superuser():
    bo_user = User.objects.create_user(
        email="bo-staff@example.invalid", password=PASSWORD, role="bo_user"
    )
    bo_user.is_staff = True
    bo_user.save()

    superuser = User.objects.create_superuser(
        email="super@example.invalid", password=PASSWORD
    )

    assert bo_user.is_staff is False
    assert superuser.is_staff is True


@pytest.mark.django_db
def test_gruppo_admin_puo_gestire_utenze_portale_ma_non_gruppi_e_permessi():
    admin = User.objects.create_user(
        email="admin-perm@example.invalid", password=PASSWORD, role="admin"
    )

    assert admin.has_perm("users.add_user")
    assert admin.has_perm("users.change_user")
    assert admin.has_perm("vendors.change_vendor")
    assert not admin.has_perm("auth.change_group")
    assert not admin.has_perm("auth.change_permission")


@pytest.mark.django_db
def test_gruppi_bo_e_vendor_non_hanno_permessi_django():
    ensure_role_groups()

    for nome in ("BO User", "Vendors"):
        assert Group.objects.get(name=nome).permissions.count() == 0


@pytest.mark.django_db
def test_ensure_role_groups_riallinea_i_permessi_del_gruppo_admin():
    gruppo = Group.objects.get(name="Admin")
    gruppo.permissions.clear()

    ensure_role_groups()

    assert gruppo.permissions.filter(codename="add_user").exists()
    assert gruppo.permissions.filter(codename="change_vendor").exists()


@pytest.mark.django_db
def test_migrazione_rinomina_gruppi_legacy_e_ricalcola_staff():
    migrazione = importlib.import_module(
        "vendor_management_system.users.migrations.0005_gruppi_ruoli_staff"
    )
    Group.objects.create(name="Administrators")
    Group.objects.create(name="BackOffice Users")
    bo_user = User.objects.create_user(
        email="legacy-bo@example.invalid", password=PASSWORD, role="bo_user"
    )
    User.objects.filter(pk=bo_user.pk).update(is_staff=True)

    migrazione.allinea_gruppi_e_staff(django_apps, None)

    bo_user.refresh_from_db()
    assert not Group.objects.filter(name="Administrators").exists()
    assert not Group.objects.filter(name="BackOffice Users").exists()
    assert bo_user.is_staff is False
    assert list(bo_user.groups.values_list("name", flat=True)) == ["BO User"]
