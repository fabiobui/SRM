"""
View di test per verificare la configurazione URL
"""
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.urls import reverse
from django.views import View

class TestUrlConfigView(View):
    """View per testare la configurazione URL"""
    
    def get(self, request):
        return JsonResponse({
            'USE_FORNITORI_PREFIX': getattr(settings, 'USE_FORNITORI_PREFIX', None),
            'FORCE_SCRIPT_NAME': getattr(settings, 'FORCE_SCRIPT_NAME', None),
            'LOGIN_URL': settings.LOGIN_URL,
            'LOGIN_REDIRECT_URL': getattr(settings, 'LOGIN_REDIRECT_URL', None),
            'STATIC_URL': settings.STATIC_URL,
            'MEDIA_URL': settings.MEDIA_URL,
            'urls': {
                'admin': reverse('admin:index'),
                'home': reverse('home'),
                'swagger': reverse('schema-swagger-ui'),
            }
        })

class SimpleTestView(View):
    """View semplice per test senza autenticazione"""
    
    def get(self, request):
        return HttpResponse(f"""
        <h1>Test Configurazione URL</h1>
        <p><strong>LOGIN_URL:</strong> {settings.LOGIN_URL}</p>
        <p><strong>USE_FORNITORI_PREFIX:</strong> {getattr(settings, 'USE_FORNITORI_PREFIX', 'NON DEFINITO')}</p>
        <p><strong>FORCE_SCRIPT_NAME:</strong> {getattr(settings, 'FORCE_SCRIPT_NAME', 'NON DEFINITO')}</p>
        <p><a href="/admin/">Admin</a></p>
        <p><a href="/auth/login/">Login Corretto</a></p>
        """, content_type='text/html')