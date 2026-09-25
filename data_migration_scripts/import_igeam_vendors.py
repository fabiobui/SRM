#!/usr/bin/env python
"""
Import una tantum dei fornitori IGEAM dall'estrazione anagrafica Embyon.

Il file sorgente è l'export Excel dell'anagrafica fornitori IGEAM (foglio
``ANAGRAFICA FORNITORI_Completa``, una riga per CODCONTO). Vengono inseriti
solo i fornitori non ancora presenti a database, con i campi minimi per il
censimento: Codice Embyon, Società Embyon (``Igeam``), ragione sociale, tipo
fornitore, P.IVA, C.F., stato attivo su Embyon, contatti e sede.

Il lavoro è diviso in due passi, da rieseguire su ogni ambiente (locale,
test, produzione) perché il risultato dipende dal database su cui girano:

1. ``analizza``: SOLA LETTURA. Incrocia l'Excel con i fornitori a database
   e scrive in ``data_migration_scripts/reports/``:
   - ``igeam_analisi.csv``: tutte le righe Excel con l'esito e il motivo;
   - ``igeam_nuovi.csv``: solo i fornitori da inserire, già mappati sui
     campi del fornitore. È il file da rivedere prima del caricamento.
2. ``carica``: inserisce i fornitori di ``igeam_nuovi.csv``. Prima di ogni
   riga ricontrolla Codice Embyon / P.IVA / C.F. sul database, quindi un
   secondo lancio non duplica nulla. Scrive ``igeam_inseriti.csv`` con i
   codici creati, utile per un eventuale rollback con
   ``data_migration_scripts/delete_vendors.py --field old_code --ids ...``.

Esiti dell'analisi (vale il primo applicabile):
    ESCLUSO_STATO      stato Embyon DISMESSO o "IN VERIFICA -DOPPIO IN SAGE"
    ESCLUSO_MARCATO    ragione sociale marcata come doppione (***, +++,
                       "non usare")
    GIA_IMPORTATO      Codice Embyon già presente con Società Igeam
    GIA_PRESENTE       P.IVA o C.F. già usati da un fornitore a database
    COLLISIONE_CODICE  Codice Embyon già usato da un fornitore di un'altra
                       Società: saltato (old_code è UNIQUE)
    GIA_PRESENTE_NOME  senza P.IVA/C.F. validi, ma con la stessa ragione
                       sociale di un fornitore a database: saltato
    DOPPIONE_EXCEL     stesso soggetto di un'altra riga Excel preferita
                       (prima lo stato attivo, poi la creazione più recente)
    NUOVO              da inserire

La "Riga excel Albo Fornitore" (``albo_excel_row``) NON viene compilata: è
la chiave con cui gli script di import competenze/servizi/documenti
ritrovano i fornitori dell'Albo originale, e i numeri di riga dei due file
si sovrapporrebbero. La riga IGEAM resta nei report CSV.

I report contengono dati fornitore (P.IVA, C.F., recapiti): restano in
``data_migration_scripts/reports/`` (non servita da Django) e sono esclusi da
git.

ESEMPI (dalla root del repo, dentro la venv):
    python data_migration_scripts/import_igeam_vendors.py analizza \
        -f data_migration_scripts/input/IGEAM_ANAGRAFICA.xlsx
    python data_migration_scripts/import_igeam_vendors.py carica \
        -f data_migration_scripts/reports/igeam_nuovi.csv --dry-run
    python data_migration_scripts/import_igeam_vendors.py carica \
        -f data_migration_scripts/reports/igeam_nuovi.csv
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

import pandas as pd  # noqa: E402
from django.db import transaction  # noqa: E402
from termcolor import colored  # noqa: E402

from vendor_management_system.import_embyon_codes import (  # noqa: E402
    code_key,
    norm_cf,
    norm_code,
    norm_name,
    norm_vat,
)
from vendor_management_system.vendors.models import (  # noqa: E402
    Address,
    Vendor,
)

REPORT_DIR = Path(__file__).resolve().parent / "reports"
ANALISI_CSV = "igeam_analisi.csv"
NUOVI_CSV = "igeam_nuovi.csv"
INSERITI_CSV = "igeam_inseriti.csv"

IGEAM = "Igeam"

# === COLONNE DELL'ESTRAZIONE EMBYON ===
COL_CODE = "CODCONTO"
COL_NAME = "DSCCONTO1"
COL_PERS_FISICA = "FLGPERSFISICA"
COL_CF = "CODFISCALE"
COL_VAT = "PARTITAIVA"
COL_TIPO = "dbo_ALD_TAB_TipoFornitore.Descrizione"
COL_STATO = "dbo_ALD_TAB_StatoFornitore.Descrizione"
COL_INDIRIZZO = "INDIRIZZO"
COL_CAP = "CAP"
COL_LOCALITA = "LOCALITA"
COL_PROVINCIA = "PROVINCIA"
COL_NAZIONE = "CODNAZIONE"
COL_TELEFONO = "TELEFONO"
COL_FAX = "FAX"
COL_EMAIL = "TELEX"  # in Embyon la colonna TELEX contiene l'email
COL_PEC = "PEC"
COL_CREAZIONE = "DtCreazione"

REQUIRED_COLUMNS = [
    COL_CODE,
    COL_NAME,
    COL_PERS_FISICA,
    COL_CF,
    COL_VAT,
    COL_TIPO,
    COL_STATO,
    COL_INDIRIZZO,
    COL_CAP,
    COL_LOCALITA,
    COL_PROVINCIA,
    COL_NAZIONE,
    COL_TELEFONO,
    COL_FAX,
    COL_EMAIL,
    COL_PEC,
    COL_CREAZIONE,
]

# === REGOLE CONCORDATE ===
# Stati Embyon considerati "attivo su Embyon"; tutti gli altri (BLOCCATO,
# NON ATTIVO/NON MOVIMENTATO, SOSPESO, ...) valgono come non attivo.
ACTIVE_STATES = {
    "ATTIVO",
    "ATTIVO_DA RIQUALIFICARE",
    "ANAGRAFICA DA SAGE/DA COMPLETARE",
    "IMPORT IGEAM",
    "DA QUALIFICARE",
}
# Stati esclusi dall'import: fornitori dismessi o doppioni già segnalati.
EXCLUDED_STATES = {"DISMESSO", "IN VERIFICA -DOPPIO IN SAGE"}
# Ragioni sociali marcate a mano come doppioni ("***ALS ITALIA SRL",
# "+++TUTTOAMBIENTE SPA", "** non usare ***STUDIO ...").
MARKED_NAME_RE = re.compile(r"^\s*[*+]|NON\s+USARE", re.IGNORECASE)

PLACEHOLDER_RE = re.compile(r"0+|9+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
PEC_HINTS = ("pec", "legalmail")
CF_PERSONA_RE = re.compile(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]")

VAT_MAX_LEN = Vendor._meta.get_field("vat_number").max_length
CF_MAX_LEN = Vendor._meta.get_field("fiscal_code").max_length

# Ordine delle colonne del file dei nuovi fornitori (input di "carica").
NUOVI_FIELDS = [
    "riga_excel",
    "old_code",
    "embyon_company",
    "name",
    "vendor_type",
    "vat_number",
    "fiscal_code",
    "embyon_active",
    "email",
    "pec",
    "phone",
    "contact_details",
    "indirizzo",
    "cap",
    "localita",
    "provincia",
    "nazione",
]
ANALISI_FIELDS = [
    "riga_excel",
    "codconto",
    "old_code",
    "name",
    "vat_number",
    "fiscal_code",
    "stato_embyon",
    "esito",
    "motivo",
    "vendor_code_esistente",
    "nome_esistente",
    "avvisi",
]


# === NORMALIZZAZIONE ===
def clean(value):
    """Stringa ripulita: None/NaN -> '', spazi esterni rimossi."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def clean_vat(value):
    """P.IVA normalizzata; vuota, segnaposto (000.., 999..) o troppo lunga ->
    None. Ritorna (valore, avviso)."""
    # clean() prima di normalizzare: una cella vuota arriva da pandas come
    # NaN, che norm_vat trasformerebbe nella stringa "NAN".
    vat = norm_vat(clean(value))
    if not vat or PLACEHOLDER_RE.fullmatch(vat):
        return None, ""
    if len(vat) > VAT_MAX_LEN:
        return None, f"P.IVA '{vat}' troppo lunga, non importata"
    return vat, ""


