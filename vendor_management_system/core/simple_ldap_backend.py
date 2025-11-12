"""
Backend di autenticazione LDAP semplificato che usa ldap3 direttamente.
"""
import logging
import ssl
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.conf import settings
import ldap3
from ldap3 import Tls

logger = logging.getLogger(__name__)
User = get_user_model()


class SimpleLDAPBackend(ModelBackend):
    """
    Backend LDAP semplificato che usa ldap3 direttamente.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
            
        # Controlla se LDAP è abilitato
        if not getattr(settings, 'LDAP_ENABLED', False):
            return None
            
        try:
            # Usa la configurazione dal .env
            server_uri = getattr(settings, 'AUTH_LDAP_SERVER_URI', '')
            bind_dn = getattr(settings, 'AUTH_LDAP_BIND_DN', '')
            bind_password = getattr(settings, 'AUTH_LDAP_BIND_PASSWORD', '')
            user_base_dn = getattr(settings, 'LDAP_USER_BASE_DN', 'DC=sicura,DC=loc')
            
            if not all([server_uri, bind_dn, bind_password, user_base_dn]):
                logger.error("Configurazione LDAP incompleta")
                return None
                
            # Configurazione TLS
            use_ssl = server_uri.startswith('ldaps://')
            tls_config = None
            
            if use_ssl:
                # Disabilita validazione certificato se richiesto
                validate_cert = getattr(settings, 'LDAP_TLS_VALIDATE', True)
                tls_config = Tls(
                    validate=ssl.CERT_REQUIRED if validate_cert else ssl.CERT_NONE
                )
            
            # Crea server e connessione per il bind di servizio
            server = ldap3.Server(
                server_uri, 
                use_ssl=use_ssl,
                tls=tls_config,
                get_info=ldap3.NONE
            )
            
            # Prima connessione: bind con account di servizio per cercare l'utente
            service_conn = ldap3.Connection(
                server,
                user=bind_dn,
                password=bind_password,
                auto_bind=True
            )
            
            # Cerca l'utente per il DN completo
            search_filter = f"(userPrincipalName={username})"
            success = service_conn.search(
                search_base=user_base_dn,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=['userPrincipalName', 'displayName', 'mail', 'memberOf']
            )
            
            if not success or not service_conn.entries:
                logger.info(f"Utente LDAP non trovato: {username}")
                service_conn.unbind()
                return None
                
            # Ottieni il DN completo dell'utente
            user_entry = service_conn.entries[0]
            user_dn = str(user_entry.entry_dn)
            user_attrs = {
                'userPrincipalName': str(user_entry.userPrincipalName),
                'displayName': str(user_entry.displayName) if user_entry.displayName else '',
                'mail': str(user_entry.mail) if user_entry.mail else username,
                'memberOf': [str(group) for group in user_entry.memberOf] if user_entry.memberOf else []
            }
            
            service_conn.unbind()
            
            # Seconda connessione: autentica l'utente con la sua password
            # Prova diversi formati di bind come nel file Flask funzionante
            bind_formats = [
                user_dn,  # DN completo trovato dalla ricerca
                username,  # UserPrincipalName diretto
                f"sicura\\{username.split('@')[0]}"  # Formato NetBIOS domain\\username
            ]
            
            user_conn = None
            for bind_user in bind_formats:
                try:
                    user_conn = ldap3.Connection(
                        server,
                        user=bind_user,
                        password=password,
                        auto_bind=True
                    )
                    if user_conn.bound:
                        logger.info(f"Bind riuscito con formato: {bind_user}")
                        break
                    user_conn.unbind()
                    user_conn = None
                except Exception as e:
                    logger.debug(f"Bind fallito con formato {bind_user}: {e}")
                    continue
            
            if not user_conn or not user_conn.bound:
                logger.warning(f"Tutti i formati di bind falliti per: {username}")
                return None
            
            # Se arriviamo qui, l'autenticazione è riuscita
            user_conn.unbind()
            
            # Crea o aggiorna l'utente nel database
            user = self.get_or_create_user(username, user_attrs)
            
            logger.info(f"Utente LDAP autenticato con successo: {username}")
            return user
            
        except ldap3.core.exceptions.LDAPBindError:
            logger.warning(f"Credenziali LDAP non valide per: {username}")
            return None
        except Exception as e:
            logger.error(f"Errore durante l'autenticazione LDAP: {e}")
            return None
    
    def get_or_create_user(self, username, ldap_attrs):
        """
        Crea o aggiorna un utente basato sui dati LDAP.
        """
        email = ldap_attrs.get('mail', username)
        display_name = ldap_attrs.get('displayName', '')
        
        try:
            # Cerca per email
            user = User.objects.get(email=email)
            logger.debug(f"Utente LDAP esistente trovato: {email}")
        except User.DoesNotExist:
            # Crea nuovo utente
            user = User(
                email=email,
                name=display_name or email.split('@')[0],
                is_ldap_user=True
            )
            user.set_unusable_password()  # Non usa password Django
            logger.info(f"Nuovo utente LDAP creato: {email}")
        
        # Aggiorna sempre i dati da LDAP
        user.name = display_name or user.name
        user.is_ldap_user = True
        
        # Assegna ruolo basato sui gruppi LDAP
        user.role = self.get_user_role_from_groups(ldap_attrs.get('memberOf', []))
        
        user.save()
        return user
    
    def get_user_role_from_groups(self, member_of_groups):
        """
        Determina il ruolo dell'utente basato sui gruppi LDAP.
        """
        # Mappatura gruppi LDAP -> ruoli (da configurare secondo i tuoi gruppi AD)
        group_role_mapping = getattr(settings, 'LDAP_GROUP_ROLE_MAPPING', {
            'vms_administrators': 'admin',
            'vms_backoffice': 'bo_user',
            'vms_vendors': 'vendor',
        })
        
        # Converti i DN dei gruppi in nomi semplici
        group_names = []
        for group_dn in member_of_groups:
            # Estrae il CN dal DN (es. "CN=gruppo,OU=Groups,DC=domain,DC=com" -> "gruppo")
            if group_dn.startswith('CN='):
                cn_part = group_dn.split(',')[0]
                group_name = cn_part[3:].lower()  # Rimuove "CN=" e converte in minuscolo
                group_names.append(group_name)
        
        # Assegna il ruolo con priorità (admin > bo_user > vendor)
        role_priorities = {'admin': 3, 'bo_user': 2, 'vendor': 1}
        assigned_role = 'bo_user'  # ruolo predefinito
        current_priority = 0
        
        for ldap_group, role in group_role_mapping.items():
            if ldap_group.lower() in group_names:
                priority = role_priorities.get(role, 0)
                if priority > current_priority:
                    assigned_role = role
                    current_priority = priority
        
        return assigned_role


class HybridAuthBackend(ModelBackend):
    """
    Backend ibrido che supporta sia l'autenticazione LDAP che locale.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Prima prova con LDAP semplificato
        ldap_backend = SimpleLDAPBackend()
        user = ldap_backend.authenticate(request, username, password, **kwargs)
        
        if user is not None:
            return user
        
        # Fallback all'autenticazione locale
        logger.debug(f"Autenticazione LDAP fallita per {username}, provo con backend locale")
        return super().authenticate(request, username, password, **kwargs)