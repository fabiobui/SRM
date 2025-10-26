from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings

from vendor_management_system.users.models import User


# Custom User Creation Form with Role selection
class CustomUserCreationForm(UserCreationForm):
    user_type = forms.ChoiceField(
        choices=[
            ('local', _('Utente Locale (Django)')),
            ('ldap', _('Utente LDAP')),
        ],
        required=True,
        label=_("Tipo Utente"),
        help_text=_("Seleziona il tipo di autenticazione per l'utente"),
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='local'
    )
    
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        label=_("Ruolo"),
        help_text=_("Seleziona il ruolo dell'utente"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    vendor = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label=_("Fornitore"),
        help_text=_("Associa l'utente a un fornitore (solo per utenti vendor)"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ("email", "name", "user_type", "role", "vendor")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Importa qui per evitare problemi di importazione circolare
        try:
            from vendor_management_system.vendors.models import Vendor
            self.fields['vendor'].queryset = Vendor.objects.all()
        except ImportError:
            # Se il modello Vendor non esiste, rimuovi il campo
            del self.fields['vendor']
        
        # Per utenti LDAP, nascondi i campi password
        self.fields['password1'].required = False
        self.fields['password2'].required = False
        
        # Aggiungi attributi per JavaScript
        self.fields['user_type'].widget.attrs.update({
            'onchange': 'togglePasswordFields(this.value)'
        })
        self.fields['role'].widget.attrs.update({
            'onchange': 'toggleVendorField(this.value)'
        })

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        role = cleaned_data.get('role')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        vendor = cleaned_data.get('vendor')
        
        # Validazione password per utenti locali
        if user_type == 'local':
            if not password1 or not password2:
                raise ValidationError(
                    _("La password è obbligatoria per gli utenti locali.")
                )
        
        # Validazione vendor per utenti vendor
        if role == 'vendor' and not vendor:
            raise ValidationError(
                _("Seleziona un fornitore per gli utenti di tipo 'Fornitore'.")
            )
        elif role != 'vendor' and vendor:
            cleaned_data['vendor'] = None
            
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        user.vendor = self.cleaned_data.get('vendor')
        
        # Imposta il flag LDAP
        user_type = self.cleaned_data.get('user_type', 'local')
        user.is_ldap_user = (user_type == 'ldap')
        
        # Per utenti LDAP, imposta una password inutilizzabile
        if user.is_ldap_user:
            user.set_unusable_password()
        
        if commit:
            user.save()
        return user


# Custom User Change Form per modificare utenti esistenti
class CustomUserChangeForm(UserChangeForm):
    user_type = forms.ChoiceField(
        choices=[
            ('local', _('Utente Locale (Django)')),
            ('ldap', _('Utente LDAP')),
        ],
        required=True,
        label=_("Tipo Utente"),
        help_text=_("Tipo di autenticazione dell'utente"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    vendor = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label=_("Fornitore"),
        help_text=_("Associa l'utente a un fornitore (solo per utenti vendor)"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ("email", "name", "role", "user_type", "vendor", "is_active", "is_staff", "is_superuser")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Importa qui per evitare problemi di importazione circolare
        try:
            from vendor_management_system.vendors.models import Vendor
            self.fields['vendor'].queryset = Vendor.objects.all()
        except ImportError:
            # Se il modello Vendor non esiste, rimuovi il campo
            del self.fields['vendor']
        
        # Imposta il valore iniziale del tipo utente
        if self.instance and self.instance.pk:
            self.fields['user_type'].initial = 'ldap' if self.instance.is_ldap_user else 'local'

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        vendor = cleaned_data.get('vendor')
        
        # Validazione vendor per utenti vendor
        if role == 'vendor' and not vendor:
            raise ValidationError(
                _("Seleziona un fornitore per gli utenti di tipo 'Fornitore'.")
            )
        elif role != 'vendor' and vendor:
            cleaned_data['vendor'] = None
            
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.vendor = self.cleaned_data.get('vendor')
        
        # Aggiorna il flag LDAP
        user_type = self.cleaned_data.get('user_type', 'local')
        user.is_ldap_user = (user_type == 'ldap')
        
        # Per utenti LDAP, imposta una password inutilizzabile
        if user.is_ldap_user:
            user.set_unusable_password()
        
        if commit:
            user.save()
        return user

# Register User model in Admin
@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informazioni Personali"), {"fields": ("name",)}),
        (_("Ruolo e Associazioni"), {"fields": ("role", "vendor", "user_type")}),
        (
            _("Permessi"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Date Importanti"), {"fields": ("last_login", "date_joined")}),
        (_("Informazioni LDAP"), {"fields": ("is_ldap_user",)}),
    )
    
    # Fieldsets per la creazione di nuovi utenti
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "user_type", "role", "vendor", "password1", "password2"),
            },
        ),
    )
    
    list_display = ["email", "name", "role", "get_user_type", "vendor", "is_active", "is_staff", "get_groups"]
    search_fields = ["name", "email", "vendor__name"]
    ordering = ["email"]
    list_filter = ["role", "is_ldap_user", "is_active", "is_staff", "vendor"]
    
    # Campi di sola lettura per utenti LDAP (alcune informazioni vengono da LDAP)
    readonly_fields = ["is_ldap_user", "last_login", "date_joined"]
    
    def get_readonly_fields(self, request, obj=None):
        """Imposta campi di sola lettura dinamicamente"""
        readonly = list(self.readonly_fields)
        
        # Per utenti LDAP esistenti, alcune informazioni non dovrebbero essere modificabili
        if obj and obj.is_ldap_user:
            readonly.extend(["email", "name"])  # Questi vengono sincronizzati da LDAP
            
        return readonly
    
    def get_fieldsets(self, request, obj=None):
        """Personalizza i fieldsets in base al tipo di utente"""
        fieldsets = list(self.fieldsets)
        
        # Per utenti LDAP, nascondi il campo password
        if obj and obj.is_ldap_user:
            # Rimuovi il campo password per utenti LDAP
            fieldsets[0] = (None, {"fields": ("email",)})
        
        return fieldsets
    
    # Metodo per mostrare il tipo di utente nella lista
    def get_user_type(self, obj):
        return _("LDAP") if obj.is_ldap_user else _("Locale")
    get_user_type.short_description = _("Tipo")
    get_user_type.admin_order_field = "is_ldap_user"
    
    # Metodo per mostrare i gruppi/ruoli nella lista
    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()]) if obj.groups.exists() else "-"
    get_groups.short_description = _("Gruppi")
    
    def save_model(self, request, obj, form, change):
        """Override per gestire la logica di salvataggio personalizzata"""
        # Assicurati che gli utenti LDAP abbiano password inutilizzabile
        if obj.is_ldap_user:
            obj.set_unusable_password()
        
        super().save_model(request, obj, form, change)
        
        # Dopo il salvataggio, assegna ai gruppi appropriati
        if not change:  # Solo per nuovi utenti
            obj.assign_to_group()
    
    def get_form(self, request, obj=None, **kwargs):
        """Personalizza il form in base al contesto"""
        form = super().get_form(request, obj, **kwargs)
        
        # Aggiungi JavaScript per gestire la UI dinamica
        if not obj:  # Solo per nuovi utenti
            form.base_fields['user_type'].widget.attrs.update({
                'onchange': 'togglePasswordFields(this.value)'
            })
            form.base_fields['role'].widget.attrs.update({
                'onchange': 'toggleVendorField(this.value)'
            })
        
        return form
    
    class Media:
        js = ('admin/js/ldap_user_admin.js',)
        css = {
            'all': ('admin/css/ldap_user_admin.css',)
        }