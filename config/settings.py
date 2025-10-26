# Imports
import os
from pathlib import Path
from celery.schedules import crontab
from urllib.parse import urlparse
from dotenv import load_dotenv
from django.utils.translation import gettext_lazy as _
#from import_export.formats.base_formats import CSV, XLSX

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "it")
USE_I18N = os.getenv("USE_I18N", "True") == "True"
TIME_ZONE = os.getenv("TIME_ZONE", "Europe/Rome")
USE_TZ = os.getenv("USE_TZ", "True") == "True"

LANGUAGES = [
    ("it", _("Italiano")),
    ("en", _("English")),
    ("fr", _("Français")),
]

LOCALE_PATHS = [BASE_DIR / "locale"]


# App directory of the Django project
APPS_DIR = BASE_DIR / "vendor_management_system"


# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
        },
    },
}


# DATABASES
# ------------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("sqlite"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                             "NAME": DATABASE_URL.split("sqlite:///")[1]}}
else:
    DATABASES = {"default": {
        "ENGINE": os.getenv("DB_ENGINE"),
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "CONN_MAX_AGE": 60,
    }}


# DATABASES["default"]["ATOMIC_REQUESTS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# URLS
# ------------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "jazzmin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_extensions",
    "drf_yasg",
]
LOCAL_APPS = [
    "vendor_management_system.users",
    "vendor_management_system.core",
    "vendor_management_system.vendors",
    "vendor_management_system.purchase_orders",
    "vendor_management_system.historical_performances",
    "vendor_management_system.documents",  # ← NUOVO MODULO
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# AUTHENTICATION
# ------------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = [
    "vendor_management_system.core.ldap_backend.HybridAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# LDAP CONFIGURATION
# ------------------------------------------------------------------------------
import ldap
import ssl
from django_auth_ldap.config import LDAPSearch, GroupOfNamesType

# Supporto per più formati di env vars: LDAP_SERVER/LDAP_PORT oppure LDAP_SERVER_URI
LDAP_SERVER = os.getenv("LDAP_SERVER")
LDAP_PORT = os.getenv("LDAP_PORT")
LDAP_USE_SSL = os.getenv("USE_SSL", os.getenv("LDAP_USE_SSL", "False")) == "True"

# Costruisco l'URI se sono forniti server/porta; altrimenti prendo LDAP_SERVER_URI
if LDAP_SERVER:
    scheme = "ldaps" if LDAP_USE_SSL else "ldap"
    port = LDAP_PORT or ("636" if LDAP_USE_SSL else "389")
    AUTH_LDAP_SERVER_URI = os.getenv("LDAP_SERVER_URI", f"{scheme}://{LDAP_SERVER}:{port}")
else:
    AUTH_LDAP_SERVER_URI = os.getenv("LDAP_SERVER_URI", "ldap://ldap.example.com")

# Bind DN / password (supporta sia LDAP_USER/LDAP_PASSWORD che LDAP_BIND_DN/LDAP_BIND_PASSWORD)
AUTH_LDAP_BIND_DN = os.getenv("LDAP_BIND_DN", os.getenv("LDAP_USER", "cn=admin,dc=example,dc=com"))
AUTH_LDAP_BIND_PASSWORD = os.getenv("LDAP_BIND_PASSWORD", os.getenv("LDAP_PASSWORD", ""))

# StartTLS (usa LDAPS se LDAP_USE_SSL=True)
AUTH_LDAP_START_TLS = os.getenv("LDAP_START_TLS", "False") == "True"

# Se è richiesto disabilitare la validazione del certificato (es. ambiente di test)
# usare LDAP_TLS_VALIDATE=False nel file .env. In produzione lasciare True.
if os.getenv("LDAP_TLS_VALIDATE", "True") in ("False", "false", "0"):
    # Disabilita la validazione del certificato per python-ldap
    try:
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    except Exception:
        # Non bloccare l'avvio se l'opzione non è supportata dall'ambiente
        pass

# Ricerca utenti
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    os.getenv("LDAP_USER_BASE_DN", "ou=users,dc=example,dc=com"),
    ldap.SCOPE_SUBTREE,
    os.getenv("LDAP_USER_FILTER", "(mail=%(user)s)")
)

# Mappatura attributi utente
AUTH_LDAP_USER_ATTR_MAP = {
    "name": "displayName",
    "email": "mail",
}

# Configurazione gruppi LDAP
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    os.getenv("LDAP_GROUP_BASE_DN", "ou=groups,dc=example,dc=com"),
    ldap.SCOPE_SUBTREE,
    "(objectClass=groupOfNames)"
)
AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()

# Mappatura gruppi LDAP -> ruoli applicazione
LDAP_GROUP_ROLE_MAPPING = {
    'vms_administrators': 'admin',
    'vms_backoffice': 'bo_user',
    'vms_vendors': 'vendor',
}

# Opzioni LDAP
AUTH_LDAP_ALWAYS_UPDATE_USER = True
AUTH_LDAP_FIND_GROUP_PERMS = True
AUTH_LDAP_CACHE_TIMEOUT = 3600

# Abilita/disabilita autenticazione LDAP
LDAP_ENABLED = os.getenv("LDAP_ENABLED", "False") == "True"

# Variabili per il comando di test (replicate dalle configurazioni sopra)
LDAP_USER_BASE_DN = os.getenv("LDAP_USER_BASE_DN", "ou=users,dc=example,dc=com")
LDAP_GROUP_BASE_DN = os.getenv("LDAP_GROUP_BASE_DN", "ou=groups,dc=example,dc=com")
LDAP_TLS_VALIDATE = os.getenv("LDAP_TLS_VALIDATE", "True") != "False"


# PASSWORDS
# ------------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

#IMPORT_EXPORT_FORMATS = [XLSX, CSV]  # ordine = priorità nel menu

# STATIC
# ------------------------------------------------------------------------------
# Static & Media
STATIC_URL = "/static/"
# 1) DOVE METTI I TUOI FILE SORGENTE (versionati in git)
STATICFILES_DIRS = [BASE_DIR / "static"]
# 2) DOVE FINISCONO I FILE RACCOLTI (NON versionare)
STATIC_ROOT = BASE_DIR / "staticfiles"


# MEDIA
# ------------------------------------------------------------------------------
MEDIA_ROOT = str(BASE_DIR / "media")
MEDIA_URL = "/media/"


# TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        'DIRS': [
            BASE_DIR / 'vendor_management_system' / 'templates',  # ← IMPORTANTE
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# FIXTURES
# ------------------------------------------------------------------------------
FIXTURE_DIRS = (str(BASE_DIR / "fixtures"),)


# SECURITY
# ------------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"


# ADMIN
# ------------------------------------------------------------------------------
ADMIN_URL = "admin/"
ADMINS = [("""Fabio Bui""", "fabio-bui@fulgard.com")]
MANAGERS = ADMINS

# Nel tuo settings.py, aggiungi questa riga
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# LOGGING
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}


# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TIME_LIMIT = 5 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BEAT_SCHEDULE = {
    "record_historical_performance": {
        "task": "vendor_management_system.historical_performances.tasks.record_historical_performance",
        "schedule": crontab(hour="*/6"),  # Run every 6 hours
    },
}


# django-rest-framework
# -------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "vendor_management_system.core.authentication.QueryParameterTokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}


# django-cors-headers
# -------------------------------------------------------------------------------
CORS_URLS_REGEX = r"^/api/.*$"