def clean_cf(value):
    """C.F. normalizzato; vuoto, segnaposto o troppo lungo -> None.
    Ritorna (valore, avviso)."""
    cf = norm_cf(clean(value))
    if not cf or PLACEHOLDER_RE.fullmatch(cf):
        return None, ""
    if len(cf) > CF_MAX_LEN:
        return None, f"C.F. '{cf}' troppo lungo, non importato"
    return cf, ""


def is_foreign(vat, nazione):
    """Fornitore estero: nazione Embyon diversa da 0 (Italia) oppure P.IVA
    con prefisso di paese (norm_vat ha già tolto l'eventuale 'IT')."""
    if clean(nazione) not in ("", "0"):
        return True
    return bool(vat and re.match(r"^[A-Z]{2}", vat))


def infer_vendor_type(pers_fisica, vat, cf, nazione, tipo_embyon):
    """Tipo fornitore dedotto dai dati anagrafici; None se in dubbio."""
    if is_foreign(vat, nazione):
        return "Internazionale"
    if clean(tipo_embyon).upper() == "DIPENDENTI INTERNI":
        return "Dipendente"
    vat_italiana = bool(vat and re.fullmatch(r"\d{11}", vat))
    flag = clean(pers_fisica)
    if flag == "0" and vat_italiana:
        return "Società"
    if flag == "1" and vat_italiana and cf and CF_PERSONA_RE.fullmatch(cf):
        return "Libero Professionista"
    return None


