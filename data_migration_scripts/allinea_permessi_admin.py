#!/usr/bin/env python
"""
Riporta i permessi admin di gruppi e utenti sui nuovi nomi dei modelli.
Da lanciare UNA VOLTA per ambiente, DOPO `manage.py migrate`.

Due cambi di master tolgono l'accesso a utenti staff non superuser che prima
lo avevano:

- `documents/0007` rinomina DocumentType in DocumentCatalog: il content type
  segue la rinomina, ma i codename dei permessi restano `*_documenttype`,
  mentre l'admin controlla `*_documentcatalog`;
- le sezioni Servizi e Requisiti dell'admin sono modelli proxy (app
  `services` e `competences`) con permessi propri, che nessuno possiede.

Chi ha un permesso sul modello di origine riceve lo stesso permesso (stessa
azione: add/change/delete/view) sul modello nuovo. Non toglie mai nulla.

È IDEMPOTENTE. Con --dry-run esegue tutto e annulla la transazione.

Uso (dalla root del repo, dentro la venv):
    python data_migration_scripts/allinea_permessi_admin.py --dry-run
    python data_migration_scripts/allinea_permessi_admin.py
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.contrib.auth.management import create_permissions  # noqa: E402
from django.contrib.auth.models import Group, Permission  # noqa: E402
from django.db import transaction  # noqa: E402

from vendor_management_system.users.models import User  # noqa: E402

# (app, modello di origine) -> (app, modello nuovo)
MAPPA = {
    ("documents", "documenttype"): ("documents", "documentcatalog"),
    ("vendors", "servicetype"): ("services", "servicecatalog"),
    ("vendors", "serviceset"): ("services", "serviceset"),
    ("vendors", "vendorservice"): ("services", "service"),
    ("vendors", "competence"): ("competences", "competencecatalog"),
    ("vendors", "vendorcompetence"): ("competences", "competence"),
    ("vendors", "competenceset"): ("competences", "competenceset"),
}
AZIONI = ("add", "change", "delete", "view")


def log(msg):
    print(f"[permessi-admin] {msg}")


def _permesso(app, codename):
    return Permission.objects.filter(
        content_type__app_label=app, codename=codename
    ).first()


def coppie_permessi():
    """Coppie (permesso di origine, permesso nuovo) esistenti a DB."""
    coppie = []
    for (app_da, modello_da), (app_a, modello_a) in MAPPA.items():
        for azione in AZIONI:
            origine = _permesso(app_da, f"{azione}_{modello_da}")
            nuovo = _permesso(app_a, f"{azione}_{modello_a}")
            if origine and nuovo:
                coppie.append((origine, nuovo))
            elif not nuovo:
                log(f"Permesso mancante: {app_a}.{azione}_{modello_a}")
    return coppie


def allinea(titolari, campo, descrivi, coppie):
    """Aggiunge il permesso nuovo a chi ha quello di origine."""
    aggiunti = 0
    for origine, nuovo in coppie:
        filtro = {campo: origine}
        for titolare in titolari.filter(**filtro).exclude(**{campo: nuovo}):
            getattr(titolare, campo).add(nuovo)
            aggiunti += 1
            log(
                f"{descrivi(titolare)}: + {nuovo.content_type.app_label}."
                f"{nuovo.codename}"
            )
    return aggiunti


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="esegue tutto e annulla la transazione",
    )
    args = parser.parse_args()

    modalita = "DRY-RUN (nessuna modifica)" if args.dry_run else "ESECUZIONE"
    log(f"Modalità: {modalita}")

    with transaction.atomic():
        # Normalmente li crea già il post_migrate: qui solo per sicurezza.
        for app_label in ("documents", "services", "competences"):
            create_permissions(apps.get_app_config(app_label), verbosity=0)

        coppie = coppie_permessi()
        gruppi = allinea(
            Group.objects.all(),
            "permissions",
            lambda g: f"Gruppo '{g.name}'",
            coppie,
        )
        utenti = allinea(
            User.objects.all(),
            "user_permissions",
            lambda u: f"Utente {u.email}",
            coppie,
        )

        if args.dry_run:
            transaction.set_rollback(True)
            log("DRY-RUN: modifiche annullate.")

    log(f"Permessi aggiunti: {gruppi} a gruppi, {utenti} a utenti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
