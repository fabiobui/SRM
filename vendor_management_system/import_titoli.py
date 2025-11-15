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

from vendor_management_system.vendors.models import QualificationType

# === CONFIG DEFAULT ===
FILE_PATH = "titoli.xlsx"
SHEET_NAME = 0
DRY_RUN = False


def resolve_file_path(path: str | Path) -> Path | None:
    """Risoluzione smart del path"""
    p = Path(path) if not isinstance(path, Path) else path
    if p.is_absolute() and p.exists():
        return p
    for candidate in [Path.cwd() / p, CURRENT_DIR / p, BASE_DIR / p]:
        if candidate.exists():
            return candidate
    return None


def safe_str(value):
    """Gestisce None e NaN"""
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_bool(value, default=True):
    """Supporta vari formati booleani"""
    if pd.isna(value) or value is None or str(value).strip() == "":
        return default

    v = str(value).strip().lower()
    if v in ["1", "true", "t", "yes", "y", "si", "s"]:
        return True
    if v in ["0", "false", "f", "no", "n"]:
        return False
    return default


def parse_int(value, default=100):
    try:
        return int(float(value))
    except Exception:
        return default


@transaction.atomic
def import_qualification_types(file_path=None, sheet_name=None, dry_run=None):
    """Importa titoli di studio PADRI e FIGLI, gestendo la gerarchia"""
    file_path = file_path or FILE_PATH
    sheet_name = sheet_name or SHEET_NAME
    dry_run = dry_run if dry_run is not None else DRY_RUN

    resolved_path = resolve_file_path(file_path)
    if not resolved_path:
        print(colored(f"❌ File non trovato: {file_path}", "red"))
        sys.exit(1)

    # Carica XLSX o CSV
    ext = resolved_path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(resolved_path, dtype=str)
    else:
        df = pd.read_excel(resolved_path, sheet_name=sheet_name, dtype=str)

    print(colored(f"\n📘 Import Titoli da: {resolved_path}", "cyan"))
    print(colored(f"   Foglio: {sheet_name} | DRY_RUN: {dry_run}", "cyan", attrs=["bold"]))
    print(colored(f"   Righe: {len(df)}\n", "cyan", attrs=["bold"]))

    # Normalizza nomi colonne
    df.columns = [c.lower() for c in df.columns]

    required_columns = {"code", "name"}
    if not required_columns.issubset(df.columns):
        print(colored(f"❌ Mancano colonne obbligatorie: {required_columns - set(df.columns)}", "red"))
        sys.exit(1)

    created_count = updated_count = skipped = 0

    with transaction.atomic():

        for i, row in df.iterrows():
            row = {k.lower(): v for k, v in row.items()}

            code = safe_str(row.get("code"))
            if not code:
                print(colored(f"[{i+1}] ⚠️ Riga senza CODE, saltata", "yellow"))
                skipped += 1
                continue

            name = safe_str(row.get("name")) or code
            description = safe_str(row.get("description")) or None
            level = safe_str(row.get("level")) or None
            sort_order = parse_int(row.get("sort_order", 100))
            is_active = parse_bool(row.get("is_active", True))

            # Gestione parent
            parent_code = safe_str(row.get("parent_code")) or None
            parent_obj = None

            if parent_code:
                parent_obj = QualificationType.objects.filter(code=parent_code).first()
                if not parent_obj:
                    print(colored(f"[{i+1}] ❌ Parent non trovato: {parent_code}", "red"))
                    skipped += 1
                    continue

            defaults = {
                "name": name,
                "description": description,
                "level": level,
                "sort_order": sort_order,
                "is_active": is_active,
                "parent": parent_obj,
            }

            obj, created = QualificationType.objects.update_or_create(
                code=code,
                defaults=defaults,
            )

            if created:
                created_count += 1
                print(colored(f"[{i+1}] ✅ Creato: {code} - {name}", "green"))
            else:
                updated_count += 1
                print(colored(f"[{i+1}] ♻️ Aggiornato: {code} - {name}", "yellow"))

        if dry_run:
            print(colored("\n🧪 DRY RUN: rollback attivato", "yellow", attrs=["bold"]))
            transaction.set_rollback(True)

    print(colored("\n🎉 IMPORT COMPLETATO", "cyan", attrs=["bold"]))
    print(colored(f"   ➕ Creati: {created_count}", "green"))
    print(colored(f"   🔁 Aggiornati: {updated_count}", "yellow"))
    print(colored(f"   ⚠️ Saltati: {skipped}\n", "red"))


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Titoli di Studio (QualificationType)")
    parser.add_argument("-f", "--file", dest="file_path", default=FILE_PATH, help="File XLSX o CSV")
    parser.add_argument("-s", "--sheet", dest="sheet_name", default=SHEET_NAME, help="Foglio XLSX")
    parser.add_argument("--dry-run", action="store_true", help="Simula senza salvare")
    args = parser.parse_args()

    import_qualification_types(
        file_path=args.file_path,
        sheet_name=args.sheet_name,
        dry_run=args.dry_run,
    )
