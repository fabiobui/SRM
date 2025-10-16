from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin che richiede ruolo Admin"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin()
    
    def handle_no_permission(self):
        messages.error(self.request, "Accesso negato. Solo gli amministratori possono accedere a questa sezione.")
        return redirect('dashboard-redirect')


class BackOfficeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin che richiede ruolo Admin o BO User"""
    
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_admin() or self.request.user.is_bo_user()
        )
    
    def handle_no_permission(self):
        messages.error(self.request, "Accesso negato. Solo staff autorizzato può accedere a questa sezione.")
        return redirect('dashboard-redirect')


class VendorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin che richiede ruolo Vendor"""
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_vendor_user()
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Devi essere associato a un fornitore per accedere a questa sezione.")
        return redirect('dashboard-redirect')


class VendorOwnerRequiredMixin(VendorRequiredMixin):
    """Mixin che richiede che il vendor corrisponda all'utente loggato"""
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if hasattr(obj, 'vendor') and obj.vendor != self.request.user.vendor:
            raise PermissionDenied("Non puoi accedere ai dati di altri fornitori.")
        return obj


# Decoratori per function-based views
def admin_required(view_func):
    """Decoratore che richiede ruolo Admin"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin:login')
        if not request.user.is_admin():
            messages.error(request, "Accesso negato. Solo gli amministratori possono accedere.")
            return redirect('dashboard-redirect')
        return view_func(request, *args, **kwargs)
    return wrapper


def backoffice_required(view_func):
    """Decoratore che richiede ruolo Admin o BO User"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin:login')
        if not (request.user.is_admin() or request.user.is_bo_user()):
            messages.error(request, "Accesso negato. Solo lo staff autorizzato può accedere.")
            return redirect('dashboard-redirect')
        return view_func(request, *args, **kwargs)
    return wrapper


def vendor_required(view_func):
    """Decoratore che richiede ruolo Vendor"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin:login')
        if not request.user.is_vendor_user():
            messages.error(request, "Devi essere associato a un fornitore per accedere.")
            return redirect('dashboard-redirect')
        return view_func(request, *args, **kwargs)
    return wrapper
