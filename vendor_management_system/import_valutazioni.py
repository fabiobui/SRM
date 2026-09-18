import argparse
import os
import re
import sys
from pathlib import Path

import django
import pandas as pd
from django.db import transaction
from termcolor import colored

# --- Setup Django ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vendor_management_system.vendors.models import (  # noqa: E402
    EvaluationCriterion,
    Vendor,
    VendorEvaluation,
)

# === CONFIG ===
FILE_PATH = "import_valutazioni.xlsx"
SHEET_NAME = 0
DRY_RUN = False

# === Mapping qualitativo -> punteggio numerico ===
SCORE_MAP = {
    "SCARSO": 1,
    "INSUFFICIENTE": 2,
    "NON SUFFICIENTE": 3,
    "AL LIMITE DELLA SUFFICIENZA": 4,
    "SUFFICIENTE": 5,
    "BUONO": 6,
    "OTTIMO": 7,
    "ECCELLENTE": 8,
}


def albo_row_from_code(code):
    """Riga del foglio Albo a partire dal codice provvisorio: XLS0001 -> 2.

    I codici XLS sono progressivi sulle righe del file Albo, che ha
    l'intestazione in riga 1: il fornitore XLS0001 sta quindi in riga 2.
    """
    m = re.match(r"^XLS0*(\d+)$", str(code or "").strip().upper())
    return int(m.group(1)) + 1 if m else None


def build_vendor_index():
    """Indici dei fornitori per Codice Embyon e per Riga excel Albo
    Fornitore."""
    by_code, by_row = {}, {}
    for v in Vendor.objects.only("pk", "old_code", "albo_excel_row", "name"):
        if v.old_code:
            by_code[v.old_code.strip().upper()] = v
        if v.albo_excel_row:
            by_row[v.albo_excel_row] = v
    return by_code, by_row


def resolve_vendor(value, by_code, by_row, key="auto"):
    """Trova il fornitore dalla colonna chiave del file.

    Il codice dell'Albo (XLS0001) finisce in ``old_code``, che però viene
    sostituito dal codice Embyon da import_embyon_codes: dopo quel passaggio
    l'unico aggancio stabile al file è ``albo_excel_row``. Per questo, per i
    codici XLS, la riga viene provata per prima.
    Ritorna (vendor, criterio usato).
    """
    key_value = str(value or "").strip().upper()
    riga = albo_row_from_code(key_value)
    if key_value.isdigit():  # la colonna porta direttamente la riga
        riga = int(key_value)

    if key != "old_code" and riga and riga in by_row:
        return by_row[riga], f"riga Albo {riga}"
    if key != "albo_row":
        vendor = by_code.get(key_value)
        if vendor:
            return vendor, "Codice Embyon"
    return None, None


def resolve_file_path(path: str | Path) -> Path | None:
    p = Path(path) if not isinstance(path, Path) else path
    if p.is_absolute() and p.exists():
        return p
    for candidate in [Path.cwd() / p, CURRENT_DIR / p, BASE_DIR / p]:
        if candidate.exists():
            return candidate
    return None


def safe_str(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_score(value):
    if pd.isna(value) or not str(value).strip():
        return None
    v = str(value).strip().upper()
    for key, val in SCORE_MAP.items():
        if key in v:
            return val
    return None  # ignora valori non riconosciuti


@transaction.atomic
def import_evaluations(
    file_path=None, sheet_name=None, dry_run=None, key="auto"
):
    file_path = file_path or FILE_PATH
    sheet_name = sheet_name or SHEET_NAME
    dry_run = dry_run if dry_run is not None else DRY_RUN

    resolved_path = resolve_file_path(file_path)
    if not resolved_path:
        print(colored(f"❌ File non trovato: {file_path}", "red"))
        sys.exit(1)

    ext = resolved_path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(resolved_path, dtype=str)
    else:
        df = pd.read_excel(resolved_path, sheet_name=sheet_name, dtype=str)

    print(colored(f"\n📊 Import valutazioni da: {resolved_path}", "cyan"))
    print(
        colored(
            f"   Foglio: {sheet_name} | DRY_RUN: {dry_run}",
            "cyan",
            attrs=["bold"],
        )
    )
    print(colored(f"   Righe: {len(df)}\n", "cyan", attrs=["bold"]))

    created_count = updated_count = missing_vendor = 0

    by_vendor_code, by_vendor_row = build_vendor_index()

    with transaction.atomic():
        for i, row in df.iterrows():
            old_code = safe_str(row.get("old_code"))
            if not old_code:
                print(
                    colored(
                        f"[{i + 1}] ⚠️ Riga senza old_code, saltata", "yellow"
                    )
                )
                continue

            vendor, criterio = resolve_vendor(
                old_code, by_vendor_code, by_vendor_row, key
            )
            if not vendor:
                print(
                    colored(
                        f"[{i + 1}] ❌ Vendor non trovato: {old_code}", "red"
                    )
                )
                missing_vendor += 1
                continue

            print(
                colored(
                    f"\n➡️ {i + 1}. Vendor: {vendor.name or old_code} "
                    f"[{old_code} → {criterio}]",
                    "cyan",
                )
            )

            for col, val in row.items():
                if col == "old_code":
                    continue

                score = parse_score(val)
                if score is None:
                    continue

                criterion_code = col.strip().upper()
                criterion = EvaluationCriterion.objects.filter(
                    code=criterion_code
                ).first()

                if not criterion:
                    print(
                        colored(
                            f"   ⚠️ Criterio {criterion_code} non trovato, "
                            "salto.",
                            "yellow",
                        )
                    )
                    continue

                ve, created = VendorEvaluation.objects.update_or_create(
                    vendor=vendor,
                    criterion=criterion,
                    defaults={"score": score, "notes": safe_str(val)},
                )

                if created:
                    created_count += 1
                    print(
                        colored(
                            f"   ✅ Nuova valutazione {criterion.code}: {val}",
                            "green",
                        )
                    )
                else:
                    updated_count += 1
                    print(
                        colored(
                            f"   ♻️ Aggiornata {criterion.code}: {val}",
                            "yellow",
                        )
                    )

        if dry_run:
            print(
                colored(
                    "\n🧪 DRY RUN attivo: annullo tutte le modifiche",
                    "yellow",
                    attrs=["bold"],
                )
            )
            transaction.set_rollback(True)

    print(colored("\n✅ Import completato", "cyan", attrs=["bold"]))
    print(colored(f"   Nuove valutazioni: {created_count}", "green"))
    print(colored(f"   Aggiornate: {updated_count}", "yellow"))
    print(colored(f"   Vendor non trovati: {missing_vendor}\n", "red"))


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import valutazioni vendor (VendorEvaluation) da Excel/CSV"
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file_path",
        default=FILE_PATH,
        help="Percorso file",
    )
    parser.add_argument(
        "-s",
        "--sheet",
        dest="sheet_name",
        default=SHEET_NAME,
        help="Indice o nome foglio",
    )
    parser.add_argument(
        "--key",
        choices=["auto", "albo_row", "old_code"],
        default="auto",
        help="Come agganciare il fornitore: auto (riga Albo per i codici XLS, "
        "poi Codice Embyon), solo riga Albo, solo Codice Embyon",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simula senza salvare modifiche"
    )
    args = parser.parse_args()

    import_evaluations(
        file_path=args.file_path,
        sheet_name=args.sheet_name,
        dry_run=args.dry_run,
        key=args.key,
    )
