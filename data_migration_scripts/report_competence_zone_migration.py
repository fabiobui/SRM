#!/usr/bin/env python
"""
Report del travaso delle vecchie zone di competenza.

Mostra, fornitore per fornitore, cosa la data migration
`vendors/0043_migrate_competence_zones` riesce a interpretare e cosa no,
partendo dalle due sorgenti legacy: le `CompetenceZone` assegnate e il
vecchio campo testuale libero `Vendor.competences_zone`.

PERCHE' UNO SCRIPT E NON UN PEZZO DELLA MIGRAZIONE:
- `migrate` gira a ogni deploy da `compose/django/start`, con
  `set -o errexit`: un errore di I/O nello scrivere il CSV farebbe
  fallire il deploy per colpa di un report;
- `docker compose exec django pytest` rigioca tutta la cronologia delle
  migrazioni, quindi il report verrebbe riscritto a ogni run della suite;
- il momento utile per guardarlo e' PRIMA di migrare, finche' il testo
  originale esiste ancora: se i "NESSUN_MATCH" sono tanti conviene
  estendere gli alias invece di ritrovarsi la dashboard piena di
  "Non specificato".

PERCHE' SQL DIRETTO E NON L'ORM: i modelli `CompetenceZone` e i campi
legacy di `Vendor` sono stati rimossi dal codice (migrazione 0044), ma le
colonne restano nel database finche' quella migrazione non viene
applicata. Lo script deve poter leggere proprio quel momento intermedio,
quindi interroga le tabelle direttamente. Se le tabelle non esistono piu'
lo dice e si ferma, senza errori criptici.

Il report puo' contenere dati fornitore (ragioni sociali), per questo
finisce in `data_migration_scripts/reports/`, che NON e' servita da
Django a differenza di `static/`.

Lo script e' di sola lettura: non scrive mai sul database.

ESEMPI (dalla root del repo, dentro la venv):
    python data_migration_scripts/report_competence_zone_migration.py
    python data_migration_scripts/report_competence_zone_migration.py \
        --report /percorso/mio.csv
"""

import argparse
import csv
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402

migrazione = importlib.import_module(
    "vendor_management_system.vendors.migrations.0043_migrate_competence_zones"
)

REPORT_DEFAULT = (
    Path(__file__).resolve().parent
    / "reports"
    / "competence_zone_migration.csv"
)

TABELLA_ZONE = "vendors_competencezone"
TABELLA_REGOLE = "vendors_competencezonerule"
TABELLA_LEGAME = "vendors_vendor_competence_zones"

COLONNE = [
    "vendor_code",
    "name",
    "zone_assegnate",
    "province_da_zone",
    "testo_libero",
    "token_riconosciuti",
    "token_non_riconosciuti",
    "province_totali",
    "nazioni_estere",
    "esito",
]


def _righe(sql, parametri=None):
    with connection.cursor() as cursore:
        cursore.execute(sql, parametri or [])
        return cursore.fetchall()


def _tabelle_legacy_presenti():
    esistenti = set(connection.introspection.table_names())
    return {TABELLA_ZONE, TABELLA_REGOLE, TABELLA_LEGAME} <= esistenti


def _carica_indice():
    """Indice dei nomi canonici dal catalogo geografico (3 query)."""
    return migrazione.costruisci_indice(
        _righe("SELECT code, name FROM vendors_country"),
        _righe(
            "SELECT r.code, r.name, c.code FROM vendors_region r "
            "JOIN vendors_country c ON c.id = r.country_id"
        ),
        _righe(
            "SELECT p.code, p.name, r.code FROM vendors_province p "
            "JOIN vendors_region r ON r.id = p.region_id"
        ),
    )


def _carica_regole():
    """Regole INCLUDE/EXCLUDE, raggruppate per zona."""
    righe = _righe(
        f"SELECT rl.zone_id, rl.rule_type, c.code, r.code, p.code "
        f"FROM {TABELLA_REGOLE} rl "
        "LEFT JOIN vendors_country c ON c.id = rl.country_id "
        "LEFT JOIN vendors_region r ON r.id = rl.region_id "
        "LEFT JOIN vendors_province p ON p.id = rl.province_id"
    )
    per_zona = {}
    for zona_id, tipo, naz, reg, prov in righe:
        per_zona.setdefault(zona_id, []).append((tipo, naz, reg, prov))
    return per_zona


