# vendor_management_system/core/auth_views.py

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import View

from vendor_management_system.core.emails import send_templated_email
from vendor_management_system.users.portal_access import (
    invite_token_generator,
)


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Inserisci la tua email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Inserisci la password",
            }
        ),
    )


class CustomLoginView(View):
    template_name = "auth/login.html"
    form_class = LoginForm

    def get(self, request):
        # Se l'utente è già loggato, reindirizza subito
        if request.user.is_authenticated:
            return self.redirect_by_role(request.user)

        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Autentica l'utente
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                request.session.set_expiry(
                    0
                )  # La sessione scade alla chiusura del browser
                messages.success(
                    request, f"Benvenuto, {user.name or user.email}!"
                )

                # Reindirizza basato sul ruolo
                return self.redirect_by_role(user)
            else:
                messages.error(request, "Email o password non corrette.")

        return render(request, self.template_name, {"form": form})

    def redirect_by_role(self, user):
        """Reindirizza l'utente basato sul campo role del modello User"""
        from vendor_management_system.vendors.models import Vendor

        # Verifica se è superuser
        if user.is_superuser:
            return redirect("/admin/")

        # Reindirizzamento basato sul ruolo dell'utente
        if user.role == "admin":
            return redirect("/admin/")
        elif user.role == "bo_user":
            # bo_user atterra sulla dashboard consolidata back-office;
            # admin resta su /admin/, invariato.
            return redirect("/portale/backoffice/dashboard/")
        elif user.role == "vendor":
            try:
                vendor = user.vendor
            except Vendor.DoesNotExist:
                vendor = None
            if vendor:
                return redirect("/documents/portal/")
            messages.warning(
                self.request,
                "Il tuo account fornitore non è collegato a nessuna "
                "anagrafica. Contatta l'amministratore.",
            )
            return redirect("login")
        else:
            # Utente senza ruolo specifico
            messages.warning(
                self.request,
                "Nessun ruolo assegnato. Contatta l'amministratore.",
            )
            return redirect("/admin/")


# In vendor_management_system/core/auth_views.py


class CustomLogoutView(View):
    def get(self, request):
        from django.contrib import messages
        from django.contrib.auth import logout

        # Pulisci tutti i messaggi esistenti
        storage = messages.get_messages(request)
        for _message in storage:
            pass  # Questo consuma tutti i messaggi
        storage.used = True

        # Effettua logout
        logout(request)

        # Aggiungi solo il messaggio di logout
        messages.success(request, "Logout effettuato con successo.")

        return redirect("login")


# -----------------------------------------------------------------------------
# Impostazione / reset password
# -----------------------------------------------------------------------------

PASSWORD_RESET_SUBJECT = (
    "Fulgard — Reimposta la password del Portale Fornitori"
)


class PortalPasswordResetForm(PasswordResetForm):
    """Form "Password dimenticata?" con i template email del progetto.

    A differenza del form Django include anche gli utenti senza password
    utilizzabile (es. un fornitore con invito scaduto può ripartire da solo),
    ma esclude gli utenti LDAP: la loro password si gestisce in Active
    Directory, non qui. Un errore di invio viene solo loggato (da
    `send_templated_email`): la pagina di conferma resta identica per non
    rivelare quali email sono registrate.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Inserisci la tua email"}
        )

    def get_users(self, email):
        return get_user_model()._default_manager.filter(
            email__iexact=email, is_active=True, is_ldap_user=False
        )

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        base_url = f"{context['protocol']}://{context['domain']}"
        reset_path = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": context["uid"], "token": context["token"]},
        )
        try:
            send_templated_email(
                subject=PASSWORD_RESET_SUBJECT,
                template_name="password_reset",
                context={
                    "user": context["user"],
                    "greeting_name": context["user"].name,
                    "reset_url": base_url + reset_path,
                    "login_url": base_url + reverse("login"),
                    "reset_hours": settings.PASSWORD_RESET_TIMEOUT // 3600,
                },
                to=[to_email],
            )
        except Exception:  # noqa: BLE001 - già loggato dall'helper
            pass


class PortalPasswordResetView(auth_views.PasswordResetView):
    template_name = "auth/password_reset_form.html"
    form_class = PortalPasswordResetForm
    success_url = reverse_lazy("password_reset_done")


class PortalPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "auth/password_reset_done.html"


class PortalSetPasswordView(auth_views.PasswordResetConfirmView):
    """Impostazione password da link a token (reset password)."""

    template_name = "auth/password_set.html"
    success_url = reverse_lazy("password_reset_complete")
    is_invite = False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs.update({"class": "form-control"})
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_invite"] = self.is_invite
        return context


class PortalInviteSetPasswordView(PortalSetPasswordView):
    """Primo accesso: impostazione password dal link dell'email d'invito."""

    token_generator = invite_token_generator
    is_invite = True


class PortalPasswordSetDoneView(auth_views.PasswordResetCompleteView):
    template_name = "auth/password_set_done.html"
