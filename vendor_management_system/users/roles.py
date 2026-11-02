"""Ruoli applicativi e gruppi Django che li rispecchiano.

Il campo `User.role` è la fonte di verità: a ogni salvataggio il gruppo
dell'utente torna quello del suo ruolo, e lo staff (accesso a /admin/)
spetta solo agli Admin e ai superuser. I permessi Django stanno nei
gruppi, così un Admin gestisce l'admin senza essere superuser.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission

ROLE_GROUP_NAMES = {
    "admin": "Admin",
    "bo_user": "BO User",
    "vendor": "Vendors",
}

# App i cui modelli l'Admin gestisce per intero. Restano fuori auth (gruppi
# e permessi), admin, contenttypes, sessions, authtoken e django_celery_beat:
# li gestisce solo un superuser.
ADMIN_APP_LABELS = (
    "users",
    "vendors",
    "vendors_analysis",
    "purchase_orders",
    "historical_performances",
    "services",
    "competences",
    "portal",
    "documents",
)


def ensure_role_groups():
    """Crea i gruppi dei ruoli e ne allinea i permessi. Idempotente."""
    for label in ADMIN_APP_LABELS:
        # Le permission di ogni app vengono create in post_migrate, in un
        # ordine che qui non controlliamo: le creiamo esplicitamente.
        create_permissions(global_apps.get_app_config(label), verbosity=0)

    for role, name in ROLE_GROUP_NAMES.items():
        group, _ = Group.objects.get_or_create(name=name)
        if role == "admin":
            group.permissions.set(
                Permission.objects.filter(
                    content_type__app_label__in=ADMIN_APP_LABELS
                )
            )
        else:
            group.permissions.clear()
