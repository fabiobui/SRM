from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _
from django import forms

from vendor_management_system.users.models import User


# Custom User Creation Form with Role selection
class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        required=True,
        label=_("Ruolo"),
        help_text=_("Seleziona il ruolo dell'utente"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ("email", "name", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user

# Register User model in Admin
@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    add_form = CustomUserCreationForm
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        (
            _("Permissions"),
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
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    
    # Aggiornato per includere il campo ruolo
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "role", "password1", "password2"),
            },
        ),
    )
    
    list_display = ["email", "name", "is_superuser", "get_groups"]
    search_fields = ["name", "email"]
    ordering = ["id"]
    
    # Metodo per mostrare i gruppi/ruoli nella lista
    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])
    get_groups.short_description = _("Ruoli")