def is_active_state(stato):
    return clean(stato).upper() in ACTIVE_STATES


def exclusion_reason(stato, name):
    """(esito, motivo) se la riga è fuori perimetro, altrimenti None."""
    stato_up = clean(stato).upper()
    if stato_up in EXCLUDED_STATES:
        return "ESCLUSO_STATO", f"stato Embyon {stato_up}"
    if MARKED_NAME_RE.search(clean(name)):
        return "ESCLUSO_MARCATO", "ragione sociale marcata come doppione"
    return None


def extract_emails(text):
    return EMAIL_RE.findall(clean(text))


def looks_like_pec(email):
    domain = email.rsplit("@", 1)[-1].lower()
    return any(hint in domain for hint in PEC_HINTS)


def split_contacts(email_col, pec_col, fax_col):
    """Distribuisce i recapiti Embyon sui campi del fornitore.

    - ``pec``: prima PEC della colonna PEC; se vuota, la prima email di
      TELEX che ha un dominio da PEC (pec/legalmail);
    - ``email``: prima email di TELEX che non è una PEC;
    - ``contact_details``: fax ed eventuali altre email, in chiaro.
    """
    pecs = extract_emails(pec_col)
    pec = pecs[0] if pecs else None
    email = None
    extra = []
    seen = {pec.lower()} if pec else set()
    for addr in pecs[1:] + extract_emails(email_col):
        if addr.lower() in seen:
            continue
        seen.add(addr.lower())
        if pec is None and looks_like_pec(addr):
            pec = addr
        elif email is None and not looks_like_pec(addr):
            email = addr
        else:
            extra.append(addr)
    details = []
    fax = clean(fax_col)
    if fax:
        details.append(f"Fax: {fax}")
    if extra:
        details.append(f"Altre email: {', '.join(extra)}")
    return email, pec, "\n".join(details)


def clean_phone(value):
    return clean(value).lstrip("-").strip()[:100] or None