def _carica_zone_per_vendor():
    """Nomi e id delle zone assegnate, per fornitore."""
    righe = _righe(
        f"SELECT l.vendor_id, z.id, z.name "
        f"FROM {TABELLA_LEGAME} l "
        f"JOIN {TABELLA_ZONE} z ON z.id = l.competencezone_id"
    )
    per_vendor = {}
    for vendor_id, zona_id, nome in righe:
        per_vendor.setdefault(vendor_id, []).append((zona_id, nome))
    return per_vendor


def _esito(da_zone, da_testo, non_riconosciuti, aveva_zone, aveva_testo):
    if not aveva_zone and not aveva_testo:
        return "VUOTO"
    if not da_zone and not da_testo:
        return "NESSUN_MATCH"
    if non_riconosciuti:
        return "PARZIALE"
    if da_zone and da_testo:
        return "OK_MISTO"
    return "OK_ZONA" if da_zone else "OK_TESTO"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Simula il travaso delle zone di competenza e scrive un CSV "
            "di esito. Non modifica il database."
        )
    )
    parser.add_argument(
        "--report",
        default=str(REPORT_DEFAULT),
        help=f"Percorso del CSV di esito (default: {REPORT_DEFAULT})",
    )
    argomenti = parser.parse_args()

    if not _tabelle_legacy_presenti():
        print(
            "Le tabelle delle vecchie zone di competenza non esistono piu': "
            "la migrazione 0044_remove_competence_zone_stack e' gia' stata "
            "applicata su questo database. Non c'e' nulla da riportare."
        )
        return

    indice = _carica_indice()
    regole_per_zona = _carica_regole()
    zone_per_vendor = _carica_zone_per_vendor()

    percorso = Path(argomenti.report)
    percorso.parent.mkdir(parents=True, exist_ok=True)

    conteggi = {}
    fornitori = _righe(
        "SELECT vendor_code, name, competences_zone FROM vendors_vendor"
    )

    with percorso.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(COLONNE)

        for vendor_code, nome, testo_grezzo in fornitori:
            testo = (testo_grezzo or "").strip()
            zone = zone_per_vendor.get(vendor_code, [])

            regole = []
            for zona_id, _nome_zona in zone:
                regole.extend(regole_per_zona.get(zona_id, []))
            province_zone, nazioni_zone = migrazione.espandi_zone(
                regole, indice
            )
            (
                province_testo,
                nazioni_testo,
                riconosciuti,
                non_riconosciuti,
            ) = migrazione.match_testo(testo, indice)

            province = province_zone | province_testo
            nazioni = nazioni_zone | nazioni_testo
            esito = _esito(
                province_zone or nazioni_zone,
                province_testo or nazioni_testo,
                non_riconosciuti,
                bool(zone),
                bool(testo),
            )
            conteggi[esito] = conteggi.get(esito, 0) + 1

            if esito == "VUOTO":
                continue

            writer.writerow(
                [
                    vendor_code,
                    nome,
                    " | ".join(n for _id, n in zone),
                    len(province_zone),
                    testo,
                    " | ".join(riconosciuti),
                    " | ".join(non_riconosciuti),
                    len(province),
                    ", ".join(sorted(nazioni)),
                    esito,
                ]
            )

    totale = sum(conteggi.values())
    con_dati = totale - conteggi.get("VUOTO", 0)
    da_sistemare = conteggi.get("NESSUN_MATCH", 0) + conteggi.get(
        "PARZIALE", 0
    )

    print(f"Report scritto in: {percorso}")
    print(f"Fornitori esaminati: {totale} (con dati legacy: {con_dati})")
    for esito in sorted(conteggi):
        print(f"  {esito}: {conteggi[esito]}")

    if con_dati and da_sistemare / con_dati > 0.3:
        print(
            "\nATTENZIONE: oltre il 30% dei fornitori con dati legacy non "
            "e' stato interpretato del tutto. Conviene estendere gli alias "
            "in vendors/migrations/0043_migrate_competence_zones.py prima "
            "di migrare in produzione."
        )


if __name__ == "__main__":
    main()
