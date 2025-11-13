import os
import sys
import django
import pandas as pd
from pathlib import Path
from django.db import transaction
from termcolor import colored
import argparse

# --- Setup Django ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vendor_management_system.vendors.models import Vendor, EvaluationCriterion, VendorEvaluation

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
def import_evaluations(file_path=None, sheet_name=None, dry_run=None):
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
    print(colored(f"   Foglio: {sheet_name} | DRY_RUN: {dry_run}", "cyan", attrs=["bold"]))
    print(colored(f"   Righe: {len(df)}\n", "cyan", attrs=["bold"]))

    created_count = updated_count = missing_vendor = 0

    with transaction.atomic():
        for i, row in df.iterrows():
            old_code = safe_str(row.get("old_code"))
            if not old_code:
                print(colored(f"[{i+1}] ⚠️ Riga senza old_code, saltata", "yellow"))
                continue

            vendor = Vendor.objects.filter(old_code=old_code).first()
            if not vendor:
                print(colored(f"[{i+1}] ❌ Vendor non trovato: {old_code}", "red"))
                missing_vendor += 1
                continue

            print(colored(f"\n➡️ {i+1}. Vendor: {vendor.name or old_code}", "cyan"))

            for col, val in row.items():
                if col == "old_code":
                    continue

                score = parse_score(val)
                if score is None:
                    continue

                criterion_code = col.strip().upper()
                criterion = EvaluationCriterion.objects.filter(code=criterion_code).first()

                if not criterion:
                    print(colored(f"   ⚠️ Criterio {criterion_code} non trovato, salto.", "yellow"))
                    continue

                ve, created = VendorEvaluation.objects.update_or_create(
                    vendor=vendor,
                    criterion=criterion,
                    defaults={"score": score, "notes": safe_str(val)},
                )

                if created:
                    created_count += 1
                    print(colored(f"   ✅ Nuova valutazione {criterion.code}: {val}", "green"))
                else:
                    updated_count += 1
                    print(colored(f"   ♻️ Aggiornata {criterion.code}: {val}", "yellow"))

        if dry_run:
            print(colored("\n🧪 DRY RUN attivo: annullo tutte le modifiche", "yellow", attrs=["bold"]))
            transaction.set_rollback(True)

    print(colored("\n✅ Import completato", "cyan", attrs=["bold"]))
    print(colored(f"   Nuove valutazioni: {created_count}", "green"))
    print(colored(f"   Aggiornate: {updated_count}", "yellow"))
    print(colored(f"   Vendor non trovati: {missing_vendor}\n", "red"))


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import valutazioni vendor (VendorEvaluation) da Excel/CSV")
    parser.add_argument("-f", "--file", dest="file_path", default=FILE_PATH, help="Percorso file")
    parser.add_argument("-s", "--sheet", dest="sheet_name", default=SHEET_NAME, help="Indice o nome foglio")
    parser.add_argument("--dry-run", action="store_true", help="Simula senza salvare modifiche")
    args = parser.parse_args()

    import_evaluations(file_path=args.file_path, sheet_name=args.sheet_name, dry_run=args.dry_run)
