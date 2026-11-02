from functools import wraps

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.permissions import BasePermission


def is_backoffice(user):
    """Admin e BO User: i ruoli che vedono l'anagrafica fornitori."""
    return user.is_authenticated and (user.is_admin() or user.is_bo_user())


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin che richiede ruolo Admin"""

    def test_func(self):
        return (
            self.request.user.is_authenticated and self.request.user.is_admin()
        )

    def handle_no_permission(self):
        messages.error(
            self.request,
            "Accesso negato. Solo gli amministratori possono accedere "
            "a questa sezione.",
        )
        return redirect("dashboard-redirect")


class BackOfficeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin che richiede ruolo Admin o BO User"""

    def test_func(self):
        return is_backoffice(self.request.user)

    def handle_no_permission(self):
        messages.error(
            self.request,
            "Accesso negato. Solo staff autorizzato può accedere "
            "a questa sezione.",
        )
        return redirect("dashboard-redirect")


class VendorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin che richiede ruolo Vendor"""

    def test_func(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.is_vendor_user()
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(
                self.request,
                "Devi essere associato a un fornitore per accedere "
                "a questa sezione.",
            )
        return redirect("dashboard-redirect")


class VendorOwnerRequiredMixin(VendorRequiredMixin):
    """Mixin che richiede che il vendor corrisponda all'utente loggato"""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if hasattr(obj, "vendor") and obj.vendor != self.request.user.vendor:
            raise PermissionDenied(
                "Non puoi accedere ai dati di altri fornitori."
            )
        return obj


class IsBackOfficeUser(BasePermission):
    """Permesso DRF: solo Admin e BO User, mai i Fornitori."""

    def has_permission(self, request, view):
        return is_backoffice(request.user)


# Decoratori per function-based views
def admin_required(view_func):
    """Decoratore che richiede ruolo Admin"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("admin:login")
        if not request.user.is_admin():
            messages.error(
                request,
                "Accesso negato. Solo gli amministratori possono accedere.",
            )
            return redirect("dashboard-redirect")
        return view_func(request, *args, **kwargs)

    return wrapper


def backoffice_required(view_func):
    """Decoratore che richiede ruolo Admin o BO User"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not is_backoffice(request.user):
            messages.error(
                request,
                "Accesso negato. Solo lo staff autorizzato può accedere.",
            )
            return redirect("dashboard-redirect")
        return view_func(request, *args, **kwargs)

    return wrapper


def backoffice_api_required(view_func):
    """Come `backoffice_required`, ma per le API JSON: 401/403 invece del
    redirect, così il client JavaScript riceve un errore leggibile."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": "Autenticazione richiesta."}, status=401
            )
        if not is_backoffice(request.user):
            return JsonResponse({"detail": "Permesso negato."}, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper


def vendor_required(view_func):
    """Decoratore che richiede ruolo Vendor"""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("admin:login")
        if not request.user.is_vendor_user():
            messages.error(
                request, "Devi essere associato a un fornitore per accedere."
            )
            return redirect("dashboard-redirect")
        return view_func(request, *args, **kwargs)

    return wrapper
