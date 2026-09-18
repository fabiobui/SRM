"""
Allinea i Set (Requisiti Professionali e Servizi) da un database SRM a un
altro.

Copia ``vendors.CompetenceSet`` e ``vendors.ServiceSet`` con le rispettive
righe M2M da un DB sorgente (di norma quello di sviluppo, dove i set sono
stati creati) a un DB destinazione (di norma una copia di produzione).

Uso:
    python vendor_management_system/sync_sets.py --source vms_db \
        --target vms_db_PROD --dry-run
    python vendor_management_system/sync_sets.py --source vms_db \
        --target vms_db_PROD

Prerequisito: sul DB destinazione deve essere applicata la migrazione
``vendors.0035_competenceset_serviceset``, altrimenti le tabelle non esistono:
    DB_NAME=<target> python manage.py migrate vendors

Le anagrafiche referenziate (Classificazioni, Competenze, Tipi Servizio) NON
vengono toccate: se un set punta a una riga che sul destinazione non esiste, la
riga viene saltata e segnalata, salvo usare --copy-missing-refs.

Lo script è idempotente: i set già presenti sul destinazione (stesso nome e
stessa classificazione) vengono aggiornati, non duplicati.
"""

import argparse
import os
import sys
from pathlib import Path

import django
from termcolor import colored

# --- Individua la root del progetto SRM ---
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.append(str(BASE_DIR))

# --- Configura Django ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection, transaction  # noqa: E402

# === CONFIG ===
# Tabelle coinvolte: (set, tabella M2M, colonna FK del set, anagrafica puntata)
SET_TABLES = [
    (
        "vendors_competenceset",
        "vendors_competenceset_competences",
        "competenceset_id",
        "competence_id",
        "vendors_competence",
        "Requisiti Professionali",
    ),
    (
        "vendors_serviceset",
        "vendors_serviceset_service_types",
        "serviceset_id",
        "servicetype_id",
        "vendors_servicetype",
        "Servizi",
    ),
]
CATEGORY_TABLE = "vendors_category"

# Collation di progetto. I confronti fra i due database vengono forzati a
# questa collation: sorgente e destinazione possono averne di diverse (un
# dump caricato in un DB con default diverso porta tabelle
# utf8mb4_0900_ai_ci accanto a utf8mb4_unicode_ci) e il confronto diretto
# fallirebbe con "Illegal mix of collations".
JOIN_COLLATE = "utf8mb4_unicode_ci"


# === HELPER FUNCTIONS ===
def table_exists(cursor, db, table):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
        [db, table],
    )
    return cursor.fetchone()[0] > 0


def columns(cursor, db, table):
    cursor.execute(
        "SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY "
        "ORDINAL_POSITION",
        [db, table],
    )
    return {r[0]: (r[1], r[2]) for r in cursor.fetchall()}


def table_collations(cursor, db, tables):
    """Collation di ogni tabella: serve solo a segnalare i DB disallineati."""
    placeholders = ", ".join(["%s"] * len(tables))
    cursor.execute(
        "SELECT TABLE_NAME, TABLE_COLLATION FROM information_schema.TABLES "
        f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME IN ({placeholders})",
        [db] + list(tables),
    )
    return dict(cursor.fetchall())


def check_structure(cursor, source, target, tables):
    """Verifica che le tabelle esistano su entrambi i DB con le stesse
    colonne."""
    problems = []
    for table in tables:
        if not table_exists(cursor, source, table):
            problems.append(f"{source}.{table}: tabella assente")
            continue
        if not table_exists(cursor, target, table):
            problems.append(
                f"{target}.{table}: tabella assente — applica prima "
                f"`DB_NAME={target} python manage.py migrate vendors`"
            )
            continue
        src, tgt = (
            columns(cursor, source, table),
            columns(cursor, target, table),
        )
        for col in sorted(set(src) - set(tgt)):
            problems.append(
                f"{table}.{col}: presente in {source}, assente in {target}"
            )
        for col in sorted(set(tgt) - set(src)):
            problems.append(
                f"{table}.{col}: presente in {target}, assente in {source}"
            )
        for col in sorted(set(src) & set(tgt)):
            if src[col] != tgt[col]:
                problems.append(
                    f"{table}.{col}: tipo diverso "
                    f"({src[col][0]} vs {tgt[col][0]})"
                )
    return problems