# === MAPPATURA RIGA EXCEL -> FORNITORE ===
def build_record(row, excel_row):
    """Mappa una riga dell'estrazione sui campi del fornitore.

    Ritorna un dict con i campi di ``NUOVI_FIELDS`` più le informazioni di
    servizio usate dall'analisi (chiavi che iniziano per ``_``).
    """
    vat, vat_warn = clean_vat(row.get(COL_VAT))
    cf, cf_warn = clean_cf(row.get(COL_CF))
    email, pec, details = split_contacts(
        row.get(COL_EMAIL), row.get(COL_PEC), row.get(COL_FAX)
    )
    nazione = clean(row.get(COL_NAZIONE))
    return {
        "riga_excel": excel_row,
        "old_code": norm_code(clean(row.get(COL_CODE))),
        "embyon_company": IGEAM,
        "name": clean(row.get(COL_NAME)),
        "vendor_type": infer_vendor_type(
            row.get(COL_PERS_FISICA), vat, cf, nazione, row.get(COL_TIPO)
        ),
        "vat_number": vat,
        "fiscal_code": cf,
        "embyon_active": is_active_state(row.get(COL_STATO)),
        "email": email,
        "pec": pec,
        "phone": clean_phone(row.get(COL_TELEFONO)),
        "contact_details": details,
        "indirizzo": clean(row.get(COL_INDIRIZZO)),
        "cap": clean(row.get(COL_CAP)),
        "localita": clean(row.get(COL_LOCALITA)),
        "provincia": clean(row.get(COL_PROVINCIA)).upper(),
        "nazione": "Italia" if nazione in ("", "0") else "Estero",
        "_codconto": clean(row.get(COL_CODE)),
        "_stato": clean(row.get(COL_STATO)),
        "_creazione": clean(row.get(COL_CREAZIONE)),
        "_avvisi": "; ".join(w for w in (vat_warn, cf_warn) if w),
    }


# === INCROCIO CON IL DATABASE ===
def build_index(vendors):
    """Indici dei fornitori esistenti per P.IVA/C.F., codice e nome.

    ``vendors`` è un iterabile di dict con pk, name, old_code,
    embyon_company, vat_number, fiscal_code. P.IVA e C.F. finiscono nello
    stesso indice: per le società il C.F. coincide con la P.IVA, e un
    fornitore censito con il solo C.F. deve essere trovato anche dalla P.IVA
    (e viceversa).
    """
    ids, codes, names = {}, {}, {}
    for v in vendors:
        ref = (v["pk"], v["name"] or "")
        for key, label in (
            (clean_vat(v["vat_number"])[0], "PARTITA_IVA"),
            (clean_cf(v["fiscal_code"])[0], "CODICE_FISCALE"),
        ):
            if key:
                ids.setdefault(key, (*ref, label))
        if v["old_code"]:
            codes[code_key(v["old_code"])] = (*ref, v["embyon_company"])
        nome = match_name(v["name"])
        if nome:
            names.setdefault(nome, ref)
    return {"ids": ids, "codes": codes, "names": names}


def load_db_index():
    return build_index(
        Vendor.objects.values(
            "pk",
            "name",
            "old_code",
            "embyon_company",
            "vat_number",
            "fiscal_code",
        )
    )


def match_name(value):
    """Ragione sociale per il confronto esatto: via i punti prima di
    ``norm_name``, così "S.r.l." diventa "SRL" (forma societaria ignorata)
    invece delle lettere isolate "S R L"."""
    return norm_name(str(value or "").replace(".", ""))


def record_ids(rec):
    return [k for k in (rec["vat_number"], rec["fiscal_code"]) if k]


def _set_esito(rec, esito, motivo, match=None):
    rec["esito"] = esito
    rec["motivo"] = motivo
    rec["vendor_code_esistente"] = match[0] if match else ""
    rec["nome_esistente"] = match[1] if match else ""


def match_db(rec, index):
    """Esito del confronto con il database, o None se il fornitore non c'è."""
    code = index["codes"].get(code_key(rec["old_code"]))
    if code and code[2] == IGEAM:
        return "GIA_IMPORTATO", "Codice Embyon già presente per Igeam", code
    for key in record_ids(rec):
        hit = index["ids"].get(key)
        if hit:
            return "GIA_PRESENTE", f"stesso {hit[2]} ({key})", hit
    if code:
        return (
            "COLLISIONE_CODICE",
            f"Codice Embyon già usato per la Società {code[2] or '-'}",
            code,
        )
    if not record_ids(rec):
        hit = index["names"].get(match_name(rec["name"]))
        if hit:
            return (
                "GIA_PRESENTE_NOME",
                "stessa ragione sociale, senza P.IVA/C.F.",
                hit,
            )
    return None


