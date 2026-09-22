"""Ripara la colonna `id` di documents_documentset.

Contesto: la migrazione 0006_documentset definisce `id` come BigAutoField
(chiave primaria auto-incrementale), ma su alcuni DB (locale Docker e test,
verificato manualmente) la colonna fisica è `bigint NOT NULL` senza
PRIMARY KEY né AUTO_INCREMENT — probabile drift da un ripristino/import dati
che ha ricreato la tabella senza questi vincoli. Effetto: gli UPDATE sulle
righe esistenti funzionano, ma qualsiasi INSERT di un nuovo DocumentSet
fallisce con "Field 'id' doesn't have a default value" (rilevato in
AIDEV-10 nel creare i nuovi Set Documentali Formatore/Dipendente/Consulente/
Laboratorio).

La riparazione è idempotente e difensiva: interviene solo se rileva
l'anomalia (colonna id senza AUTO_INCREMENT) e solo su MySQL — nessun
effetto se lo schema è già corretto o su altri backend (es. SQLite nei test,
dove comunque le migrazioni non vengono rigiocate: vedi `--no-migrations`
in CLAUDE.md).
"""

from django.db import migrations


def fix_documentset_id(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'documents_documentset'
              AND COLUMN_NAME = 'id'
              AND EXTRA LIKE '%auto_increment%'
            """
        )
        (already_fixed,) = cursor.fetchone()
        if already_fixed:
            return

        cursor.execute(
            "ALTER TABLE documents_documentset "
            "MODIFY id BIGINT NOT NULL AUTO_INCREMENT, "
            "ADD PRIMARY KEY (id)"
        )


def noop_reverse(apps, schema_editor):
    """Riparazione difensiva: nessun rollback (la tabella torna corretta,
    non c'è motivo di romperla di nuovo)."""


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0007_rename_documenttype_documentcatalog"),
    ]

    operations = [
        migrations.RunPython(fix_documentset_id, noop_reverse),
    ]