def missing_refs(cursor, source, target, m2m_table, fk_col, ref_table):
    """Righe M2M del sorgente che puntano a un record assente sul
    destinazione."""
    cursor.execute(
        f"SELECT DISTINCT m.{fk_col} FROM {source}.{m2m_table} m "
        f"LEFT JOIN {target}.{ref_table} r "
        f"  ON m.{fk_col} COLLATE {JOIN_COLLATE} = "
        f"r.id COLLATE {JOIN_COLLATE} "
        f"WHERE r.id IS NULL"
    )
    return [r[0] for r in cursor.fetchall()]


def copy_refs(cursor, source, target, ref_table, ids):
    """Copia sul destinazione le righe di anagrafica mancanti (stessi id)."""
    if not ids:
        return 0
    cols = list(columns(cursor, source, ref_table))
    collist = ", ".join(f"`{c}`" for c in cols)
    placeholders = ", ".join(["%s"] * len(ids))
    cursor.execute(
        f"INSERT INTO {target}.{ref_table} ({collist}) "
        f"SELECT {collist} FROM {source}.{ref_table} WHERE id IN "
        f"({placeholders})",
        ids,
    )
    return cursor.rowcount


def sync_sets(source, target, dry_run=False, copy_missing_refs=False):
    with connection.cursor() as cursor:
        # 1. Struttura
        tables = [CATEGORY_TABLE]
        for set_t, m2m_t, _, _, ref_t, _ in SET_TABLES:
            tables += [set_t, m2m_t, ref_t]
        problems = check_structure(cursor, source, target, tables)

        print(
            colored(
                f"🔍 Confronto struttura {source} → {target}",
                "cyan",
                attrs=["bold"],
            )
        )
        if problems:
            for p in problems:
                print(colored(f"   ❌ {p}", "red"))
            print(
                colored(
                    "\nStruttura non allineata: interrotto.",
                    "red",
                    attrs=["bold"],
                )
            )
            return False
        print(
            colored(
                f"   ✅ {len(tables)} tabelle con struttura identica", "green"
            )
        )

        # Collation diverse non bloccano (i confronti sono forzati a
        # JOIN_COLLATE) ma è bene saperlo: dentro un singolo DB devono
        # invece essere uniformi.
        src_coll = table_collations(cursor, source, tables)
        tgt_coll = table_collations(cursor, target, tables)
        diverse = [t for t in tables if src_coll.get(t) != tgt_coll.get(t)]
        if diverse:
            print(
                colored(
                    f"   ℹ️  Collation diverse fra i due DB su "
                    f"{len(diverse)} tabelle "
                    f"({src_coll.get(diverse[0])} vs "
                    f"{tgt_coll.get(diverse[0])}): "
                    f"i confronti sono forzati a {JOIN_COLLATE}",
                    "cyan",
                )
            )
        for db, coll in ((source, src_coll), (target, tgt_coll)):
            valori = set(coll.values())
            if len(valori) > 1:
                print(
                    colored(
                        f"   ⚠️  {db} ha collation NON uniformi fra le "
                        f"sue tabelle: {', '.join(sorted(valori))} — le "
                        f"query interne di Django falliranno con "
                        f"'Illegal mix of collations'",
                        "yellow",
                    )
                )
        print()

        totals = {"set": 0, "m2m": 0, "refs": 0, "skipped": 0}

        with transaction.atomic():
            for set_t, m2m_t, set_fk, ref_fk, ref_t, label in SET_TABLES:
                print(colored(f"📦 {label} ({set_t})", "cyan", attrs=["bold"]))

                # 2. Riferimenti mancanti sul destinazione
                missing = missing_refs(
                    cursor, source, target, m2m_t, ref_fk, ref_t
                )
                if missing:
                    cursor.execute(
                        f"SELECT id, code, name FROM {source}.{ref_t} "
                        f"WHERE id IN "
                        f"({', '.join(['%s'] * len(missing))})",
                        missing,
                    )
                    rows = cursor.fetchall()
                    if copy_missing_refs:
                        n = copy_refs(cursor, source, target, ref_t, missing)
                        totals["refs"] += n
                        for _, code, name in rows:
                            print(
                                colored(
                                    f"   ➕ Copiato in anagrafica: "
                                    f"{code} — {name}",
                                    "green",
                                )
                            )
                    else:
                        for _, code, name in rows:
                            print(
                                colored(
                                    f"   ⚠️  Assente su {target}: "
                                    f"{code} — {name} "
                                    f"(le righe che lo usano verranno "
                                    f"saltate; usa --copy-missing-refs)",
                                    "yellow",
                                )
                            )

                # 3. Set: aggiorna quelli già presenti (stesso nome +
                # categoria), inserisce i nuovi
                cursor.execute(
                    f"SELECT id, name, description, is_active, "
                    f"sort_order, category_id "
                    f"FROM {source}.{set_t} ORDER BY sort_order, name"
                )
                source_sets = cursor.fetchall()

                for sid, name, descr, active, order, cat in source_sets:
                    cursor.execute(
                        f"SELECT id FROM {target}.{set_t} WHERE name = %s AND "
                        + (
                            "category_id = %s"
                            if cat
                            else "category_id IS NULL"
                        ),
                        [name, cat] if cat else [name],
                    )
                    existing = cursor.fetchone()

                    if existing:
                        tid = existing[0]
                        cursor.execute(
                            f"UPDATE {target}.{set_t} SET "
                            f"description=%s, is_active=%s, "
                            f"sort_order=%s WHERE id=%s",
                            [descr, active, order, tid],
                        )
                        verbo = "♻️  Aggiornato"
                    else:
                        cursor.execute(
                            f"INSERT INTO {target}.{set_t} "
                            f"(name, description, is_active, "
                            f"sort_order, category_id) "
                            f"VALUES (%s, %s, %s, %s, %s)",
                            [name, descr, active, order, cat],
                        )
                        cursor.execute("SELECT LAST_INSERT_ID()")
                        tid = cursor.fetchone()[0]
                        verbo = "✅ Creato"
                    totals["set"] += 1

                    # 4. Righe M2M: si riallineano al contenuto del sorgente
                    cursor.execute(
                        f"DELETE FROM {target}.{m2m_t} WHERE {set_fk} = %s",
                        [tid],
                    )
                    cursor.execute(
                        f"INSERT INTO {target}.{m2m_t} ({set_fk}, {ref_fk}) "
                        f"SELECT %s, m.{ref_fk} FROM {source}.{m2m_t} m "
                        f"JOIN {target}.{ref_t} r "
                        f"  ON m.{ref_fk} COLLATE {JOIN_COLLATE} = "
                        f"r.id COLLATE {JOIN_COLLATE} "
                        f"WHERE m.{set_fk} = %s",
                        [tid, sid],
                    )
                    copiate = cursor.rowcount
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {source}.{m2m_t} "
                        f"WHERE {set_fk} = %s",
                        [sid],
                    )
                    attese = cursor.fetchone()[0]
                    totals["m2m"] += copiate
                    totals["skipped"] += attese - copiate

                    nota = (
                        ""
                        if copiate == attese
                        else colored(
                            f" ({attese - copiate} saltate per "
                            f"riferimento assente)",
                            "yellow",
                        )
                    )
                    print(
                        f"   {verbo}: {name} — {copiate}/{attese} voci{nota}"
                    )
                print()

            if dry_run:
                print(
                    colored(
                        "🧪 DRY RUN attivo: annullo tutte le modifiche...",
                        "yellow",
                        attrs=["bold"],
                    )
                )
                transaction.set_rollback(True)

    print(colored("✅ Allineamento completato", "cyan", attrs=["bold"]))
    print(
        colored(
            f"   Set: {totals['set']} | Voci nei set: {totals['m2m']} "
            f"| Anagrafiche copiate: {totals['refs']} | "
            f"Voci saltate: {totals['skipped']}",
            "green",
        )
    )
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Allinea i Set (Requisiti Professionali e Servizi) fra "
            "due database SRM"
        )
    )
    parser.add_argument(
        "--source", required=True, help="Database sorgente (es. vms_db)"
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Database destinazione (es. vms_db_PROD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Esegue senza salvare le modifiche",
    )
    parser.add_argument(
        "--copy-missing-refs",
        dest="copy_missing_refs",
        action="store_true",
        help=(
            "Copia anche le righe di anagrafica (competenze/servizi) "
            "assenti sul destinazione"
        ),
    )
    args = parser.parse_args()

    if args.source == args.target:
        print(colored("❌ Sorgente e destinazione coincidono.", "red"))
        sys.exit(1)

    ok = sync_sets(
        args.source, args.target, args.dry_run, args.copy_missing_refs
    )
    sys.exit(0 if ok else 1)