def dedupe_keys(rec):
    """Chiavi con cui riconoscere lo stesso soggetto dentro l'Excel: P.IVA e
    C.F.; senza identificativi, la ragione sociale (se c'è)."""
    ids = record_ids(rec)
    if ids:
        return ids
    nome = match_name(rec["name"])
    return [f"NOME:{nome}"] if nome else []


def gruppo_iva_hint(rec, other):
    """Avviso per la revisione: stessa P.IVA ma C.F. entrambi valorizzati e
    diversi è tipico di un Gruppo IVA (società distinte, P.IVA comune)."""
    if (
        rec["vat_number"]
        and rec["vat_number"] == other["vat_number"]
        and rec["fiscal_code"]
        and other["fiscal_code"]
        and rec["fiscal_code"] != other["fiscal_code"]
    ):
        return " - C.F. diverso, possibile Gruppo IVA: verificare"
    return ""


def classify(records, index):
    """Assegna esito/motivo a ogni record (modifica i dict in place)."""
    candidates = []
    for rec in records:
        excluded = exclusion_reason(rec["_stato"], rec["name"])
        if excluded:
            _set_esito(rec, *excluded)
            continue
        found = match_db(rec, index)
        if found:
            _set_esito(rec, *found)
            continue
        candidates.append(rec)

    # Doppioni interni all'Excel: un solo fornitore per soggetto. Si
    # preferisce lo stato attivo, poi la creazione più recente su Embyon,
    # poi la riga più alta nel file.
    candidates.sort(
        key=lambda r: (r["embyon_active"], r["_creazione"], r["riga_excel"]),
        reverse=True,
    )
    chosen = {}
    for rec in candidates:
        keys = dedupe_keys(rec)
        winner = next((chosen[k] for k in keys if k in chosen), None)
        if winner:
            _set_esito(
                rec,
                "DOPPIONE_EXCEL",
                f"stesso soggetto di {winner['old_code']} "
                f"(riga {winner['riga_excel']}){gruppo_iva_hint(rec, winner)}",
            )
            continue
        _set_esito(rec, "NUOVO", "")
        for k in keys:
            chosen[k] = rec
    return records


# === I/O ===
def read_excel(path, sheet):
    df = pd.read_excel(path, sheet_name=sheet, dtype=str)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(
            colored(f"Colonne mancanti nel file: {', '.join(missing)}", "red")
        )
    # Intestazione in riga 1: il primo fornitore è la riga 2 del foglio.
    return [
        build_record(row, i + 2)
        for i, row in enumerate(df.to_dict(orient="records"))
    ]


def _csv_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "SI" if value else "NO"
    return value


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig: il BOM fa aprire il file correttamente da Excel.
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=fields, delimiter=";", extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({f: _csv_value(row.get(f)) for f in fields})


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def analizza(path, sheet=0, report_dir=REPORT_DIR):
    """Passo 1: sola lettura, scrive i due report. Ritorna i record."""
    records = classify(read_excel(path, sheet), load_db_index())
    for rec in records:
        rec.update(
            codconto=rec["_codconto"],
            stato_embyon=rec["_stato"],
            avvisi=rec["_avvisi"],
        )
    write_csv(report_dir / ANALISI_CSV, ANALISI_FIELDS, records)
    nuovi = [r for r in records if r["esito"] == "NUOVO"]
    write_csv(report_dir / NUOVI_CSV, NUOVI_FIELDS, nuovi)
    return records


def _none_if_empty(value):
    value = (value or "").strip()
    return value or None


def create_vendor(row):
    """Crea Address (se indirizzo e località ci sono) e Vendor da una riga
    del file dei nuovi fornitori."""
    address = None
    if row["indirizzo"] and row["localita"]:
        address = Address.objects.create(
            street_address=row["indirizzo"][:255],
            city=row["localita"][:100],
            postal_code=row["cap"][:20] or None,
            state_province=row["provincia"] or None,
            country=row["nazione"] or "Italia",
        )
    return Vendor.objects.create(
        old_code=row["old_code"],
        embyon_company=row["embyon_company"] or IGEAM,
        name=row["name"],
        # esplicito: il default del modello è "Società"
        vendor_type=_none_if_empty(row["vendor_type"]),
        vat_number=_none_if_empty(row["vat_number"]),
        fiscal_code=_none_if_empty(row["fiscal_code"]),
        embyon_active=row["embyon_active"].strip().upper() == "SI",
        email=_none_if_empty(row["email"]),
        pec=_none_if_empty(row["pec"]),
        phone=_none_if_empty(row["phone"]),
        contact_details=row["contact_details"] or "",
        address=address,
    )


