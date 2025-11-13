"""
View temporanea per bypassare il problema del redirect
"""
from django.http import HttpResponse
from django.views import View
from django.conf import settings

class TempHomeView(View):
    """View temporanea per testare senza redirect di login"""
    
    def get(self, request):
        return HttpResponse(f"""
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SRM - Modalita Sviluppo</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; }}
                .config {{ background: #f0f0f0; padding: 15px; margin: 10px 0; }}
                .success {{ color: green; font-weight: bold; }}
                .error {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>SRM - Sistema Gestione Fornitori</h1>
            <h2>Modalita Sviluppo Attiva</h2>
            
            <div class="config">
                <h3>Configurazione Attuale:</h3>
                <p><strong>LOGIN_URL:</strong> {settings.LOGIN_URL}</p>
                <p><strong>USE_FORNITORI_PREFIX:</strong> {getattr(settings, 'USE_FORNITORI_PREFIX', 'NON DEFINITO')}</p>
                <p><strong>STATIC_URL:</strong> {settings.STATIC_URL}</p>
            </div>
            
            <div>
                <h3>Link di Test:</h3>
                <p><a href="/admin/">Admin Django</a></p>
                <p><a href="/auth/login/">Login Page</a></p>
                <p><a href="/swagger/">API Documentation</a></p>
                <p><a href="/vendors/">Vendors API</a></p>
            </div>
            
            <div style="margin-top: 30px; color: #666;">
                <p><small>Server avviato con: DJANGO_SETTINGS_MODULE=config.dev_settings</small></p>
                <p><small>Nessun prefisso /fornitori attivo</small></p>
            </div>
        </body>
        </html>
        """, content_type='text/html; charset=utf-8')