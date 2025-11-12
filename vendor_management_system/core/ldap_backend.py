"""
Backend di autenticazione LDAP personalizzato per il sistema VMS.
"""
import logging
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django_auth_ldap.backend import LDAPBackend
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


class CustomLDAPBackend(LDAPBackend):
    """
    Backend LDAP personalizzato che gestisce la sincronizzazione degli utenti
    e l'assegnazione dei ruoli basata sui gruppi LDAP.
    """
    
    def authenticate_ldap_user(self, ldap_user, password):
        """
        Autentica l'utente tramite LDAP e sincronizza i dati.
        """
        user = super().authenticate_ldap_user(ldap_user, password)
        
        if user is not None:
            # Sincronizza i dati utente da LDAP
            self._sync_user_data(user, ldap_user)
            
            # Assegna il ruolo basato sui gruppi LDAP
            self._assign_role_from_ldap_groups(user, ldap_user)
            
            user.save()
            logger.info(f"Utente LDAP autenticato e sincronizzato: {user.email}")
        
        return user
    
    def _sync_user_data(self, user, ldap_user):
        """
        Sincronizza i dati dell'utente da LDAP.
        """
        # Mappa gli attributi LDAP ai campi del modello User
        ldap_attrs = ldap_user.attrs
        
        # Nome completo
        if 'displayName' in ldap_attrs:
            user.name = ldap_attrs['displayName'][0] if ldap_attrs['displayName'] else user.name
        elif 'cn' in ldap_attrs:
            user.name = ldap_attrs['cn'][0] if ldap_attrs['cn'] else user.name
        
        # Email (dovrebbe già essere sincronizzata)
        if 'mail' in ldap_attrs and ldap_attrs['mail']:
            user.email = ldap_attrs['mail'][0]
        
        # Altri attributi personalizzati se necessario
        # user.department = ldap_attrs.get('department', [''])[0]
        # user.phone = ldap_attrs.get('telephoneNumber', [''])[0]
    
    def _assign_role_from_ldap_groups(self, user, ldap_user):
        """
        Assegna il ruolo all'utente basato sui gruppi LDAP.
        """
        ldap_groups = [group.lower() for group in ldap_user.group_names]
        
        # Mappatura gruppi LDAP -> ruoli
        group_role_mapping = getattr(settings, 'LDAP_GROUP_ROLE_MAPPING', {
            'vms_administrators': 'admin',
            'vms_backoffice': 'bo_user',
            'vms_vendors': 'vendor',
        })
        
        # Assegna il ruolo con priorità (admin > bo_user > vendor)
        role_priorities = {'admin': 3, 'bo_user': 2, 'vendor': 1}
        assigned_role = 'bo_user'  # ruolo predefinito
        current_priority = 0
        
        for ldap_group, role in group_role_mapping.items():
            if ldap_group.lower() in ldap_groups:
                priority = role_priorities.get(role, 0)
                if priority > current_priority:
                    assigned_role = role
                    current_priority = priority
        
        # Aggiorna il ruolo solo se è cambiato
        if user.role != assigned_role:
            old_role = user.role
            user.role = assigned_role
            logger.info(f"Ruolo utente {user.email} cambiato da {old_role} a {assigned_role}")
    
    def get_or_build_user(self, username, ldap_user):
        """
        Recupera o crea un utente basato sui dati LDAP.
        """
        model = get_user_model()
        
        # Cerca per email (che è il nostro USERNAME_FIELD)
        email = ldap_user.attrs.get('mail', [username])[0]
        
        try:
            user = model.objects.get(email=email)
            logger.debug(f"Utente LDAP esistente trovato: {email}")
        except model.DoesNotExist:
            # Crea un nuovo utente
            user = model(email=email)
            user.set_unusable_password()  # Non usa password Django
            logger.info(f"Nuovo utente LDAP creato: {email}")
        
        return user, True


class HybridAuthBackend(ModelBackend):
    """
    Backend ibrido che supporta sia l'autenticazione locale che LDAP.
    Controlla prima LDAP, poi fallback all'autenticazione locale.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Prima prova con LDAP
        ldap_backend = CustomLDAPBackend()
        user = ldap_backend.authenticate(request, username, password, **kwargs)
        
        if user is not None:
            return user
        
        # Fallback all'autenticazione locale
        logger.debug(f"Autenticazione LDAP fallita per {username}, provo con backend locale")
        return super().authenticate(request, username, password, **kwargs)