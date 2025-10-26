# Imports
import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Resolve the base directory of the project
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
dotenv_path = BASE_DIR / ".env"

if dotenv_path.exists():
    print(f"✅ Carico variabili da {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print("⚠️ Nessun file .env trovato in", BASE_DIR)

# --- Imposta modulo di configurazione Django ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Add the project directory to the Python path
sys.path.append(str(BASE_DIR / "vendor_management_system"))

# Set the Django settings module to use for the application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Get the WSGI application for the Django project
application = get_wsgi_application()

# --- 🔧 Forza il prefisso /fornitori per tutti i link ---
class PrefixMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Imposta il prefisso di script usato per generare i link assoluti
        environ['SCRIPT_NAME'] = '/fornitori'
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith('/fornitori'):
            environ['PATH_INFO'] = path_info[len('/fornitori'):]
        return self.app(environ, start_response)

application = PrefixMiddleware(application)

#print("💡 HTTP_HOST:", os.environ.get("HTTP_HOST"))
