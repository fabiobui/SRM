from django.db import migrations, models


def clear_validity_without_renewal(apps, schema_editor):
    """I tipi senza rinnovo non hanno periodo di validità."""
    DocumentCatalog = apps.get_model("documents", "DocumentCatalog")
    DocumentCatalog.objects.filter(requires_renewal=False).update(
        validity_period_days=None
    )


def restore_validity(apps, schema_editor):
    DocumentCatalog = apps.get_model("documents", "DocumentCatalog")
    DocumentCatalog.objects.filter(validity_period_days__isnull=True).update(
        validity_period_days=0
    )


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0011_documentcatalog_reminder_days_renewal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="documentcatalog",
            name="is_required",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Indica se il documento è obbligatorio per la qualifica "
                    "del fornitore"
                ),
                verbose_name="È obbligatorio",
            ),
        ),
        migrations.AlterField(
            model_name="documentcatalog",
            name="validity_period_days",
            field=models.PositiveIntegerField(
                blank=True,
                default=365,
                help_text=(
                    "Solo per i documenti che richiedono rinnovo: giorni di "
                    "validità dalla data di emissione, usati per calcolare "
                    "la data di scadenza."
                ),
                null=True,
                verbose_name="Periodo validità (giorni)",
            ),
        ),
        migrations.RunPython(clear_validity_without_renewal, restore_validity),
    ]
