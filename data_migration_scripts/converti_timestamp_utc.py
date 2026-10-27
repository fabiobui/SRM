#!/usr/bin/env python
"""
Converte i timestamp (DateTimeField di tutte le app, anche auth/admin/sessioni)
da ora locale naive a UTC naive, nel passaggio di un ambiente da
USE_TZ=False a USE_TZ=True.

Con USE_TZ=False i valori sono salvati nell'ora di TIME_ZONE (Europe/Rome).
Con USE_TZ=True Django li legge come UTC: senza questa conversione tutti i
timestamp risulterebbero spostati di 1-2 ore.

Da lanciare UNA VOLTA per ambiente, con il codice ancora su USE_TZ=False e
l'applicazione ferma (nessuna scrittura concorrente), PRIMA di impostare
USE_TZ=True e riavviare.

- Senza --esegui fa solo il conteggio (sola lettura).
- Con --esegui scrive tutto in un'unica transazione: in caso di errore non
  resta nulla di modificato.
- Registra l'esecuzione in django_migrations: una seconda esecuzione viene
  rifiutata, perché sposterebbe di nuovo i valori. --forza la permette solo
  dopo un ripristino del dump.

Uso (dalla root del repo, dentro la venv, con USE_TZ=False nel .env):
    python data_migration_scripts/converti_timestamp_utc.py
    python data_migration_scripts/converti_timestamp_utc.py --esegui
"""

import argparse
import os
import sys
from datetime import UTC
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402
from django.conf import settings  # noqa: E402
from django.db import connection, models, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

MARKER_APP = "data_migration_scripts"
MARKER_NAME = "0001_converti_timestamp_utc"
BATCH = 500


def gia_eseguito(cursor):
    cursor.execute(
        "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
        [MARKER_APP, MARKER_NAME],
    )
    return cursor.fetchone() is not None


def registra_esecuzione(cursor):
    cursor.execute(
        "INSERT INTO django_migrations (app, name, applied) "
        "VALUES (%s, %s, %s)",
        [MARKER_APP, MARKER_NAME, timezone.now().replace(tzinfo=None)],
    )


def campi_da_convertire():
    """(modello, [campi DateTimeField]) per ogni tabella, una sola volta.
    I modelli proxy condividono la tabella del padre: vanno saltati, altrimenti
    la conversione verrebbe applicata due volte."""
    visti = set()
    risultato = []
    for model in apps.get_models():
        if model._meta.proxy or model._meta.db_table in visti:
            continue
        visti.add(model._meta.db_table)
        campi = [
            f
            for f in model._meta.concrete_fields
            if isinstance(f, models.DateTimeField)
        ]
        if campi:
            risultato.append((model, campi))
    return risultato


def locale_a_utc(valore, fuso):
    """Naive nell'ora di `fuso` -> naive in UTC. Nei cambi d'ora ambigui
    (fine ora legale) vale la prima occorrenza, quella in ora legale."""
    aware = valore.replace(tzinfo=fuso)
    return aware.astimezone(UTC).replace(tzinfo=None)


def converti(fuso, esegui):
    totale_righe = 0
    totale_valori = 0
    for model, campi in campi_da_convertire():
        nomi = [f.attname for f in campi]
        base = model._base_manager
        qs = base.only("pk", *nomi).order_by("pk")
        modifiche = []
        for obj in qs.iterator(chunk_size=BATCH):
            cambiati = False
            for nome in nomi:
                valore = getattr(obj, nome)
                if valore is None:
                    continue
                setattr(obj, nome, locale_a_utc(valore, fuso))
                cambiati = True
                totale_valori += 1
            if cambiati:
                modifiche.append(obj)
        if not modifiche:
            continue
        totale_righe += len(modifiche)
        print(
            f"{model._meta.db_table}: {len(modifiche)} righe, "
            f"campi {', '.join(nomi)}"
        )
        if esegui:
            for i in range(0, len(modifiche), BATCH):
                base.bulk_update(modifiche[i : i + BATCH], nomi)
    return totale_righe, totale_valori


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--esegui",
        action="store_true",
        help="scrive le conversioni (senza, solo conteggio)",
    )
    parser.add_argument(
        "--forza",
        action="store_true",
        help="ignora il registro: solo dopo un ripristino del dump",
    )
    args = parser.parse_args()

    if settings.USE_TZ:
        sys.exit(
            "Interrotto: USE_TZ è True. Lo script va lanciato con "
            "USE_TZ=False nel .env, prima di passare a True."
        )

    fuso = ZoneInfo(settings.TIME_ZONE)
    print(f"Fuso sorgente: {settings.TIME_ZONE}")

    with transaction.atomic():
        with connection.cursor() as cursor:
            if gia_eseguito(cursor) and not args.forza:
                sys.exit(
                    "Interrotto: conversione già registrata in "
                    "django_migrations. Ripristina il dump prima di "
                    "rilanciarla (oppure --forza)."
                )
            righe, valori = converti(fuso, args.esegui)
            if args.esegui:
                registra_esecuzione(cursor)

    print(f"Totale: {righe} righe, {valori} valori convertiti")
    if not args.esegui:
        print("Sola lettura: nulla è stato modificato. Rilancia con --esegui.")


if __name__ == "__main__":
    main()
