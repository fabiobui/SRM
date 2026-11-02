import uuid
from typing import ClassVar

from django.contrib.auth.models import AbstractUser, Group
from django.db.models import (
    SET_NULL,
    BooleanField,
    CharField,
    EmailField,
    ForeignKey,
)
from django.utils.translation import gettext_lazy as _

from vendor_management_system.users.managers import UserManager
from vendor_management_system.users.roles import (
    ROLE_GROUP_NAMES,
    ensure_role_groups,
)


class User(AbstractUser):
    # Ruoli disponibili
    ROLE_CHOICES = [
        ("admin", _("Amministratore")),
        ("bo_user", _("Utente Back Office")),
        ("vendor", _("Fornitore")),
    ]

    # Fields
    id = CharField(
        _("ID of User"),
        primary_key=True,
        editable=False,
        default=uuid.uuid4,
        max_length=36,
    )
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None
    last_name = None
    email = EmailField(_("Email Address"), unique=True)
    username = None

    # Ruolo utente
    role = CharField(
        _("Ruolo"),
        max_length=20,
        choices=ROLE_CHOICES,
        default="bo_user",
        help_text=_("Ruolo dell'utente nel sistema"),
    )

    # Collegamento al Vendor (solo per utenti vendor)
    vendor = ForeignKey(
        "vendors.Vendor",
        on_delete=SET_NULL,
        verbose_name=_("Fornitore"),
        help_text=_("Fornitore associato a questo utente"),
        null=True,
        blank=True,
        related_name="users",
    )

    # Tracciamento origine utente
    is_ldap_user = BooleanField(
        _("Utente LDAP"),
        default=False,
        help_text=_(
            "Indica se l'utente è stato creato tramite autenticazione LDAP"
        ),
    )

    # Username Field
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    # Required Fields
    REQUIRED_FIELDS = ["name"]

    # Manager
    objects: ClassVar[UserManager] = UserManager()

    def save(self, *args, **kwargs):
        # Lo staff serve solo per entrare in /admin/: lo concediamo ai soli
        # Admin e superuser, qualunque valore sia stato impostato a mano.
        self.is_staff = self.is_superuser or self.role == "admin"
        super().save(*args, **kwargs)
        self.sync_role_group()

    def sync_role_group(self):
        """Porta l'utente nel solo gruppo corrispondente al suo ruolo.

        Chiamato a ogni salvataggio, così anche i gruppi assegnati a mano
        vengono riallineati.
        """
        name = ROLE_GROUP_NAMES.get(self.role)
        if name is None:
            self.groups.clear()
            return
        group = Group.objects.filter(name=name).first()
        if group is None:
            ensure_role_groups()
            group = Group.objects.get(name=name)
        self.groups.set([group])

    def is_admin(self):
        return self.role == "admin" or self.is_superuser

    def is_bo_user(self):
        return self.role == "bo_user"

    def is_vendor_user(self):
        if self.role != "vendor":
            return False
        from vendor_management_system.vendors.models import Vendor

        try:
            return self.vendor is not None
        except Vendor.DoesNotExist:
            return False

    def can_access_admin(self):
        return self.is_admin()

    def can_manage_vendors(self):
        return self.is_admin() or self.is_bo_user()

    def can_manage_documents(self):
        return self.is_admin() or self.is_bo_user()

    def can_view_all_documents(self):
        return self.is_admin() or self.is_bo_user()
