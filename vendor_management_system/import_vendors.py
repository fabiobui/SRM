import os
import sys
import django
import pandas as pd
from datetime import datetime
from django.db import transaction
from termcolor import colored
from pathlib import Path
import argparse

# --- Individua la root del progetto SRM ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent  # cioè /home/fabio/SRM
sys.path.append(str(BASE_DIR))

# --- Configura Django ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from vendor_management_system.vendors.models import Vendor, Address, QualificationType, ServiceType


# === CONFIG ===
FILE_PATH = "Import.xlsx"  # percorso file Excel o CSV
SHEET_NAME = 0  # se Excel ha più fogli
DRY_RUN = False  # True = non salva nulla


# === HELPER FUNCTIONS ===
def parse_bool(value):
    if pd.isna(value):
        return False
    v = str(value).strip().upper()
    return v in ["SI", "YES", "TRUE", "1", "X", "Y", "SI-X"]


def parse_date(value):
    if pd.isna(value) or value == "":
        return None
    try:
        return pd.to_datetime(value, errors="coerce").date()
    except Exception:
        return None


def safe_str(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def get_or_none(model, **filters):
    try:
        return model.objects.filter(**filters).first()
    except Exception:
        return None


def resolve_fk(model, name_field, value):
    """Ritorna una ForeignKey cercando per nome (case-insensitive)"""
    if not value or pd.isna(value):
        return None
    value = str(value).strip()
    obj = model.objects.filter(**{f"{name_field}__iexact": value}).first()
    if not obj:
        obj = model.objects.filter(**{f"{name_field}__icontains": value}).first()
    return obj


def create_or_get_address(row):
    """Evita duplicati di indirizzi identici"""
    address_data = dict(
        street_address=safe_str(row.get("address.street_address")),
        city=safe_str(row.get("address.city")),
        state_province=safe_str(row.get("address.state_province")),
        region=safe_str(row.get("address.region")),
        country=safe_str(row.get("address.country", "Italia")),
        postal_code="",
    )
    address, _ = Address.objects.get_or_create(**address_data)
    return address


def resolve_file_path(path: str | Path) -> Path | None:
    """
    Risolve il percorso del file cercando nell'ordine:
    - percorso assoluto
    - CWD (cartella da cui lanci lo script)
    - cartella dello script (vendor_management_system/)
    - root del progetto (BASE_DIR)
    """
    p = Path(path) if not isinstance(path, Path) else path
    if p.is_absolute() and p.exists():
        return p

    candidates = [
        Path.cwd() / p,
        CURRENT_DIR / p,
        BASE_DIR / p,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


# === MAIN IMPORT FUNCTION ===
@transaction.atomic
def import_vendors(file_path: str | Path | None = None, sheet_name=None, dry_run: bool | None = None):
    file_path = file_path if file_path is not None else FILE_PATH
    sheet_name = sheet_name if sheet_name is not None else SHEET_NAME
    dry_run = dry_run if dry_run is not None else DRY_RUN

    # Converte "0" in 0 se arriva come stringa
    if isinstance(sheet_name, str) and sheet_name.isdigit():
        sheet_name = int(sheet_name)

    resolved_path = resolve_file_path(file_path)
    if not resolved_path:
        print(colored("❌ File non trovato. Percorso fornito: ", "red"), end="")
        print(colored(str(file_path), "red", attrs=["bold"]))
        print(colored("Prova a specificare un percorso assoluto o usa l'opzione -f/--file.", "yellow"))
        print(colored(f"Cartella corrente: {Path.cwd()}", "yellow"))
        print(colored(f"Cartella script:   {CURRENT_DIR}", "yellow"))
        print(colored(f"Cartella progetto: {BASE_DIR}", "yellow"))
        sys.exit(1)

    ext = resolved_path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(resolved_path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(resolved_path, sheet_name=sheet_name, dtype=str)

    print(colored(f"\n📦 Importazione avviata da: {resolved_path}", "cyan"))
    print(colored(f"   Foglio: {sheet_name} | DRY_RUN: {dry_run}", "cyan", attrs=["bold"]))
    print(colored(f"   Fornitori trovati: {len(df)}\n", "cyan", attrs=["bold"]))

    created_count = updated_count = 0

    # Transazione esplicita per poter fare il rollback in DRY_RUN
    with transaction.atomic():
        for i, row in df.iterrows():
            try:
                old_code = safe_str(row.get("old_code"))
                if not old_code:
                    print(colored(f"[{i+1}] ❌ Riga senza old_code, ignorata", "red"))
                    continue

                # === Address ===
                address = create_or_get_address(row)

                # === ForeignKey resolution ===
                qualification = resolve_fk(QualificationType, "name", row.get("qualification_type"))
                service_type = resolve_fk(ServiceType, "name", row.get("service_type"))
                service_parent = resolve_fk(ServiceType, "name", row.get("service_type.parent"))

                # === Vendor ===
                defaults = dict(
                    name=safe_str(row.get("name")),
                    vat_number=safe_str(row.get("vat_number")),
                    email=safe_str(row.get("email")),
                    phone=safe_str(row.get("phone")),
                    vendor_type=safe_str(row.get("vendor_typye (typo)")),
                    competences_zone=safe_str(row.get("competences_zone")),
                    vendor_management_update=safe_str(row.get("vendor_management_update")),
                    qualification_type=qualification,
                    is_ico_consultant=parse_bool(row.get("is_ico_consultant")),
                    albo_zucchetti=safe_str(row.get("albo_zucchetti")),
                    service_type=service_type or service_parent,
                    service_additional=safe_str(row.get("service_additional")),
                    service_note=safe_str(row.get("service_note")),
                    cluster_cost=safe_str(row.get("cluster_cost")),
                    vendor_task_description=safe_str(row.get("vendor_task_description")),
                    begin_experience_date=parse_date(row.get("begin_experience_date")),
                    vendor_medical_service=safe_str(row.get("vendor_medical_service")),
                    mobile_device=parse_bool(row.get("mobile_device")),
                    ambulatory_service=safe_str(row.get("ambulatory_service")),
                    laboratory_service=parse_bool(row.get("laboratory_service")),
                    laboratory_independent=parse_bool(row.get("laboratory_independent")),
                    date_of_establishment=parse_date(row.get("date_of_establishment")),
                    licensed_physician_year=row.get("licensed_physician_year") if not pd.isna(row.get("licensed_physician_year")) else None,
                    other_medical_service=safe_str(row.get("other_medical_service")),
                    doctor_registration=safe_str(row.get("doctor_registration")),
                    doctor_cv=parse_bool(row.get("doctor_cv")),
                    doctor_cv2=parse_bool(row.get("doctor_cv2")),
                    contractual_status=safe_str(row.get("contractual_status"))[:2],
                    contractual_start_date=parse_date(row.get("contractual_start_date")),
                    contractual_end_date=parse_date(row.get("contractual_end_date")),
                    contractual_terms=safe_str(row.get("contractual_terms")),
                    reference_contact=safe_str(row.get("reference_contact / reference_person")),
                    vendor_final_evaluation=safe_str(row.get("vendor_final_evaluation")),
                    review_notes=safe_str(row.get("review_notes")),
                    address=address,
                )

                vendor, created = Vendor.objects.update_or_create(old_code=old_code, defaults=defaults)

                if created:
                    created_count += 1
                    print(colored(f"[{i+1}] ✅ Creato {vendor.name}", "green"))
                else:
                    updated_count += 1
                    print(colored(f"[{i+1}] ♻️ Aggiornato {vendor.name}", "yellow"))

            except Exception as e:
                print(colored(f"[{i+1}] ❌ Errore su {row.get('old_code')}: {e}", "red"))
                raise  # fa rollback di tutta la transazione

        if dry_run:
            print(colored("\n🧪 DRY RUN attivo: annullo tutte le modifiche...", "yellow", attrs=["bold"]))
            transaction.set_rollback(True)

    print(colored(f"\n✅ Importazione completata", "cyan", attrs=["bold"]))
    print(colored(f"   Nuovi: {created_count} | Aggiornati: {updated_count}", "green"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import fornitori da file Excel/CSV")
    parser.add_argument("-f", "--file", dest="file_path", default=FILE_PATH, help="Percorso file (assoluto o relativo)")
    parser.add_argument("-s", "--sheet", dest="sheet_name", default=SHEET_NAME, help="Indice (int) o nome (str) del foglio")
    parser.add_argument("--dry-run", action="store_true", help="Esegue senza salvare le modifiche")
    args = parser.parse_args()

    import_vendors(file_path=args.file_path, sheet_name=args.sheet_name, dry_run=args.dry_run)
