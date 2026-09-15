import os
import re
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

# Tipo di assegnazione ricavato dal prefisso del codice in intestazione.
# Nel file lo stesso requisito compare sotto più codici (QUAL-001 e COMP-001 sono
# entrambi "Qualifica RSPP"): il prefisso non identifica il requisito, dice con
# quale ruolo viene assegnato al fornitore. Per questo i flag stanno su
# VendorCompetence e non su Competence.
TYPE_BY_PREFIX = {
    "QUAL": "is_qualifica",
    "COMP": "is_competenza",
    "ISCR": "is_iscrizione_albo",
}

# Corrispondenze da codice colonna del file a codice del catalogo, per i casi in
# cui la descrizione nel file non coincide con il nome a catalogo e l'aggancio
# automatico non riesce. Si può aggiungerne una al volo con --alias.
ALIASES = {
    # "QUAL-003": "REQ-003",   # Qualifica Coord. Sicurezza Cantieri -> Coordinatore Sicurezza Cantieri (CSP-CSE)
    # "QUAL-004": "REQ-004",   # Consul. Merci Pericolose            -> Consul. ADR
}
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


def albo_row_from_code(code):
    """Riga del foglio Albo a partire dal codice provvisorio: XLS0001 -> 2.

    I codici XLS sono progressivi sulle righe del file Albo, che ha
    l'intestazione in riga 1: il fornitore XLS0001 sta quindi in riga 2.
    """
    m = re.match(r"^XLS0*(\d+)$", str(code or "").strip().upper())
    return int(m.group(1)) + 1 if m else None


def build_vendor_index():
    """Indici dei fornitori per Codice Embyon e per Riga excel Albo Fornitore."""
    by_code, by_row = {}, {}
    for v in Vendor.objects.only("pk", "old_code", "albo_excel_row", "name"):
        if v.old_code:
            by_code[v.old_code.strip().upper()] = v
        if v.albo_excel_row:
            by_row[v.albo_excel_row] = v
    return by_code, by_row


def resolve_vendor(value, by_code, by_row, key="auto"):
    """Trova il fornitore dalla prima colonna del file.

    La colonna contiene il codice provvisorio dell'Albo (XLS0001). Quel codice
    finisce in ``old_code``, che però viene sostituito dal codice Embyon da
    import_embyon_codes: dopo quel passaggio l'unico aggancio stabile al file è
    ``albo_excel_row``. Per questo, per i codici XLS, la riga viene provata per
    prima. Ritorna (vendor, criterio usato).
    """
    key_value = str(value or "").strip().upper()
    riga = albo_row_from_code(key_value)
    if key_value.isdigit():           # la colonna porta direttamente la riga
        riga = int(key_value)

    if key != "old_code" and riga and riga in by_row:
        return by_row[riga], f"riga Albo {riga}"
    if key != "albo_row":
        vendor = by_code.get(key_value)
        if vendor:
            return vendor, "Codice Embyon"
    return None, None


def norm_name(value):
    """Normalizza una descrizione per il confronto: minuscolo, spazi collassati."""
    return " ".join(str(value or "").strip().lower().split())


def norm_code(value):
    """Normalizza un codice: maiuscolo, solo caratteri alfanumerici."""
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def assignment_flag(code):
    """Flag di VendorCompetence corrispondente al prefisso del codice colonna."""
    prefix = str(code or "").split("-")[0].strip().upper()
    return TYPE_BY_PREFIX.get(prefix)


