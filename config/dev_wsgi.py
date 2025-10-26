"""
WSGI config pulito per sviluppo locale senza middleware del prefisso
"""
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
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.dev_settings")

# Add the project directory to the Python path
sys.path.append(str(BASE_DIR / "vendor_management_system"))

# Get the WSGI application for the Django project (SENZA middleware prefisso)
application = get_wsgi_application()

print("🚀 WSGI Sviluppo: Nessun PrefixMiddleware attivato")