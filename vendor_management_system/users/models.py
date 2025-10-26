import uuid
from typing import ClassVar
from django.contrib.auth.models import AbstractUser, Group
from django.db.models import CharField, EmailField, ForeignKey, SET_NULL, BooleanField
from django.utils.translation import gettext_lazy as _
from vendor_management_system.users.managers import UserManager

class User(AbstractUser):
    # Ruoli disponibili
    ROLE_CHOICES = [
        ('admin', _('Amministratore')),
        ('bo_user', _('Utente Back Office')),
        ('vendor', _('Fornitore')),
    ]
    
    # Fields
    id = CharField(_("ID of User"), primary_key=True, editable=False, default=uuid.uuid4, max_length=36)
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
        default='bo_user',
        help_text=_("Ruolo dell'utente nel sistema")
    )
    
    # Collegamento al Vendor (solo per utenti vendor)
    vendor = ForeignKey(
        "vendors.Vendor",
        on_delete=SET_NULL,
        verbose_name=_("Fornitore"),
        help_text=_("Fornitore associato a questo utente"),
        null=True,
        blank=True,
        related_name="users"
    )
    
    # Tracciamento origine utente
    is_ldap_user = BooleanField(
        _("Utente LDAP"),
        default=False,
        help_text=_("Indica se l'utente è stato creato tramite autenticazione LDAP")
    )

    # Username Field
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    # Required Fields
    REQUIRED_FIELDS = ["name"]

    # Manager
    object: ClassVar[UserManager] = UserManager()
    
    def save(self, *args, **kwargs):
        # Assegna automaticamente ai gruppi in base al ruolo
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.assign_to_group()
    
    def assign_to_group(self):
        """Assegna l'utente al gruppo corretto basato sul ruolo"""
        # Rimuovi da tutti i gruppi esistenti
        self.groups.clear()
        
        # Assegna al gruppo appropriato
        if self.role == 'admin':
            group, created = Group.objects.get_or_create(name='Administrators')
            self.groups.add(group)
        elif self.role == 'bo_user':
            group, created = Group.objects.get_or_create(name='BackOffice Users')
            self.groups.add(group)
        elif self.role == 'vendor':
            group, created = Group.objects.get_or_create(name='Vendors')
            self.groups.add(group)
    
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    def is_bo_user(self):
        return self.role == 'bo_user'
    
    def is_vendor_user(self):
        return self.role == 'vendor' and self.vendor is not None
    
    def can_access_admin(self):
        return self.is_admin()
    
    def can_manage_vendors(self):
        return self.is_admin() or self.is_bo_user()
    
    def can_manage_documents(self):
        return self.is_admin() or self.is_bo_user()
    
    def can_view_all_documents(self):
        return self.is_admin() or self.is_bo_user()
