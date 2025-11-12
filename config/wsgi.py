# Imports
import os
import sys
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv  # <--- IMPORTANTE

# Resolve the base directory of the project
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# Carica le variabili dal file .env
dotenv_path = BASE_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"✅ File .env caricato da {dotenv_path}")
else:
    print("⚠️ Nessun file .env trovato!")

# Add the project directory to the Python path
sys.path.append(str(BASE_DIR / "vendor_management_system"))


# Set the Django settings module to use for the application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


# Get the WSGI application for the Django project
application = get_wsgi_application()

# ============================
# Forza il prefisso /fornitori
# ============================
class PrefixMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = '/fornitori'
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith('/fornitori'):
            environ['PATH_INFO'] = path_info[len('/fornitori'):]
        return self.app(environ, start_response)

application = PrefixMiddleware(application)

