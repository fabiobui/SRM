import os
import sys
import django
import pandas as pd
from pathlib import Path
from django.db import transaction
from termcolor import colored
import argparse
from datetime import datetime

# --- Setup Django ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vendor_management_system.vendors.models import Vendor, DocumentType, VendorDocument


# === CONFIG ===
FILE_PATH = "import_sa8000.xlsx"
SHEET_NAME = 0
DRY_RUN = False


# === Helper ===
def safe_str(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_date(value):
    if pd.isna(value) or not str(value).strip():
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except Exception:
            continue
    return None


def parse_bool(value):
    if pd.isna(value):
        return False
    v = str(value).strip().upper()
    return v in ["SI", "YES", "TRUE", "1", "X", "Y"]


def resolve_file_path(path: str | Path) -> Path | None:
    p = Path(path) if not isinstance(path, Path) else path
    if p.is_absolute() and p.exists():
        return p
    for candidate in [Path.cwd() / p, CURRENT_DIR / p, BASE_DIR / p]:
        if candidate.exists():
            return candidate
    return None


# === MAIN ===
@transaction.atomic
def import_documents(file_path=None, sheet_name=None, dry_run=None):
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

    print(colored(f"\n📄 Import documenti da: {resolved_path}", "cyan"))
    print(colored(f"   Foglio: {sheet_name} | DRY_RUN: {dry_run}", "cyan", attrs=["bold"]))
    print(colored(f"   Righe: {len(df)}\n", "cyan", attrs=["bold"]))

    created_docs = updated_docs = missing_vendor = 0

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

                value = safe_str(val)
                if not value:
                    continue

                doc_type = DocumentType.objects.filter(code__iexact=col.strip()).first()
                if not doc_type:
                    print(colored(f"   ⚠️ Tipo documento {col} non trovato, salto", "yellow"))
                    continue

                # Rileva tipo di valore
                if parse_bool(value):
                    status = "APPROVED"
                elif parse_date(value):
                    status = "APPROVED"
                else:
                    status = "SUBMITTED"

                expiry_date = parse_date(value)

                vd, created = VendorDocument.objects.update_or_create(
                    vendor=vendor,
                    document_type=doc_type,
                    defaults=dict(
                        status=status,
                        verified=False,
                        expiry_date=expiry_date,
                        notes=value if not expiry_date else None,
                    ),
                )

                if created:
                    created_docs += 1
                    print(colored(f"   ✅ Nuovo documento: {doc_type.code} ({value})", "green"))
                else:
                    updated_docs += 1
                    print(colored(f"   ♻️ Aggiornato: {doc_type.code} ({value})", "yellow"))

        if dry_run:
            print(colored("\n🧪 DRY RUN: annullo tutte le modifiche", "yellow", attrs=["bold"]))
            transaction.set_rollback(True)

    print(colored("\n✅ Import completato", "cyan", attrs=["bold"]))
    print(colored(f"   Nuovi documenti: {created_docs}", "green"))
    print(colored(f"   Aggiornati: {updated_docs}", "yellow"))
    print(colored(f"   Vendor non trovati: {missing_vendor}\n", "red"))


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import documenti vendor (VendorDocument) da Excel/CSV")
    parser.add_argument("-f", "--file", dest="file_path", default=FILE_PATH, help="Percorso file")
    parser.add_argument("-s", "--sheet", dest="sheet_name", default=SHEET_NAME, help="Indice o nome foglio")
    parser.add_argument("--dry-run", action="store_true", help="Simula senza salvare modifiche")
    args = parser.parse_args()

    import_documents(file_path=args.file_path, sheet_name=args.sheet_name, dry_run=args.dry_run)
