"""
Associa ai fornitori il Codice Embyon (campo ``old_code``) cercandoli
nell'anagrafica Embyon per Codice Fiscale / Partita IVA.

Di default lavora solo sui vendor il cui ``old_code`` inizia per ``XLS``
(quelli caricati da Excel con un codice provvisorio), sostituendolo con il
CODCONTO trovato su Embyon (es. ``F 6459``). Insieme al codice viene salvata la
Società Embyon (``embyon_company``), perché lo stesso fornitore ha un CODCONTO
diverso per ogni Società. Il campo "Riga excel Albo Fornitore"
(``albo_excel_row``) non viene toccato: resta il riferimento al file di origine e
viene riportato nel CSV di esito.

Uso:
    python vendor_management_system/import_embyon_codes.py --dry-run
    python vendor_management_system/import_embyon_codes.py
    python vendor_management_system/import_embyon_codes.py --prefix XLS --report out.csv

Criterio di match (come la query di riferimento, in ordine di priorità):
    1. Codice Fiscale + Partita IVA coincidenti
    2. Codice Fiscale
    3. Partita IVA
Se il criterio migliore restituisce più CODCONTO distinti (lo stesso fornitore
esiste su più Società/DITTA) viene preso il codice con il numero più alto dopo
la 'F', ma solo fino a 3 omocodie (--max-omocodie): oltre quella soglia il
fornitore viene saltato come AMBIGUO e va deciso a mano.
Con --prefer-ditta si restringe prima la scelta a una Società.

Con --fuzzy i fornitori rimasti senza aggancio su C.F./P.IVA vengono cercati per
somiglianza della ragione sociale (soglia --fuzzy-threshold, default 0.90) usando
la provincia come vincolo quando è nota da entrambe le parti.
"""

import os
import sys
import csv
import django
import difflib
import argparse
from collections import defaultdict
from pathlib import Path
from termcolor import colored

# --- Individua la root del progetto SRM ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.append(str(BASE_DIR))

# --- Configura Django ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings as dj_settings  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from vendor_management_system.vendors.models import Vendor  # noqa: E402


# === CONFIG ===
PREFIX = "XLS"          # prefisso degli old_code da rimpiazzare
DRY_RUN = False
REPORT = "embyon_match_report.csv"
MAX_OMOCODIE = 3        # oltre questo numero di codici distinti non si sceglie da soli
FUZZY_THRESHOLD = 0.90  # similarità minima sulla ragione sociale (--fuzzy)

# Anagrafica con indirizzo/provincia: Embyon_Fornitori_T non ha la provincia,
# che si recupera (dove presente) da Account_Embyon_T su DITTA+CODCONTO.
ACCOUNT_TABLE = "redmine_test.Account_Embyon_T"

# Forme societarie e titoli: tolti dal nome prima del confronto fuzzy, altrimenti
# "ROSSI SRL" e "ROSSI S.R.L." risulterebbero diversi e "ALFA SRL"/"BETA SRL" simili.
NOISE_TOKENS = {
    "SRL", "SRLS", "SPA", "SAS", "SNC", "SS", "SC", "SCARL", "SCRL", "SAPA",
    "SOCIETA", "SOC", "COOP", "COOPERATIVA", "IMPRESA", "DITTA", "STUDIO",
    "DOTT", "DOTTOR", "DOTTORE", "DOTTSSA", "DR", "DRSSA", "PROF", "ING", "AVV",
    "DI", "E", "C", "IN", "DEL", "DELLA", "DEI", "SPORT", "ONLUS", "ETS",
}

# Priorità dei criteri: valore più basso = criterio migliore
CRITERIA = {
    "CODICE_FISCALE_E_PARTITA_IVA": 0,
    "CODICE_FISCALE": 1,
    "PARTITA_IVA": 2,
}


# === HELPER FUNCTIONS ===
def norm_vat(value):
    """Normalizza una partita IVA: maiuscolo, senza separatori, senza prefisso IT."""
    v = "".join(ch for ch in str(value or "").upper() if ch.isalnum())
    if v.startswith("IT") and v[2:].isdigit():
        v = v[2:]
    return v


