"""
Comando per testare la connessione e configurazione LDAP.
"""
import ldap3
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Testa la connessione LDAP e la configurazione'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test-user',
            type=str,
            help='Email utente da testare per l\'autenticazione'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password per testare l\'autenticazione'
        )
        parser.add_argument(
            '--list-users',
            action='store_true',
            help='Lista i primi 10 utenti trovati in LDAP'
        )
        parser.add_argument(
            '--list-groups',
            action='store_true',
            help='Lista i gruppi trovati in LDAP'
        )
    
    def handle(self, *args, **options):
        # Controlla se LDAP è abilitato
        if not getattr(settings, 'LDAP_ENABLED', False):
            self.stdout.write(
                self.style.WARNING(
                    'LDAP non è abilitato. Imposta LDAP_ENABLED=True nel file .env'
                )
            )
            return
        
        # Mostra configurazione LDAP corrente
        self.show_ldap_config()
        
        # Test connessione base
        if not self.test_connection():
            return
        
        # Test specifici
        if options['list_users']:
            self.list_users()
        
        if options['list_groups']:
            self.list_groups()
        
        if options['test_user'] and options['password']:
            self.test_authentication(options['test_user'], options['password'])
    
    def show_ldap_config(self):
        """Mostra la configurazione LDAP corrente."""
        self.stdout.write("📋 Configurazione LDAP corrente:")
        self.stdout.write(f"   Server URI: {getattr(settings, 'AUTH_LDAP_SERVER_URI', 'Non configurato')}")
        self.stdout.write(f"   Bind DN: {getattr(settings, 'AUTH_LDAP_BIND_DN', 'Non configurato')}")
        self.stdout.write(f"   User Base DN: {getattr(settings, 'LDAP_USER_BASE_DN', 'Non configurato')}")
        self.stdout.write(f"   Group Base DN: {getattr(settings, 'LDAP_GROUP_BASE_DN', 'Non configurato')}")
        self.stdout.write(f"   Start TLS: {getattr(settings, 'AUTH_LDAP_START_TLS', False)}")
        self.stdout.write("")
    
    def get_ldap_connection(self):
        """Crea una connessione LDAP con la configurazione corretta."""
        server_uri = getattr(settings, 'AUTH_LDAP_SERVER_URI', '')
        use_ssl = server_uri.startswith('ldaps://')
        tls_config = None
        
        if use_ssl or getattr(settings, 'AUTH_LDAP_START_TLS', False):
            try:
                import ssl
                from ldap3 import Tls
                
                # Se LDAP_TLS_VALIDATE=False, disabilita la validazione certificato
                validate_cert = True
                if hasattr(settings, 'LDAP_TLS_VALIDATE') and not getattr(settings, 'LDAP_TLS_VALIDATE', True):
                    validate_cert = False
                
                tls_config = Tls(
                    validate=ssl.CERT_REQUIRED if validate_cert else ssl.CERT_NONE
                )
            except ImportError:
                self.stdout.write(
                    self.style.WARNING("⚠️ ldap3 non installato. TLS potrebbe non funzionare correttamente.")
                )
        
        server = ldap3.Server(
            server_uri, 
            get_info=ldap3.ALL,
            use_ssl=use_ssl,
            tls=tls_config
        )
        
        return ldap3.Connection(
            server,
            user=getattr(settings, 'AUTH_LDAP_BIND_DN', ''),
            password=getattr(settings, 'AUTH_LDAP_BIND_PASSWORD', ''),
            auto_bind=True
        )
    
    def test_connection(self):
        """Testa la connessione base al server LDAP."""
        self.stdout.write("🔍 Testing connessione LDAP...")
        
        try:
            server_uri = getattr(settings, 'AUTH_LDAP_SERVER_URI', '')
            if not server_uri:
                raise CommandError("AUTH_LDAP_SERVER_URI non configurato")
            
            self.stdout.write(f"   Server: {server_uri}")
            
            # Usa il metodo helper per creare la connessione
            conn = self.get_ldap_connection()
            
            self.stdout.write(
                self.style.SUCCESS("✅ Connessione LDAP riuscita!")
            )
            
            # Mostra info server
            if hasattr(conn, 'server') and hasattr(conn.server, 'info'):
                self.stdout.write(f"   Schema: {conn.server.info.naming_contexts}")
                self.stdout.write(f"   Vendor: {conn.server.info.vendor_name}")
            
            conn.unbind()
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Errore connessione LDAP: {e}")
            )
            return False
    
    def list_users(self):
        """Lista alcuni utenti dal server LDAP."""
        self.stdout.write("\n👥 Listing primi 10 utenti LDAP...")
        
        try:
            conn = self.get_ldap_connection()
            
            # Cerca utenti
            user_base_dn = getattr(settings, 'LDAP_USER_BASE_DN', 'ou=users,dc=example,dc=com')
            
            success = conn.search(
                search_base=user_base_dn,
                search_filter='(objectClass=person)',
                search_scope=ldap3.SUBTREE,
                attributes=['cn', 'mail', 'displayName', 'uid'],
                size_limit=10
            )
            
            if success and conn.entries:
                for entry in conn.entries:
                    name = entry.displayName.value if entry.displayName else entry.cn.value
                    email = entry.mail.value if entry.mail else 'N/A'
                    uid = entry.uid.value if entry.uid else 'N/A'
                    self.stdout.write(f"   • {name} ({email}) - UID: {uid}")
            else:
                self.stdout.write("   Nessun utente trovato")
            
            conn.unbind()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Errore nel listare utenti: {e}")
            )
    
    def list_groups(self):
        """Lista i gruppi dal server LDAP."""
        self.stdout.write("\n👥 Listing gruppi LDAP...")
        
        try:
            conn = self.get_ldap_connection()
            
            # Cerca gruppi
            group_base_dn = getattr(settings, 'LDAP_GROUP_BASE_DN', 'ou=groups,dc=example,dc=com')
            
            success = conn.search(
                search_base=group_base_dn,
                search_filter='(objectClass=groupOfNames)',
                search_scope=ldap3.SUBTREE,
                attributes=['cn', 'description'],
                size_limit=20
            )
            
            if success and conn.entries:
                for entry in conn.entries:
                    name = entry.cn.value
                    desc = entry.description.value if entry.description else 'N/A'
                    self.stdout.write(f"   • {name} - {desc}")
            else:
                self.stdout.write("   Nessun gruppo trovato")
            
            conn.unbind()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Errore nel listare gruppi: {e}")
            )
    
    def test_authentication(self, email, password):
        """Testa l'autenticazione di un utente specifico."""
        self.stdout.write(f"\n🔐 Testing autenticazione per: {email}")
        
        try:
            from django.contrib.auth import authenticate
            
            user = authenticate(username=email, password=password)
            
            if user:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Autenticazione riuscita!")
                )
                self.stdout.write(f"   Nome: {user.name}")
                self.stdout.write(f"   Email: {user.email}")
                self.stdout.write(f"   Ruolo: {user.role}")
                self.stdout.write(f"   Gruppi: {', '.join([g.name for g in user.groups.all()])}")
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Autenticazione fallita")
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Errore durante l'autenticazione: {e}")
            )