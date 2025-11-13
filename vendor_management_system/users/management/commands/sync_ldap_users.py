from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group
from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import Vendor
import ldap
from django.conf import settings


class Command(BaseCommand):
    help = 'Sincronizza utenti LDAP nel database Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-ldap-user',
            type=str,
            help='Email/username dell\'utente LDAP da creare nel database Django'
        )
        parser.add_argument(
            '--role',
            type=str,
            default='bo_user',
            choices=['admin', 'bo_user', 'vendor'],
            help='Ruolo da assegnare all\'utente (default: bo_user)'
        )
        parser.add_argument(
            '--vendor-code',
            type=str,
            help='Codice fornitore (richiesto solo per ruolo vendor)'
        )
        parser.add_argument(
            '--sync-all',
            action='store_true',
            help='Sincronizza tutti gli utenti LDAP esistenti nel database'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe fatto senza eseguire modifiche'
        )

    def handle(self, *args, **options):
        if options['create_ldap_user']:
            self.create_ldap_user(
                options['create_ldap_user'],
                options['role'],
                options.get('vendor_code'),
                options['dry_run']
            )
        elif options['sync_all']:
            self.sync_all_users(options['dry_run'])
        else:
            raise CommandError('Specifica --create-ldap-user o --sync-all')

    def create_ldap_user(self, email, role, vendor_code=None, dry_run=False):
        """Crea un utente nel database Django che si autenticherà via LDAP"""
        
        # Verifica se l'utente esiste già
        if User.objects.filter(email=email).exists():
            raise CommandError(f'Utente {email} già esistente nel database')
        
        # Valida vendor per ruolo vendor
        vendor = None
        if role == 'vendor':
            if not vendor_code:
                raise CommandError('--vendor-code è richiesto per ruolo vendor')
            try:
                vendor = Vendor.objects.get(vendor_code=vendor_code)
            except Vendor.DoesNotExist:
                raise CommandError(f'Fornitore con codice {vendor_code} non trovato')
        
        # Cerca l'utente in LDAP per verificare che esista
        ldap_user_info = self.search_ldap_user(email)
        
        if not ldap_user_info:
            raise CommandError(
                f'Utente {email} non trovato in LDAP. '
                'L\'utente deve esistere nel server LDAP prima di essere sincronizzato.'
            )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Verrebbe creato utente:')
            )
            self.stdout.write(f'  Email: {email}')
            self.stdout.write(f'  Nome: {ldap_user_info.get("name", "N/A")}')
            self.stdout.write(f'  Ruolo: {role}')
            self.stdout.write(f'  LDAP: Sì')
            if vendor:
                self.stdout.write(f'  Fornitore: {vendor.name}')
            return
        
        # Crea l'utente nel database Django
        try:
            user = User.objects.create(
                email=email,
                name=ldap_user_info.get('name', email.split('@')[0]),
                role=role,
                is_ldap_user=True,
                vendor=vendor,
                is_active=True
            )
            
            # Imposta una password non utilizzabile (si autenticherà via LDAP)
            user.set_unusable_password()
            user.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Utente LDAP {email} creato con successo (ruolo: {role})'
                )
            )
            
            # Mostra i gruppi assegnati
            groups = user.groups.values_list('name', flat=True)
            if groups:
                self.stdout.write(f'  Gruppi assegnati: {", ".join(groups)}')
                
        except Exception as e:
            raise CommandError(f'Errore nella creazione dell\'utente: {str(e)}')

    def search_ldap_user(self, email):
        """Cerca un utente nel server LDAP (SOLO LETTURA)"""
        try:
            # Configura la connessione LDAP
            ldap_server = getattr(settings, 'AUTH_LDAP_SERVER_URI', None)
            if not ldap_server:
                raise CommandError('AUTH_LDAP_SERVER_URI non configurato in settings')
            
            bind_dn = getattr(settings, 'AUTH_LDAP_BIND_DN', '')
            bind_password = getattr(settings, 'AUTH_LDAP_BIND_PASSWORD', '')
            search_base = getattr(settings, 'AUTH_LDAP_USER_SEARCH_BASE', '')
            
            # Connetti al server LDAP
            conn = ldap.initialize(ldap_server)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            
            # Bind con le credenziali di servizio
            if bind_dn and bind_password:
                conn.simple_bind_s(bind_dn, bind_password)
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'AUTH_LDAP_BIND_DN/PASSWORD non configurati, '
                        'tentativo di ricerca anonima'
                    )
                )
            
            # Cerca l'utente
            search_filter = f'(mail={email})'
            attributes = ['cn', 'mail', 'displayName', 'givenName', 'sn']
            
            result = conn.search_s(
                search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                attributes
            )
            
            conn.unbind_s()
            
            if not result:
                return None
            
            # Estrai le informazioni dell'utente
            dn, attrs = result[0]
            user_info = {
                'dn': dn,
                'email': attrs.get('mail', [b''])[0].decode('utf-8'),
                'name': (
                    attrs.get('displayName', [b''])[0].decode('utf-8') or
                    attrs.get('cn', [b''])[0].decode('utf-8') or
                    email.split('@')[0]
                )
            }
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Utente trovato in LDAP: {user_info["name"]}')
            )
            
            return user_info
            
        except ldap.LDAPError as e:
            self.stdout.write(
                self.style.ERROR(f'Errore LDAP: {str(e)}')
            )
            self.stdout.write(
                self.style.WARNING(
                    'NOTA: L\'utente sarà creato nel database anche se non trovato in LDAP. '
                    'Assicurati che esista nel server LDAP per permettere il login.'
                )
            )
            return {'name': email.split('@')[0], 'email': email}
        except Exception as e:
            raise CommandError(f'Errore nella ricerca LDAP: {str(e)}')

    def sync_all_users(self, dry_run=False):
        """Sincronizza gli utenti LDAP esistenti nel database con il server LDAP"""
        ldap_users = User.objects.filter(is_ldap_user=True)
        
        self.stdout.write(f'Trovati {ldap_users.count()} utenti LDAP nel database')
        
        for user in ldap_users:
            ldap_info = self.search_ldap_user(user.email)
            
            if ldap_info and ldap_info.get('name') != user.name:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f'[DRY RUN] {user.email}: '
                            f'Nome verrebbe aggiornato da "{user.name}" a "{ldap_info["name"]}"'
                        )
                    )
                else:
                    user.name = ldap_info['name']
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ {user.email}: Nome aggiornato a "{ldap_info["name"]}"'
                        )
                    )