"""
Settings per sviluppo locale che bypassa completamente il prefisso /fornitori
"""
from .settings import *

# Forza la disabilitazione del prefisso
USE_FORNITORI_PREFIX = False
FORCE_SCRIPT_NAME = None

# URL di autenticazione senza prefisso
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Static e Media URL senza prefisso  
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

print("🚀 MODALITÀ SVILUPPO: Nessun prefisso /fornitori attivato")