#!/usr/bin/env python
"""
Riallinea la migrazione documents.0006_documentset con lo stato reale del DB.

Contesto: in produzione la tabella `documents_documentset` esiste già ma la
migrazione 0006 non risulta applicata, quindi `migrate` fallisce con
(1050, "Table 'documents_documentset' already exists").

Lo script è IDEMPOTENTE e non distruttivo salvo un caso esplicito e sicuro
(tabella parziale e VUOTA). Decide da solo il da farsi:

  - 0006 già applicata            -> nulla da fare.
  - 0006 non applicata, nessuna
    tabella                       -> nessun intervento (migrate la creerà).
  - 0006 non applicata, tabella
    principale + tabella ponte     -> --fake della 0006 (schema già completo).
  - 0006 non applicata, solo la
    tabella principale e VUOTA     -> DROP della tabella (la ricreerà migrate).
  - 0006 non applicata, solo la
    tabella principale con DATI    -> si ferma e chiede intervento manuale.

Uso (sul server, dentro la venv):
    python fix_documentset_migration.py            # esegue
    python fix_documentset_migration.py --dry-run  # mostra solo la diagnosi

Dopo l'esecuzione lancia comunque:
    python manage.py migrate
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db.migrations.recorder import MigrationRecorder  # noqa: E402

APP = "documents"
MIGRATION = "0006_documentset"
MAIN_TABLE = "documents_documentset"
M2M_TABLE = "documents_documentset_document_types"

DRY_RUN = "--dry-run" in sys.argv


def log(msg):
    print(f"[fix-documentset] {msg}")


def migration_applied():
    recorder = MigrationRecorder(connection)
    applied = recorder.applied_migrations()  # set di (app, name)
    return (APP, MIGRATION) in applied


def table_exists(name):
    return name in connection.introspection.table_names()


def table_is_empty(name):
    with connection.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM `{name}`")
        return cur.fetchone()[0] == 0


def main():
    log(f"DB: {connection.settings_dict.get('NAME')} @ "
        f"{connection.settings_dict.get('HOST') or 'localhost'}")
    log(f"Modalità: {'DRY-RUN (nessuna modifica)' if DRY_RUN else 'ESECUZIONE'}")

    applied = migration_applied()
    has_main = table_exists(MAIN_TABLE)
    has_m2m = table_exists(M2M_TABLE)

    log(f"Migrazione {APP}.{MIGRATION} applicata: {applied}")
    log(f"Tabella {MAIN_TABLE} presente: {has_main}")
    log(f"Tabella {M2M_TABLE} presente: {has_m2m}")

    if applied:
        log("Nulla da fare: la migrazione risulta già applicata.")
        return 0

    if not has_main and not has_m2m:
        log("Nessuna tabella presente: nessun intervento, "
            "`manage.py migrate` la creerà normalmente.")
        return 0

    if has_main and has_m2m:
        log("Schema già completo nel DB ma migrazione non registrata "
            "=> segno la 0006 come applicata (--fake).")
        if DRY_RUN:
            log("DRY-RUN: avrei eseguito `migrate documents 0006 --fake`.")
            return 0
        call_command("migrate", APP, MIGRATION, fake=True, verbosity=1)
        log("Fatto. Ora esegui: python manage.py migrate")
        return 0

    if has_main and not has_m2m:
        empty = table_is_empty(MAIN_TABLE)
        log(f"Solo tabella principale presente (creazione parziale). "
            f"Tabella vuota: {empty}")
        if not empty:
            log("STOP: la tabella contiene dati e manca la tabella ponte M2M. "
                "Non eseguo DROP automatico. Serve intervento manuale "
                "(fake 0006 + creazione manuale di "
                f"{M2M_TABLE}). Contatta lo sviluppatore.")
            return 2
        log("Tabella vuota: elimino la tabella parziale così `migrate` "
            "ricrea tabella e tabella ponte correttamente.")
        if DRY_RUN:
            log(f"DRY-RUN: avrei eseguito `DROP TABLE {MAIN_TABLE}` + "
                f"`migrate {APP}`.")
            return 0
        with connection.cursor() as cur:
            cur.execute(f"DROP TABLE `{MAIN_TABLE}`")
        log(f"Tabella {MAIN_TABLE} eliminata. Applico la migrazione {APP}...")
        call_command("migrate", APP, verbosity=1)
        log("Fatto.")
        return 0

    # Caso residuo: solo tabella ponte senza principale (anomalo).
    log("Stato anomalo (solo tabella ponte presente). Intervento manuale "
        "necessario.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
