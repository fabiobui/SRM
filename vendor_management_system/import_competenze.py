import os
import sys
import django
import pandas as pd
from pathlib import Path
from django.db import transaction
from termcolor import colored
import argparse

# --- Setup Django environment ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vendor_management_system.vendors.models import Vendor, Competence, VendorCompetence


# === CONFIG ===
FILE_PATH = "import_competenze.xlsx"
SHEET_NAME = 0
DRY_RUN = False


# === Helper functions ===
def safe_str(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_bool(value):
    """Riconosce X, YES, TRUE, 1 come True"""
    if pd.isna(value):
        return False
    v = str(value).strip().upper()
    return v in ["SI", "YES", "TRUE", "1", "X", "Y"]


def resolve_file_path(path: str | Path) -> Path | None:
    """Risoluzione percorso file coerente con import_vendors"""
    p = Path(path) if not isinstance(path, Path) else path
    if p.is_absolute() and p.exists():
        return p
    for candidate in [Path.cwd() / p, CURRENT_DIR / p, BASE_DIR / p]:
        if candidate.exists():
            return candidate
    return None


def classify_competence_category(name: str) -> str:
    """Tenta di assegnare la categoria più adatta alla competenza"""
    n = name.upper()
    if any(k in n for k in ["RSPP", "ASPP", "SICUREZZA", "CANTIERE", "ANTINCENDIO"]):
        return "SAFETY"
    if any(k in n for k in ["AUDITOR", "ISO", "SGS", "9001", "14001", "45001", "50001"]):
        return "AUDIT"
    if any(k in n for k in ["ENERGY", "EGE", "MANAGER"]):
        return "ENERGY"
    if any(k in n for k in ["AMBIENTE", "ERGONOMO", "IGIENISTA", "AMIANTO", "ATEX"]):
        return "ENVIRONMENT"
    if any(k in n for k in ["HAZOP", "SIL", "QRA", "FERA", "SAFETY EXPERT"]):
        return "TECHNICAL"
    return "OTHER"


# === MAIN FUNCTION ===
@transaction.atomic
def import_competences(file_path: str | Path | None = None, sheet_name=None, dry_run: bool | None = None):
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

    print(colored(f"\n📘 Import competenze da: {resolved_path}", "cyan"))
    print(colored(f"   Foglio: {sheet_name} | DRY_RUN: {dry_run}", "cyan", attrs=["bold"]))
    print(colored(f"   Righe: {len(df)}\n", "cyan", attrs=["bold"]))

    created_vendor_competences = 0
    missing_vendors = 0
    created_competences = 0

    with transaction.atomic():
        for i, row in df.iterrows():
            old_code = safe_str(row.get("old_code"))
            if not old_code:
                print(colored(f"[{i+1}] ⚠️ Riga senza old_code, saltata", "yellow"))
                continue

            vendor = Vendor.objects.filter(old_code=old_code).first()
            if not vendor:
                print(colored(f"[{i+1}] ❌ Vendor non trovato: {old_code}", "red"))
                missing_vendors += 1
                continue

            print(colored(f"\n➡️ {i+1}. Vendor: {vendor.name or old_code}", "cyan"))

            for col, val in row.items():
                if col == "old_code":
                    continue
                if not parse_bool(val):
                    continue

                comp_name = col.strip()
                comp_code = comp_name.upper().replace(" ", "_").replace("/", "_").replace("-", "_")
                category = classify_competence_category(comp_name)

                comp, created = Competence.objects.get_or_create(
                    code=comp_code,
                    defaults={
                        "name": comp_name,
                        "competence_category": category,
                        "is_active": True,
                        "requires_certification": True,
                    },
                )
                if created:
                    created_competences += 1
                    print(colored(f"   🆕 Creata competenza: {comp.name}", "green"))

                vc, created_vc = VendorCompetence.objects.get_or_create(
                    vendor=vendor,
                    competence=comp,
                    defaults={"has_competence": True, "verified": False},
                )
                if created_vc:
                    created_vendor_competences += 1
                    print(colored(f"   ✅ Assegnata: {comp.name}", "yellow"))
                else:
                    print(colored(f"   ↪️ Già presente: {comp.name}", "white"))

        if dry_run:
            print(colored("\n🧪 DRY RUN: annullo tutte le modifiche", "yellow", attrs=["bold"]))
            transaction.set_rollback(True)

    print(colored("\n✅ Import completato", "cyan", attrs=["bold"]))
    print(colored(f"   VendorCompetence create: {created_vendor_competences}", "green"))
    print(colored(f"   Competenze nuove: {created_competences}", "green"))
    print(colored(f"   Vendor non trovati: {missing_vendors}\n", "red"))


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import competenze vendor da Excel/CSV")
    parser.add_argument("-f", "--file", dest="file_path", default=FILE_PATH, help="Percorso file")
    parser.add_argument("-s", "--sheet", dest="sheet_name", default=SHEET_NAME, help="Indice o nome foglio")
    parser.add_argument("--dry-run", action="store_true", help="Esegue simulazione senza salvare")
    args = parser.parse_args()

    import_competences(file_path=args.file_path, sheet_name=args.sheet_name, dry_run=args.dry_run)
