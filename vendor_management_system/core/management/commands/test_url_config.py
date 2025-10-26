"""
Comando per testare la configurazione degli URL
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import reverse, NoReverseMatch


class Command(BaseCommand):
    help = 'Testa la configurazione degli URL per verificare il prefisso /fornitori'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Test Configurazione URL ===\n'))
        
        # Mostra configurazione attuale
        use_prefix = getattr(settings, 'USE_FORNITORI_PREFIX', False)
        force_script_name = getattr(settings, 'FORCE_SCRIPT_NAME', None)
        
        self.stdout.write(f'USE_FORNITORI_PREFIX: {use_prefix}')
        self.stdout.write(f'FORCE_SCRIPT_NAME: {force_script_name}')
        self.stdout.write(f'STATIC_URL: {settings.STATIC_URL}')
        self.stdout.write(f'MEDIA_URL: {settings.MEDIA_URL}')
        self.stdout.write(f'LOGIN_URL: {settings.LOGIN_URL}')
        self.stdout.write(f'LOGIN_REDIRECT_URL: {settings.LOGIN_REDIRECT_URL}')
        self.stdout.write('')
        
        # Test URL reversal
        self.stdout.write(self.style.SUCCESS('=== Test URL Reversal ==='))
        
        url_tests = [
            ('admin:index', 'Admin Home'),
            ('home', 'Homepage'),
            ('schema-swagger-ui', 'Swagger UI'),
            ('vendors--list-create-vendor', 'Vendors List'),
        ]
        
        for url_name, description in url_tests:
            try:
                url = reverse(url_name)
                status = self.style.SUCCESS('✓')
                self.stdout.write(f'{status} {description}: {url}')
            except NoReverseMatch as e:
                status = self.style.ERROR('✗')
                self.stdout.write(f'{status} {description}: ERRORE - {e}')
        
        self.stdout.write('')
        
        # Raccomandazioni
        if use_prefix:
            self.stdout.write(self.style.WARNING('🔧 Modalità PRODUZIONE attiva'))
            self.stdout.write('   - Gli URL useranno il prefisso /fornitori')
            self.stdout.write('   - Configura il web server per gestire il prefisso')
        else:
            self.stdout.write(self.style.SUCCESS('🚀 Modalità SVILUPPO attiva'))
            self.stdout.write('   - Gli URL useranno la root /')
            self.stdout.write('   - Perfetto per il runserver di Django')
        
        self.stdout.write('')
        self.stdout.write('Per cambiare modalità, modifica USE_FORNITORI_PREFIX nel file .env')