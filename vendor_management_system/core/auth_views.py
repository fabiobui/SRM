# vendor_management_system/core/auth_views.py

from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse
from django.views.generic import View
from django import forms


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Inserisci la tua email'
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Inserisci la password'
        })
    )


class CustomLoginView(View):
    template_name = 'auth/login.html'
    form_class = LoginForm
    
    def get(self, request):
        # Se l'utente è già loggato, reindirizza subito
        if request.user.is_authenticated:
            return self.redirect_by_role(request.user)
        
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # Autentica l'utente
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Benvenuto, {user.name or user.email}!')
                
                # Reindirizza basato sul ruolo
                return self.redirect_by_role(user)
            else:
                messages.error(request, 'Email o password non corrette.')
        
        return render(request, self.template_name, {'form': form})
    
    def redirect_by_role(self, user):
        """Reindirizza l'utente basato sui suoi gruppi/ruoli"""
        
        # Verifica se è superuser
        if user.is_superuser:
            return redirect('/admin/')
        
        # Ottieni i nomi dei gruppi dell'utente
        user_groups = user.groups.values_list('name', flat=True)
        
        # Reindirizzamento basato sui ruoli
        if 'Admin' in user_groups or 'Revisore' in user_groups:
            return redirect('/vendors/dashboard/')
        elif 'Fornitore' in user_groups:
            return redirect('/documents/portal/')
        else:
            # Utente senza ruolo specifico - vai alla dashboard admin di default
            messages.warning(
                self.request if hasattr(self, 'request') else None,
                'Nessun ruolo assegnato. Contatta l\'amministratore.'
            )
            return redirect('/vendors/dashboard/')


# In vendor_management_system/core/auth_views.py

class CustomLogoutView(View):
    def get(self, request):
        from django.contrib.auth import logout
        from django.contrib import messages
        
        # Pulisci tutti i messaggi esistenti
        storage = messages.get_messages(request)
        for message in storage:
            pass  # Questo consuma tutti i messaggi
        storage.used = True
        
        # Effettua logout
        logout(request)
        
        # Aggiungi solo il messaggio di logout
        messages.success(request, 'Logout effettuato con successo.')
        
        return redirect('login')