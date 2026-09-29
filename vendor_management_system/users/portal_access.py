"""Accesso al portale fornitori: creazione utenza e invito via email.

Flusso: l'utente fornitore nasce senza password utilizzabile e riceve
un'email con un link a token (flow nativo Django `PasswordResetTokenGenerator`)
per impostarla al primo accesso. Il token si invalida da solo appena la
password viene impostata, perché l'hash del token include quello della
password.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes
from django.utils.http import base36_to_int, urlsafe_base64_encode

from vendor_management_system.core.emails import send_templated_email
from vendor_management_system.users.models import User

INVITE_SUBJECT = "Fulgard — Attivazione del tuo accesso al Portale Fornitori"


class InviteTokenGenerator(PasswordResetTokenGenerator):
    """Token d'invito, distinto da quello di reset password (salt dedicato)
    e con una propria scadenza (`PORTAL_INVITE_TIMEOUT_DAYS`)."""

    key_salt = "vendor_management_system.users.InviteTokenGenerator"

    def check_token(self, user, token):
        # Stessa logica di PasswordResetTokenGenerator.check_token (Django
        # 5.0), che però legge la scadenza da settings.PASSWORD_RESET_TIMEOUT:
        # qui serve quella dell'invito.
        if not (user and token):
            return False
        try:
            ts_b36, _hash = token.split("-")
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False
        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret), token
            ):
                break
        else:
            return False
        timeout = settings.PORTAL_INVITE_TIMEOUT_DAYS * 24 * 60 * 60
        return (self._num_seconds(self._now()) - ts) <= timeout


invite_token_generator = InviteTokenGenerator()


class PortalAccessError(Exception):
    """Errore con messaggio già pronto da mostrare all'operatore."""


def portal_users(vendor):
    """Utenti del portale (ruolo Fornitore) collegati al vendor."""
    return vendor.users.filter(role="vendor").order_by("email")


def pending_invite(user):
    """Vero se l'utente fornitore non ha ancora impostato la password."""
    return (
        user.role == "vendor"
        and not user.is_ldap_user
        and not user.has_usable_password()
    )


def create_portal_user(vendor):
    """Crea l'utente portale del vendor con l'email dell'anagrafica.

    L'utente nasce senza password utilizzabile: la imposterà dal link
    d'invito (`send_portal_invite`).
    """
    email = (vendor.email or "").strip()
    if not email:
        raise PortalAccessError(
            "Il fornitore non ha un'email di contatto: compila il campo "
            "Email nella scheda prima di creare l'accesso al portale."
        )

    if portal_users(vendor).exists():
        raise PortalAccessError(
            'Il fornitore ha già un accesso al portale: usa "Reinvia '
            "invito\" se l'utente non ha ancora impostato la password."
        )

    existing = User.objects.filter(email__iexact=email).first()
    if existing is not None:
        if existing.role == "vendor" and existing.vendor_id == vendor.pk:
            raise PortalAccessError(
                f"Esiste già un accesso al portale per {email}: usa "
                '"Reinvia invito" se l\'utente non ha ancora impostato la '
                "password."
            )
        raise PortalAccessError(
            f"L'email {email} è già usata da un altro utente: non è "
            "possibile creare l'accesso al portale con questo indirizzo."
        )

    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=None,
            name=vendor.reference_contact or vendor.name,
            role="vendor",
            vendor=vendor,
        )
        # User.save() non assegna mai il gruppo (la pk ha un default uuid,
        # quindi "is_new" risulta sempre falso): va fatto esplicitamente,
        # come in UserAdmin.save_model.
        user.assign_to_group()
    return user


def send_portal_invite(user, request):
    """Invia all'utente fornitore l'email con il link "imposta password".

    Restituisce i destinatari effettivi (quelli di redirect, se attivo).
    Gli errori di invio vengono propagati al chiamante.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = invite_token_generator.make_token(user)
    context = {
        "user": user,
        "vendor": user.vendor,
        "greeting_name": user.name or (user.vendor and user.vendor.name),
        "set_password_url": request.build_absolute_uri(
            reverse(
                "portal_invite_confirm",
                kwargs={"uidb64": uidb64, "token": token},
            )
        ),
        "login_url": request.build_absolute_uri(reverse("login")),
        "password_reset_url": request.build_absolute_uri(
            reverse("password_reset")
        ),
        "invite_days": settings.PORTAL_INVITE_TIMEOUT_DAYS,
    }
    return send_templated_email(
        subject=INVITE_SUBJECT,
        template_name="portal_invite",
        context=context,
        to=[user.email],
    )


def invite_and_notify(modeladmin, request, user, *, created):
    """Invia l'invito e riporta l'esito all'operatore dell'admin.

    Un errore di invio non annulla la creazione dell'utente: l'operatore
    viene avvisato e può riprovare con "Reinvia invito".
    """
    prefix = f"Accesso al portale creato per {user.email}. " if created else ""
    try:
        recipients = send_portal_invite(user, request)
    except Exception:  # noqa: BLE001 - già loggato da send_templated_email
        modeladmin.message_user(
            request,
            prefix + "Invio dell'email d'invito non riuscito: riprova più "
            'tardi con "Reinvia invito".',
            messages.WARNING,
        )
        return False
    note = ""
    if recipients != [user.email]:
        note = f" (dirottata a {', '.join(recipients)})"
    modeladmin.message_user(
        request,
        prefix + f"Email d'invito inviata a {user.email}{note}.",
        messages.SUCCESS,
    )
    return True
