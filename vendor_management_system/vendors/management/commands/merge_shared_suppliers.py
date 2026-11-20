"""Accorpa i fornitori censiti più volte (uno per società) per codice SAGE.

Di default è una simulazione: scrive solo i report CSV in
``data_migration_scripts/reports/`` (merge_report.csv, merge_skipped.csv,
embyon_codes_not_in_views.csv). Con ``--apply`` esegue l'accorpamento.

Uso:
    python manage.py merge_shared_suppliers
    python manage.py merge_shared_suppliers --apply
    python manage.py merge_shared_suppliers --apply --sage-code 000011
    python manage.py merge_shared_suppliers --apply --survivor-map mappa.csv

``--survivor-map``: CSV ``sage_code;vendor_code`` per imporre il superstite
di un gruppo invece di quello con la modifica più recente.
"""

import csv

from django.core.management.base import BaseCommand

from vendor_management_system.vendors import fabric_hub
from vendor_management_system.vendors.supplier_merge import (
    REPORTS_DIR,
    merge_shared_suppliers,
    write_reports,
)


class Command(BaseCommand):
    help = (
        "Accorpa per codice SAGE i fornitori già censiti per più società "
        "(simulazione senza --apply)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Esegue l'accorpamento (senza: solo simulazione e report).",
        )
        parser.add_argument("--sage-code", help="Solo questo codice SAGE.")
        parser.add_argument(
            "--survivor-map",
            help="CSV sage_code;vendor_code con il superstite imposto.",
        )

    def handle(self, *args, **options):
        survivor_map = {}
        if options["survivor_map"]:
            with open(options["survivor_map"], encoding="utf-8") as f:
                for row in csv.reader(f, delimiter=";"):
                    if len(row) >= 2 and row[0] and row[1]:
                        survivor_map[row[0].strip()] = row[1].strip()
        rows = [
            fabric_hub.normalize_company_row(r)
            for r in fabric_hub.all_supplier_companies()
        ]
        summary = merge_shared_suppliers(
            rows,
            apply=options["apply"],
            survivor_map=survivor_map,
            only_sage=options["sage_code"],
            backup_dir=REPORTS_DIR / "merge_backup",
        )
        write_reports(summary)
        for entry in summary["merged"]:
            donors = ", ".join(f"{d.pk} {d.name}" for d in entry["donors"])
            self.stdout.write(
                f"SAGE {entry['sage']}: superstite {entry['survivor'].pk} "
                f"{entry['survivor'].name} <- {donors}"
            )
        for sage, vendors, reason in summary["skipped"]:
            codes = ", ".join(v.pk for v in vendors)
            self.stdout.write(f"SAGE {sage} saltato ({reason}): {codes}")
        reasons = {}
        for _vendor, reason, _detail in summary["unmatched"]:
            reasons[reason] = reasons.get(reason, 0) + 1
        verb = "accorpati" if options["apply"] else "da accorpare"
        self.stdout.write(
            self.style.SUCCESS(
                f"Gruppi {verb}: {len(summary['merged'])}; saltati: "
                f"{len(summary['skipped'])}; collegati al SAGE: "
                f"{len(summary['linked'])}; non agganciati: "
                f"{len(summary['unmatched'])} {reasons}. Report in "
                f"{REPORTS_DIR}."
            )
        )
