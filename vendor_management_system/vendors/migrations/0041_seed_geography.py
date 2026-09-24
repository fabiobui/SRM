"""Semina il catalogo geografico (Nazioni, Regioni, Province).

Perché è una data migration e non basta il management command
``seed_geography``: ``compose/django/start`` esegue ``migrate`` PRIMA dei
comandi di seed, e la migrazione che travasa le vecchie zone di competenza
nei nuovi campi territoriali ha bisogno che le province
esistano già. Seminando qui, l'ordine è garantito per costruzione, e
funziona anche su un database vergine in fase di test.

Il seeding è idempotente e non tocca ``is_active``/``sort_order`` delle
righe già presenti: vedi ``vendor_management_system.vendors
.geography_seed``.
"""

from django.db import migrations

from vendor_management_system.vendors.geography_seed import seed_geography


def semina(apps, schema_editor):
    seed_geography(
        apps.get_model("vendors", "Country"),
        apps.get_model("vendors", "Region"),
        apps.get_model("vendors", "Province"),
        create_only=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("vendors", "0040_alter_vendor_vendor_type"),
    ]

    operations = [
        # Reverse noop: il catalogo geografico è dato di riferimento, non
        # va cancellato tornando indietro (altre righe lo referenziano).
        migrations.RunPython(semina, migrations.RunPython.noop),
    ]
