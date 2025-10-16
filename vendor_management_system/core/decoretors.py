# vendor_management_system/core/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def require_roles(*roles):
    """
    Decoratore che richiede che l'utente abbia uno dei ruoli specificati.
    
    Uso:
    @require_roles('Admin', 'Revisore')
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Superuser può accedere a tutto
            if user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Controlla se l'utente ha uno dei ruoli richiesti
            user_groups = user.groups.values_list('name', flat=True)
            
            if any(role in user_groups for role in roles):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(
                    request, 
                    f'Accesso negato. Sono richiesti i seguenti ruoli: {", ".join(roles)}'
                )
                # Reindirizza alla pagina appropriata in base al ruolo dell'utente
                if 'Fornitore' in user_groups:
                    return redirect('/documents/portal/')
                else:
                    return redirect('/documents/dashboard/')
        
        return _wrapped_view
    return decorator


def admin_or_reviewer_required(view_func):
    """
    Decoratore specifico per viste che richiedono ruolo Admin o Revisore
    """
    return require_roles('Admin', 'Revisore')(view_func)


def vendor_required(view_func):
    """
    Decoratore specifico per viste che richiedono ruolo Fornitore
    """
    return require_roles('Fornitore')(view_func)


def admin_required(view_func):
    """
    Decoratore specifico per viste che richiedono solo ruolo Admin
    """
    return require_roles('Admin')(view_func)


class RoleRequiredMixin:
    """
    Mixin per Class-Based Views che richiede ruoli specifici
    
    Uso:
    class MyView(RoleRequiredMixin, TemplateView):
        required_roles = ['Admin', 'Revisore']
        template_name = 'my_template.html'
    """
    required_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user
        
        if not user.is_authenticated:
            return redirect('login')
        
        # Superuser può accedere a tutto
        if user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Controlla se l'utente ha uno dei ruoli richiesti
        user_groups = user.groups.values_list('name', flat=True)
        
        if any(role in user_groups for role in self.required_roles):
            return super().dispatch(request, *args, **kwargs)
        else:
            messages.error(
                request, 
                f'Accesso negato. Sono richiesti i seguenti ruoli: {", ".join(self.required_roles)}'
            )
            # Reindirizza alla pagina appropriata
            if 'Fornitore' in user_groups:
                return redirect('/documents/portal/')
            else:
                return redirect('/documents/dashboard/')


class AdminOrReviewerMixin(RoleRequiredMixin):
    """Mixin per viste che richiedono ruolo Admin o Revisore"""
    required_roles = ['Admin', 'Revisore']


class VendorMixin(RoleRequiredMixin):
    """Mixin per viste che richiedono ruolo Fornitore"""
    required_roles = ['Fornitore']


class AdminMixin(RoleRequiredMixin):
    """Mixin per viste che richiedono solo ruolo Admin"""
    required_roles = ['Admin']