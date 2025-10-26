"""
Comando per testare l'autenticazione LDAP
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import authenticate
from django.conf import settings
from vendor_management_system.core.ldap_backend import CustomLDAPBackend

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Testa l\'autenticazione LDAP con un utente specifico'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email dell\'utente da testare',
        )
        parser.add_argument(
            'password',
            type=str,
            help='Password dell\'utente',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Output verboso con dettagli del processo di autenticazione',
        )

    def handle(self, *args, **options):
        if not getattr(settings, 'LDAP_ENABLED', False):
            raise CommandError('LDAP non è abilitato nelle impostazioni.')

        email = options['email']
        password = options['password']
        verbose = options['verbose']

        if verbose:
            # Abilita logging dettagliato per django-auth-ldap
            ldap_logger = logging.getLogger('django_auth_ldap')
            ldap_logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            ldap_logger.addHandler(handler)

        self.stdout.write(f'Tentativo di autenticazione LDAP per: {email}')
        
        try:
            # Prova l'autenticazione
            user = authenticate(username=email, password=password)
            
            if user is not None:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Autenticazione riuscita!')
                )
                self.stdout.write(f'  Nome: {user.name}')
                self.stdout.write(f'  Email: {user.email}')
                self.stdout.write(f'  Ruolo: {user.get_role_display()}')
                self.stdout.write(f'  Utente LDAP: {"Sì" if user.is_ldap_user else "No"}')
                self.stdout.write(f'  Attivo: {"Sì" if user.is_active else "No"}')
                
                # Mostra i gruppi
                groups = user.groups.all()
                if groups:
                    group_names = [group.name for group in groups]
                    self.stdout.write(f'  Gruppi: {", ".join(group_names)}')
                else:
                    self.stdout.write('  Gruppi: Nessuno')
                    
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Autenticazione fallita per {email}')
                )
                
                # Suggerimenti per il debug
                self.stdout.write('\nSuggerimenti per il debug:')
                self.stdout.write('1. Verifica che l\'utente esista nel server LDAP')
                self.stdout.write('2. Controlla le credenziali di bind LDAP')
                self.stdout.write('3. Verifica la configurazione del base DN')
                self.stdout.write('4. Usa --verbose per più dettagli')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Errore durante l\'autenticazione: {e}')
            )
            
            if verbose:
                import traceback
                self.stdout.write('\nTraceback completo:')
                self.stdout.write(traceback.format_exc())