def build_competence_index():
    """Indici del catalogo a DB: per codice normalizzato e per nome normalizzato.

    Il file usa codici storici (QUAL-*/COMP-*) che a catalogo non esistono più:
    l'aggancio avviene quindi per nome, con il codice come conferma.
    """
    by_code, by_name = {}, {}
    for comp in Competence.objects.all():
        by_code[norm_code(comp.code)] = comp
        by_name.setdefault(norm_name(comp.name), comp)
    return by_code, by_name


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
def import_competences(file_path: str | Path | None = None, sheet_name=None, dry_run: bool | None = None,
                       create_missing=False, reset_except_company=None, aliases=None, key="auto"):
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
    print(colored(f"   Righe dati: {len(df)} | Colonne requisito: {len(code_to_name)}", "cyan", attrs=["bold"]))

    # Risoluzione delle colonne sul catalogo a DB, fatta una volta sola.
    by_code, by_name = build_competence_index()
    alias_map = dict(ALIASES)
    alias_map.update(aliases or {})
    resolved_cols = {}   # codice colonna -> (Competence, flag) oppure (None, flag)
    for code, name in code_to_name.items():
        target = alias_map.get(code)
        comp = (by_code.get(norm_code(target)) if target else None)
        if comp is None:
            comp = by_name.get(norm_name(name)) or by_code.get(norm_code(code))
        resolved_cols[code] = (comp, assignment_flag(code))

    noti = sum(1 for c, _ in resolved_cols.values() if c)
    senza_tipo = [c for c, (_, f) in resolved_cols.items() if not f]
    print(colored(f"   Requisiti riconosciuti a catalogo: {noti}/{len(resolved_cols)}", "cyan"))
    for code, (comp, flag) in resolved_cols.items():
        if not comp:
            print(colored(f"   ⚠️  {code} ({code_to_name[code][:40]}) non è a catalogo"
                          + ("" if create_missing else
                             " — colonna ignorata (usa --alias CODICE=CODICE_CATALOGO)"), "yellow"))
    if senza_tipo:
        print(colored(f"   ⚠️  Prefisso non riconosciuto (nessun tipo assegnabile): "
                      f"{', '.join(senza_tipo)}", "yellow"))
    print()

    created_vendor_competences = 0
    updated_vendor_competences = 0
    missing_vendors = 0
    created_competences = 0
    deleted = 0

    by_vendor_code, by_vendor_row = build_vendor_index()

    with transaction.atomic():
        # Azzeramento delle assegnazioni dei fornitori di altre Società, da fare
        # prima dell'import per non lasciare righe di un caricamento precedente.
        if reset_except_company:
            to_delete = VendorCompetence.objects.exclude(
                vendor__embyon_company=reset_except_company)
            deleted = to_delete.count()
            print(colored(
                f"🧹 Assegnazioni da rimuovere (fornitori con Società ≠ "
                f"{reset_except_company}, vuota compresa): {deleted}", "yellow", attrs=["bold"]))
            if deleted:
                to_delete.delete()
            print()

        for i, row in df.iterrows():
            # La prima colonna ora si chiama "codice" (non più "old_code")
            old_code = safe_str(row.get("codice"))
            if not old_code:
                print(colored(f"[{i+1}] ⚠️ Riga senza codice, saltata", "yellow"))
                continue

            vendor, criterio = resolve_vendor(old_code, by_vendor_code, by_vendor_row, key)
            if not vendor:
                print(colored(f"[{i+1}] ❌ Vendor non trovato: {old_code}", "red"))
                missing_vendors += 1
                continue

            print(colored(f"\n➡️ {i+1}. Vendor: {vendor.name or old_code} "
                          f"[{old_code} → {criterio}]", "cyan"))

            for col, val in row.items():
                if col == "codice":
                    continue
                if not parse_bool(val):
                    continue

                comp_code = safe_str(col)
                comp_name = code_to_name.get(comp_code, comp_code)
                comp, flag = resolved_cols.get(comp_code, (None, assignment_flag(comp_code)))

                if comp is None:
                    if not create_missing:
                        # Il requisito non è a catalogo: crearlo qui produrrebbe
                        # doppioni dei codici storici, quindi si salta.
                        continue
                    comp = Competence.objects.create(
                        code=comp_code,
                        name=comp_name,
                        is_active=True,
                        requires_certification=True,
                    )
                    resolved_cols[comp_code] = (comp, flag)
                    created_competences += 1
                    print(colored(f"   🆕 Creato requisito: {comp.code} - {comp.name}", "green"))

                vc, created_vc = VendorCompetence.objects.get_or_create(
                    vendor=vendor,
                    competence=comp,
                    defaults={"has_competence": True, "verified": False},
                )

                # Il tipo dipende dalla colonna: lo stesso requisito può arrivare
                # come qualifica e come competenza, e allora la riga è una sola
                # con entrambi i flag.
                tipo = ""
                if flag and not getattr(vc, flag):
                    setattr(vc, flag, True)
                    vc.save(update_fields=[flag])
                    tipo = f" [{flag.replace('is_', '')}]"

                if created_vc:
                    created_vendor_competences += 1
                    print(colored(f"   ✅ Assegnato: {comp.name}{tipo}", "yellow"))
                elif tipo:
                    updated_vendor_competences += 1
                    print(colored(f"   ➕ Tipo aggiunto: {comp.name}{tipo}", "yellow"))
                else:
                    print(colored(f"   ↪️ Già presente: {comp.name}", "white"))

        if dry_run:
            print(colored("\n🧪 DRY RUN: annullo tutte le modifiche", "yellow", attrs=["bold"]))
            transaction.set_rollback(True)

    print(colored("\n✅ Import completato", "cyan", attrs=["bold"]))
    if reset_except_company:
        print(colored(f"   Assegnazioni rimosse prima dell'import: {deleted}", "yellow"))
    print(colored(f"   Assegnazioni create: {created_vendor_competences}", "green"))
    print(colored(f"   Assegnazioni a cui è stato aggiunto un tipo: {updated_vendor_competences}", "green"))
    print(colored(f"   Requisiti creati a catalogo: {created_competences}", "green"))
    print(colored(f"   Vendor non trovati: {missing_vendors}\n", "red"))


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import competenze vendor da Excel/CSV")
    parser.add_argument("-f", "--file", dest="file_path", default=FILE_PATH, help="Percorso file")
    parser.add_argument("-s", "--sheet", dest="sheet_name", default=SHEET_NAME, help="Indice o nome foglio")
    parser.add_argument("--dry-run", action="store_true", help="Esegue simulazione senza salvare")
    parser.add_argument("--key", choices=["auto", "albo_row", "old_code"], default="auto",
                        help="Come agganciare il fornitore: auto (riga Albo per i codici XLS, "
                             "poi Codice Embyon), solo riga Albo, solo Codice Embyon")
    parser.add_argument("--create-missing", dest="create_missing", action="store_true",
                        help="Crea a catalogo i requisiti non riconosciuti (default: li salta)")
    parser.add_argument("--alias", action="append", default=[], metavar="COL=CATALOGO",
                        help="Aggancia una colonna a un requisito a catalogo (es. QUAL-003=REQ-003); "
                             "ripetibile")
    parser.add_argument("--reset-except-company", dest="reset_except_company", default=None,
                        help="Prima dell'import cancella le assegnazioni dei fornitori la cui "
                             "Società Embyon è diversa da quella indicata (es. Sicura); "
                             "i fornitori senza Società sono inclusi nella cancellazione")
    args = parser.parse_args()

    alias_map = {}
    for item in args.alias:
        if "=" not in item:
            print(colored(f"❌ Alias non valido (atteso COL=CATALOGO): {item}", "red"))
            sys.exit(1)
        col, target = item.split("=", 1)
        alias_map[col.strip()] = target.strip()

    import_competences(file_path=args.file_path, sheet_name=args.sheet_name, dry_run=args.dry_run,
                       create_missing=args.create_missing,
                       reset_except_company=args.reset_except_company, aliases=alias_map, key=args.key)
