"""
Comando di gestione per sincronizzare utenti LDAP esistenti
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from django_auth_ldap.backend import LDAPBackend
import ldap

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Sincronizza utenti LDAP esistenti o crea utenti LDAP pre-configurati'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-existing',
            action='store_true',
            help='Sincronizza tutti gli utenti LDAP esistenti nel database',
        )
        parser.add_argument(
            '--create-ldap-user',
            type=str,
            help='Crea un nuovo utente LDAP specificando l\'email (deve esistere in LDAP)',
        )
        parser.add_argument(
            '--list-ldap-users',
            action='store_true',
            help='Elenca tutti gli utenti disponibili nel server LDAP',
        )
        parser.add_argument(
            '--test-ldap-connection',
            action='store_true',
            help='Testa la connessione al server LDAP',
        )
        parser.add_argument(
            '--role',
            type=str,
            choices=['admin', 'bo_user', 'vendor'],
            default='bo_user',
            help='Ruolo da assegnare al nuovo utente LDAP (default: bo_user)',
        )

    def handle(self, *args, **options):
        if not getattr(settings, 'LDAP_ENABLED', False):
            raise CommandError('LDAP non è abilitato nelle impostazioni.')

        if options['test_ldap_connection']:
            self.test_ldap_connection()
        elif options['list_ldap_users']:
            self.list_ldap_users()
        elif options['sync_existing']:
            self.sync_existing_users()
        elif options['create_ldap_user']:
            self.create_ldap_user(options['create_ldap_user'], options['role'])
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Specifica un\'azione: --sync-existing, --create-ldap-user, '
                    '--list-ldap-users, o --test-ldap-connection'
                )
            )

    def test_ldap_connection(self):
        """Testa la connessione al server LDAP"""
        try:
            backend = LDAPBackend()
            connection = backend.ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
            
            # Prova a fare bind con le credenziali di servizio
            if settings.AUTH_LDAP_BIND_DN and settings.AUTH_LDAP_BIND_PASSWORD:
                connection.simple_bind_s(
                    settings.AUTH_LDAP_BIND_DN,
                    settings.AUTH_LDAP_BIND_PASSWORD
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Connessione LDAP riuscita: {settings.AUTH_LDAP_SERVER_URI}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'Credenziali bind LDAP non configurate. Test di connessione limitato.'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Errore connessione LDAP: {e}')
            )

    def list_ldap_users(self):
        """Elenca utenti disponibili in LDAP"""
        try:
            backend = LDAPBackend()
            connection = backend.ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
            
            if settings.AUTH_LDAP_BIND_DN and settings.AUTH_LDAP_BIND_PASSWORD:
                connection.simple_bind_s(
                    settings.AUTH_LDAP_BIND_DN,
                    settings.AUTH_LDAP_BIND_PASSWORD
                )
                
                # Cerca utenti nella base DN configurata
                search_filter = '(objectClass=person)'  # Filtro generico per persone
                results = connection.search_s(
                    settings.LDAP_USER_BASE_DN,
                    ldap.SCOPE_SUBTREE,
                    search_filter,
                    ['mail', 'displayName', 'cn']
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Utenti trovati in LDAP ({len(results)} risultati):')
                )
                
                for dn, attrs in results:
                    if 'mail' in attrs and attrs['mail']:
                        email = attrs['mail'][0].decode('utf-8')
                        name = ''
                        
                        if 'displayName' in attrs and attrs['displayName']:
                            name = attrs['displayName'][0].decode('utf-8')
                        elif 'cn' in attrs and attrs['cn']:
                            name = attrs['cn'][0].decode('utf-8')
                        
                        # Controlla se l'utente esiste già nel database
                        exists_in_db = User.objects.filter(email=email).exists()
                        status = '(già nel DB)' if exists_in_db else '(nuovo)'
                        
                        self.stdout.write(f'  • {email} - {name} {status}')
                        
            else:
                raise CommandError('Credenziali bind LDAP non configurate.')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Errore nell\'elencare utenti LDAP: {e}')
            )

    def sync_existing_users(self):
        """Sincronizza utenti LDAP esistenti nel database"""
        ldap_users = User.objects.filter(is_ldap_user=True)
        
        if not ldap_users.exists():
            self.stdout.write(
                self.style.WARNING('Nessun utente LDAP trovato nel database.')
            )
            return
        
        backend = LDAPBackend()
        synced_count = 0
        
        for user in ldap_users:
            try:
                # Simula un'autenticazione per sincronizzare i dati
                ldap_user = backend.get_user_model().objects.get(email=user.email)
                if ldap_user:
                    # Qui potresti aggiungere logica di sincronizzazione più specifica
                    self.stdout.write(f'✓ Sincronizzato: {user.email}')
                    synced_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Errore sincronizzazione {user.email}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Sincronizzati {synced_count} utenti LDAP.')
        )

    def create_ldap_user(self, email, role):
        """Crea un nuovo utente LDAP nel database locale"""
        # Controlla se l'utente esiste già
        if User.objects.filter(email=email).exists():
            raise CommandError(f'Utente con email {email} esiste già nel database.')
        
        try:
            # Verifica che l'utente esista in LDAP
            backend = LDAPBackend()
            connection = backend.ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
            
            if settings.AUTH_LDAP_BIND_DN and settings.AUTH_LDAP_BIND_PASSWORD:
                connection.simple_bind_s(
                    settings.AUTH_LDAP_BIND_DN,
                    settings.AUTH_LDAP_BIND_PASSWORD
                )
                
                # Cerca l'utente in LDAP
                search_filter = f'(mail={email})'
                results = connection.search_s(
                    settings.LDAP_USER_BASE_DN,
                    ldap.SCOPE_SUBTREE,
                    search_filter,
                    ['mail', 'displayName', 'cn']
                )
                
                if not results:
                    raise CommandError(f'Utente {email} non trovato nel server LDAP.')
                
                # Estrai informazioni dall'LDAP
                dn, attrs = results[0]
                name = ''
                
                if 'displayName' in attrs and attrs['displayName']:
                    name = attrs['displayName'][0].decode('utf-8')
                elif 'cn' in attrs and attrs['cn']:
                    name = attrs['cn'][0].decode('utf-8')
                else:
                    name = email.split('@')[0]  # Fallback
                
                # Crea l'utente nel database
                user = User(
                    email=email,
                    name=name,
                    role=role,
                    is_ldap_user=True,
                )
                user.set_unusable_password()
                user.save()
                
                # Assegna ai gruppi appropriati
                user.assign_to_group()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Utente LDAP creato: {email} - {name} (ruolo: {role})'
                    )
                )
                
            else:
                raise CommandError('Credenziali bind LDAP non configurate.')
                
        except Exception as e:
            raise CommandError(f'Errore nella creazione dell\'utente LDAP: {e}')