def carica(path, dry_run=False, report_dir=REPORT_DIR):
    """Passo 2: inserisce i fornitori del file dei nuovi. Ritorna la lista
    dei risultati per riga (dict con esito INSERITO/SALTATO)."""
    rows = read_csv(path)
    missing = [f for f in NUOVI_FIELDS if rows and f not in rows[0]]
    if missing:
        sys.exit(
            colored(f"Colonne mancanti nel file: {', '.join(missing)}", "red")
        )
    results = []
    with transaction.atomic():
        index = load_db_index()
        for row in rows:
            rec = {
                "old_code": row["old_code"],
                "name": row["name"],
                "vat_number": _none_if_empty(row["vat_number"]),
                "fiscal_code": _none_if_empty(row["fiscal_code"]),
            }
            found = match_db(rec, index)
            if found:
                results.append({**row, "esito": "SALTATO", "motivo": found[1]})
                continue
            vendor = create_vendor(row)
            ref = (vendor.pk, vendor.name)
            index["codes"][code_key(vendor.old_code)] = (*ref, IGEAM)
            for key in record_ids(rec):
                index["ids"].setdefault(key, (*ref, "INSERITO"))
            results.append(
                {
                    **row,
                    "vendor_code": vendor.pk,
                    "esito": "INSERITO",
                    "motivo": "",
                }
            )
        if dry_run:
            transaction.set_rollback(True)
    if not dry_run:
        write_csv(
            report_dir / INSERITI_CSV,
            [
                "vendor_code",
                "old_code",
                "name",
                "riga_excel",
                "esito",
                "motivo",
            ],
            results,
        )
    return results


# === CLI ===
def print_summary(title, counter):
    print(colored(title, "cyan", attrs=["bold"]))
    for esito, n in sorted(counter.items(), key=lambda kv: -kv[1]):
        print(f"   {esito:<20} {n:>6}")
    print(f"   {'TOTALE':<20} {sum(counter.values()):>6}")


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Import una tantum dei fornitori IGEAM da Embyon."
    )
    sub = p.add_subparsers(dest="comando", required=True)

    a = sub.add_parser(
        "analizza", help="incrocia l'Excel con il DB (sola lettura)"
    )
    a.add_argument(
        "-f", "--file", required=True, help="estrazione Excel IGEAM"
    )
    a.add_argument("-s", "--sheet", default=0, help="indice o nome del foglio")

    c = sub.add_parser(
        "carica", help="inserisce i fornitori di igeam_nuovi.csv"
    )
    c.add_argument("-f", "--file", required=True, help="file igeam_nuovi.csv")
    c.add_argument(
        "--dry-run", action="store_true", help="esegue e annulla tutto"
    )

    for parser in (a, c):
        parser.add_argument(
            "--report-dir",
            type=Path,
            default=REPORT_DIR,
            help=f"cartella dei report (default: {REPORT_DIR})",
        )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.comando == "analizza":
        sheet = int(args.sheet) if str(args.sheet).isdigit() else args.sheet
        records = analizza(args.file, sheet, args.report_dir)
        print_summary(
            f"Analisi di {len(records)} righe",
            Counter(r["esito"] for r in records),
        )
        print(f"   Report completo: {args.report_dir / ANALISI_CSV}")
        print(f"   Da inserire:     {args.report_dir / NUOVI_CSV}")
    else:
        results = carica(args.file, args.dry_run, args.report_dir)
        title = (
            "Caricamento (DRY RUN, annullato)"
            if args.dry_run
            else "Caricamento"
        )
        print_summary(title, Counter(r["esito"] for r in results))
        for r in results:
            if r["esito"] == "SALTATO":
                print(
                    colored(
                        f"   saltato {r['old_code']} {r['name']}: "
                        f"{r['motivo']}",
                        "yellow",
                    )
                )
        if not args.dry_run:
            print(f"   Esito: {args.report_dir / INSERITI_CSV}")


if __name__ == "__main__":
    main()
