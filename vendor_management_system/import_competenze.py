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
FILE_PATH = "import_competenze_assegnate.xlsx"
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
    
    # Nuovo formato: riga 0 = nomi descrittivi, riga 1 = codici (header)
    # Leggiamo prima le due righe di intestazione per creare il mapping codice -> nome
    if ext == ".csv":
        df_headers = pd.read_csv(resolved_path, dtype=str, nrows=2, header=None)
    else:
        df_headers = pd.read_excel(resolved_path, sheet_name=sheet_name, dtype=str, nrows=2, header=None)
    
    # Riga 0: nomi descrittivi delle competenze
    # Riga 1: codici delle competenze (QUAL-001, QUAL-003, ecc.)
    names_row = df_headers.iloc[0].tolist()
    codes_row = df_headers.iloc[1].tolist()
    
    # Creiamo mapping codice -> nome (escludendo la prima colonna "codice")
    code_to_name = {}
    for i, (name, code) in enumerate(zip(names_row, codes_row)):
        if i == 0:  # Salta la prima colonna (codice vendor)
            continue
        code_str = safe_str(code)
        name_str = safe_str(name)
        if code_str and name_str:
            code_to_name[code_str] = name_str
    
    # Ora leggiamo il file con header sulla riga 1 (codici) e skippiamo la riga 0
    if ext == ".csv":
        df = pd.read_csv(resolved_path, dtype=str, header=1)
    else:
        df = pd.read_excel(resolved_path, sheet_name=sheet_name, dtype=str, header=1)

    print(colored(f"\n📘 Import competenze da: {resolved_path}", "cyan"))
    print(colored(f"   Foglio: {sheet_name} | DRY_RUN: {dry_run}", "cyan", attrs=["bold"]))
    print(colored(f"   Righe dati: {len(df)} | Competenze: {len(code_to_name)}\n", "cyan", attrs=["bold"]))

    created_vendor_competences = 0
    missing_vendors = 0
    created_competences = 0

    with transaction.atomic():
        for i, row in df.iterrows():
            # La prima colonna ora si chiama "codice" (non più "old_code")
            old_code = safe_str(row.get("codice"))
            if not old_code:
                print(colored(f"[{i+1}] ⚠️ Riga senza codice, saltata", "yellow"))
                continue

            vendor = Vendor.objects.filter(old_code=old_code).first()
            if not vendor:
                print(colored(f"[{i+1}] ❌ Vendor non trovato: {old_code}", "red"))
                missing_vendors += 1
                continue

            print(colored(f"\n➡️ {i+1}. Vendor: {vendor.name or old_code}", "cyan"))

            for col, val in row.items():
                if col == "codice":
                    continue
                if not parse_bool(val):
                    continue

                # Il codice competenza è l'intestazione della colonna (es. QUAL-001)
                comp_code = safe_str(col)
                # Il nome viene dal mapping con la prima riga
                comp_name = code_to_name.get(comp_code, comp_code)

                comp, created = Competence.objects.get_or_create(
                    code=comp_code,
                    defaults={
                        "name": comp_name,
                        "is_active": True,
                        "requires_certification": True,
                    },
                )
                if created:
                    created_competences += 1
                    print(colored(f"   🆕 Creata competenza: {comp.code} - {comp.name}", "green"))

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