def norm_cf(value):
    """Normalizza un codice fiscale: maiuscolo, senza separatori."""
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def norm_code(value):
    """Normalizza il CODCONTO: 'F     7' -> 'F 7' (come il modal di ricerca)."""
    return " ".join(str(value or "").split())


def code_key(value):
    """Chiave di confronto fra codici conto: ignora gli spazi di padding."""
    return norm_code(value).replace(" ", "").upper()


def norm_name(value):
    """Normalizza una ragione sociale per il confronto fuzzy.

    Maiuscolo, via accenti/punteggiatura, via forme societarie e titoli
    (vedi NOISE_TOKENS): "Bianalisi S.p.A." -> "BIANALISI".
    """
    txt = str(value or "").upper()
    txt = "".join(ch if ch.isalnum() else " " for ch in txt)
    tokens = [t for t in txt.split() if t and t not in NOISE_TOKENS]
    return " ".join(tokens)


def similarity(a, b):
    """Similarità 0..1 fra due ragioni sociali normalizzate, con prefiltri.

    quick_ratio() è un limite superiore di ratio(): se già non basta si evita il
    confronto completo, che su decine di migliaia di righe pesa parecchio.
    """
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    if min(la, lb) / max(la, lb) < 0.80:
        return 0.0
    sm = difflib.SequenceMatcher(None, a, b)
    if sm.real_quick_ratio() < 0.80 or sm.quick_ratio() < 0.80:
        return 0.0
    return sm.ratio()


def name_buckets(name):
    """Chiavi di blocking: prefisso di 4 caratteri di ogni parola significativa.

    Serve solo a restringere i candidati da confrontare; il match vero lo decide
    la similarità sull'intera ragione sociale.
    """
    return {t[:4] for t in name.split() if len(t) >= 3}


def vendor_province(vendor):
    """Sigla provincia del fornitore (da Address), se valorizzata."""
    addr = getattr(vendor, "address", None)
    return (getattr(addr, "state_province", "") or "").strip().upper()[:2]


def load_embyon_rows(table):
    """Carica l'anagrafica fornitori Embyon e la indicizza per P.IVA e C.F.

    Il match viene fatto in Python e non con una JOIN cross-schema perché i due
    schema hanno collation diverse (utf8mb4_0900_ai_ci vs utf8mb4_unicode_ci) e
    il confronto diretto in SQL fallisce con "Illegal mix of collations".
    """
    account = getattr(dj_settings, "EMBYON_ACCOUNT_TABLE", ACCOUNT_TABLE)
    sql = (
        "SELECT f.DITTA, f.CODCONTO, f.DSCCONTO1, f.PARTITAIVA, f.CODFISCALE, "
        "f.Descrizione, a.PROVINCIA, a.LOCALITA "
        f"FROM {table} f "
        f"LEFT JOIN {account} a "
        "  ON a.DITTA = f.DITTA AND a.CODCONTO = f.CODCONTO AND a.TIPOCONTO = 'F' "
        "WHERE f.TIPOCONTO = 'F'"
    )
    fallback = (
        "SELECT DITTA, CODCONTO, DSCCONTO1, PARTITAIVA, CODFISCALE, Descrizione, "
        f"NULL, NULL FROM {table} WHERE TIPOCONTO = 'F'"
    )
    with connection.cursor() as cursor:
        try:
            cursor.execute(sql)
        except Exception:
            # L'anagrafica con indirizzo può non esserci: si prosegue senza provincia.
            cursor.execute(fallback)
        rows = cursor.fetchall()

    by_vat = defaultdict(list)
    by_cf = defaultdict(list)
    by_name = defaultdict(list)
    with_prov = 0
    for ditta, codconto, dsc1, piva, cfisc, descr, prov, loc in rows:
        status = (descr or "").strip()
        rec = {
            "ditta": (ditta or "").strip(),
            "code": norm_code(codconto),
            "name": (dsc1 or "").strip(),
            "norm_name": norm_name(dsc1),
            "vat": norm_vat(piva),
            "cf": norm_cf(cfisc),
            "province": (prov or "").strip().upper()[:2],
            "city": (loc or "").strip(),
            "status": status,
            "active": status.lower() == "attivo",
        }
        if not rec["code"]:
            continue
        if rec["province"]:
            with_prov += 1
        if rec["vat"]:
            by_vat[rec["vat"]].append(rec)
        if rec["cf"]:
            by_cf[rec["cf"]].append(rec)
        if rec["norm_name"]:
            for key in name_buckets(rec["norm_name"]):
                by_name[key].append(rec)
    return len(rows), with_prov, by_vat, by_cf, by_name


def find_fuzzy(vendor, by_name, threshold, require_province=False):
    """Cerca il fornitore per somiglianza della ragione sociale.

    La provincia (quando nota da entrambe le parti) è un vincolo: candidati di
    un'altra provincia vengono scartati. Su Embyon però la provincia è presente
    solo per una piccola parte dei fornitori, quindi di default un candidato
    senza provincia resta valido (con --fuzzy-province-required invece cade).

    Ritorna (righe migliori, similarità, nota).
    """
    target = norm_name(vendor.name)
    if not target:
        return [], 0.0, ""

    prov = vendor_province(vendor)
    seen = {}
    for key in name_buckets(target):
        for rec in by_name.get(key, []):
            seen[id(rec)] = rec

    best_score = 0.0
    best = []
    scartati_prov = 0
    for rec in seen.values():
        score = similarity(target, rec["norm_name"])
        if score < threshold:
            continue
        if prov and rec["province"] and rec["province"] != prov:
            scartati_prov += 1
            continue
        if require_province and not (prov and rec["province"]):
            continue
        if score > best_score + 1e-9:
            best_score, best = score, [rec]
        elif abs(score - best_score) <= 1e-9:
            best.append(rec)

    if not best:
        nota = f"scartati {scartati_prov} candidati di altra provincia" if scartati_prov else ""
        return [], 0.0, nota

    conferme = {r["province"] for r in best if r["province"]}
    if prov and conferme:
        nota = f"provincia confermata ({prov})"
    elif prov:
        nota = "provincia non presente su Embyon"
    else:
        nota = "provincia non presente sul fornitore"
    if scartati_prov:
        nota += f"; scartati {scartati_prov} di altra provincia"
    return best, best_score, nota


def find_candidates(vendor, by_vat, by_cf):
    """Ritorna (criterio, righe Embyon) per il criterio di match migliore."""
    vat = norm_vat(vendor.vat_number)
    cf = norm_cf(vendor.fiscal_code)

    candidates = {}  # id(rec) -> rec, per deduplicare fra i due indici
    for rec in (by_vat.get(vat, []) if vat else []) + (by_cf.get(cf, []) if cf else []):
        candidates[id(rec)] = rec

    best = None
    grouped = defaultdict(list)
    for rec in candidates.values():
        if vat and cf and rec["vat"] == vat and rec["cf"] == cf:
            crit = "CODICE_FISCALE_E_PARTITA_IVA"
        elif cf and rec["cf"] == cf:
            crit = "CODICE_FISCALE"
        elif vat and rec["vat"] == vat:
            crit = "PARTITA_IVA"
        else:
            continue
        grouped[crit].append(rec)
        rank = CRITERIA[crit]
        if best is None or rank < best:
            best = rank

    if best is None:
        return None, []
    criterion = next(k for k, v in CRITERIA.items() if v == best)
    return criterion, grouped[criterion]


def code_number(value):
    """Parte numerica del CODCONTO: 'F 18148' -> 18148."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else -1


def pick_code(rows, prefer_ditta=None, max_omocodie=MAX_OMOCODIE):
    """Sceglie un unico CODCONTO fra le righe candidate.

    Se lo stesso fornitore esiste su più Società (più CODCONTO distinti) viene
    preso quello con il numero più alto dopo la 'F', cioè il codice più recente.
    La scelta automatica vale però solo fino a ``max_omocodie`` codici distinti:
    oltre quella soglia il fornitore è troppo frammentato in anagrafica (es. i
    gruppi con la stessa P.IVA su decine di sedi) e va deciso a mano.

    Ritorna (riga_scelta, nota); riga_scelta è None se non si può decidere.
    """
    if not rows:
        return None, "nessun match"

    if prefer_ditta:
        filtered = [r for r in rows if r["ditta"].lower() == prefer_ditta.lower()]
        if filtered:
            rows = filtered

    distinct = {code_key(r["code"]) for r in rows}
    chosen = max(rows, key=lambda r: code_number(r["code"]))
    if len(distinct) == 1:
        return chosen, None

    codes = sorted({r["code"] for r in rows}, key=code_number)
    if len(distinct) > max_omocodie:
        return None, (f"ambiguo: {len(distinct)} omocodie (oltre il limite di "
                      f"{max_omocodie}): {', '.join(codes)}")

    scartati = ", ".join(c for c in codes if code_key(c) != code_key(chosen["code"]))
    return chosen, f"ambiguo ({len(distinct)} omocodie): scelto il maggiore, scartati {scartati}"


def import_embyon_codes(prefix=None, dry_run=None, report=None, prefer_ditta=None,
                        limit=None, set_active=False, max_omocodie=MAX_OMOCODIE,
                        fuzzy=False, fuzzy_threshold=FUZZY_THRESHOLD,
                        fuzzy_province_required=False):
    prefix = prefix if prefix is not None else PREFIX
    dry_run = DRY_RUN if dry_run is None else dry_run
    report = report if report is not None else REPORT

    table = getattr(dj_settings, "EMBYON_FORNITORI_TABLE", "redmine_test.Embyon_Fornitori_T")

    try:
        total_rows, with_prov, by_vat, by_cf, by_name = load_embyon_rows(table)
    except Exception as exc:
        print(colored(f"❌ Errore leggendo l'anagrafica Embyon ({table}): {exc}", "red"))
        return

    qs = Vendor.objects.filter(old_code__startswith=prefix).select_related("address").order_by("old_code")
    if limit:
        qs = qs[:limit]
    vendors = list(qs)

    print(colored(f"📦 Anagrafica Embyon: {table} | righe TIPOCONTO='F': {total_rows}", "cyan", attrs=["bold"]))
    print(colored(f"   Fornitori con old_code '{prefix}*': {len(vendors)} | DRY_RUN: {dry_run}", "cyan", attrs=["bold"]))
    print(colored(f"   Scelta automatica del codice maggiore fino a {max_omocodie} omocodie", "cyan"))
    if fuzzy:
        print(colored(
            f"   Fuzzy su ragione sociale attivo: soglia {fuzzy_threshold:.0%} | "
            f"provincia nota su {with_prov}/{total_rows} righe Embyon"
            + (" | provincia obbligatoria" if fuzzy_province_required else ""), "cyan"))
    if prefer_ditta:
        print(colored(f"   Società preferita in caso di ambiguità: {prefer_ditta}", "cyan"))
    print()

    # Società note al modello: una DITTA nuova su Embyon va aggiunta a
    # Vendor.EMBYON_COMPANY_CHOICES, altrimenti il form admin la rifiuta.
    known_companies = {c for c, _ in Vendor.EMBYON_COMPANY_CHOICES}
    unknown = {r["ditta"] for recs in by_vat.values() for r in recs if r["ditta"]} - known_companies
    if unknown:
        print(colored(
            f"   ⚠️  Società presenti su Embyon ma non in Vendor.EMBYON_COMPANY_CHOICES: "
            f"{', '.join(sorted(unknown))}", "yellow"))

    # Codici già assegnati ad altri vendor: old_code è UNIQUE, va evitata la collisione.
    taken = {
        code_key(c): pk
        for pk, c in Vendor.objects.exclude(old_code__isnull=True)
        .exclude(old_code="")
        .values_list("pk", "old_code")
    }

    updated = skipped = not_found = ambiguous = fuzzy_hits = 0
    rows_report = []

    with transaction.atomic():
        for i, vendor in enumerate(vendors):
            # Riferimento alla riga dell'Albo: old_code sta per essere sostituito,
            # quindi è l'unico aggancio che resta verso il file di origine.
            riga = f" (riga Albo {vendor.albo_excel_row})" if vendor.albo_excel_row else ""
            criterion, candidates = find_candidates(vendor, by_vat, by_cf)
            score = 0.0
            fuzzy_note = ""
            if not candidates and fuzzy:
                # Nessun aggancio su C.F./P.IVA: si ripiega sulla ragione sociale.
                candidates, score, fuzzy_note = find_fuzzy(
                    vendor, by_name, fuzzy_threshold, fuzzy_province_required)
                if candidates:
                    criterion = f"FUZZY_{score:.0%}"

            chosen, note = pick_code(candidates, prefer_ditta, max_omocodie)
            if fuzzy_note:
                note = f"{note}; {fuzzy_note}" if note else fuzzy_note
            sim = f"{score:.2f}".replace(".", ",") if score else ""

            if chosen is None:
                if candidates:
                    skipped += 1
                    esito, colore = "AMBIGUO", "yellow"
                    print(colored(f"[{i+1}] ⚠️  {vendor.old_code}{riga} {vendor.name[:40]} — {note}", colore))
                else:
                    not_found += 1
                    esito = "NESSUN_MATCH"
                    print(colored(f"[{i+1}] ⚪ {vendor.old_code}{riga} {vendor.name[:40]} — nessun match", "white"))
                rows_report.append([vendor.pk, vendor.albo_excel_row or "", vendor.old_code, "", vendor.name,
                                    vendor.fiscal_code or "", vendor.vat_number or "",
                                    criterion or "", "", "", "", sim, vendor_province(vendor), "",
                                    esito, note or ""])
                continue

            new_code = chosen["code"]
            owner = taken.get(code_key(new_code))
            if owner and owner != vendor.pk:
                skipped += 1
                other = Vendor.objects.filter(pk=owner).values_list("name", flat=True).first()
                msg = f"codice {new_code} già assegnato a {other}"
                print(colored(f"[{i+1}] ⚠️  {vendor.old_code}{riga} {vendor.name[:40]} — {msg}", "yellow"))
                rows_report.append([vendor.pk, vendor.albo_excel_row or "", vendor.old_code, new_code, vendor.name,
                                    vendor.fiscal_code or "", vendor.vat_number or "",
                                    criterion, chosen["ditta"], chosen["status"],
                                    chosen["name"], sim,
                                    vendor_province(vendor), chosen["province"],
                                    "COLLISIONE", msg])
                continue

            if len(new_code) > Vendor._meta.get_field("old_code").max_length:
                skipped += 1
                msg = f"codice {new_code} troppo lungo"
                print(colored(f"[{i+1}] ⚠️  {vendor.old_code}{riga} {vendor.name[:40]} — {msg}", "yellow"))
                rows_report.append([vendor.pk, vendor.albo_excel_row or "", vendor.old_code, new_code, vendor.name,
                                    vendor.fiscal_code or "", vendor.vat_number or "",
                                    criterion, chosen["ditta"], chosen["status"],
                                    chosen["name"], sim,
                                    vendor_province(vendor), chosen["province"],
                                    "SCARTATO", msg])
                continue

            old = vendor.old_code
            vendor.old_code = new_code
            # La Società (DITTA) fa parte dell'identificazione del codice: lo
            # stesso fornitore ha un CODCONTO diverso per ogni Società.
            vendor.embyon_company = chosen["ditta"] or None
            fields = ["old_code", "embyon_company"]
            if set_active:
                vendor.embyon_active = chosen["active"]
                fields.append("embyon_active")
            vendor.save(update_fields=fields)

            taken.pop(code_key(old), None)
            taken[code_key(new_code)] = vendor.pk
            updated += 1
            if score:
                fuzzy_hits += 1
                esito_ok = "AGGIORNATO_FUZZY"
            elif note:
                esito_ok = "AGGIORNATO_AMBIGUO"
            else:
                esito_ok = "AGGIORNATO"
            if "omocodie" in (note or ""):
                ambiguous += 1
            print(colored(
                f"[{i+1}] ✅ {old} → {new_code} | {vendor.name[:35]} "
                f"[{criterion} | {chosen['ditta']} | {chosen['status']}]"
                + (f" ≈ {chosen['name'][:35]}" if score else "")
                + (f" — {note}" if note else ""), "yellow" if note else "green"))
            rows_report.append([vendor.pk, vendor.albo_excel_row or "", old, new_code, vendor.name,
                                vendor.fiscal_code or "", vendor.vat_number or "",
                                criterion, chosen["ditta"], chosen["status"],
                                chosen["name"], sim,
                                vendor_province(vendor), chosen["province"],
                                esito_ok, note or ""])

        if dry_run:
            print(colored("\n🧪 DRY RUN attivo: annullo tutte le modifiche...", "yellow", attrs=["bold"]))
            transaction.set_rollback(True)

    if report:
        report_path = Path(report)
        if not report_path.is_absolute():
            report_path = Path.cwd() / report_path
        with open(report_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow(["vendor_id", "riga_albo", "old_code_precedente", "codice_embyon", "name",
                             "fiscal_code", "vat_number", "criterio", "ditta", "stato_embyon",
                             "nome_embyon", "similarita", "provincia_vendor", "provincia_embyon",
                             "esito", "note"])
            writer.writerows(rows_report)
        print(colored(f"\n📄 Report scritto in: {report_path}", "cyan"))

    print(colored("\n✅ Elaborazione completata", "cyan", attrs=["bold"]))
    print(colored(f"   Aggiornati: {updated} (di cui {ambiguous} con più codici, preso il maggiore"
                  + (f"; {fuzzy_hits} per ragione sociale" if fuzzy_hits else "") + ") "
                  f"| Saltati: {skipped} | Senza match: {not_found}", "green"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Associa il Codice Embyon (old_code) ai fornitori cercandoli per C.F./P.IVA")
    parser.add_argument("-p", "--prefix", default=PREFIX,
                        help="Prefisso degli old_code da elaborare (default: XLS)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Esegue senza salvare le modifiche")
    parser.add_argument("--report", default=REPORT,
                        help="File CSV con l'esito riga per riga (contiene anche i codici precedenti)")
    parser.add_argument("--prefer-ditta", dest="prefer_ditta", default=None,
                        help="Società da preferire quando il fornitore esiste su più DITTA")
    parser.add_argument("--set-active", dest="set_active", action="store_true",
                        help="Aggiorna anche il flag 'Attivo su Embyon' in base allo stato Embyon")
    parser.add_argument("--fuzzy", action="store_true",
                        help="Se C.F./P.IVA non agganciano, cerca per somiglianza della ragione sociale")
    parser.add_argument("--fuzzy-threshold", dest="fuzzy_threshold", type=float, default=FUZZY_THRESHOLD,
                        help=f"Similarità minima 0..1 per il match fuzzy (default: {FUZZY_THRESHOLD})")
    parser.add_argument("--fuzzy-province-required", dest="fuzzy_province_required", action="store_true",
                        help="Accetta un match fuzzy solo se la provincia è nota e coincide su entrambi i lati")
    parser.add_argument("--max-omocodie", dest="max_omocodie", type=int, default=MAX_OMOCODIE,
                        help=f"Numero massimo di codici distinti entro cui scegliere il maggiore (default: {MAX_OMOCODIE})")
    parser.add_argument("--limit", type=int, default=None,
                        help="Elabora solo i primi N fornitori (per prove)")
    args = parser.parse_args()

    import_embyon_codes(prefix=args.prefix, dry_run=args.dry_run, report=args.report,
                        prefer_ditta=args.prefer_ditta, limit=args.limit,
                        set_active=args.set_active, max_omocodie=args.max_omocodie,
                        fuzzy=args.fuzzy, fuzzy_threshold=args.fuzzy_threshold,
                        fuzzy_province_required=args.fuzzy_province_required)
