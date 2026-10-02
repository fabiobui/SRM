import django.core.validators
from django.db import migrations, models

REMINDER_DAYS_DEFAULT = 30
VALIDITY_DAYS_DEFAULT = 365


def months_to_days(apps, schema_editor):
    """Converte il periodo da mesi a giorni (12 -> 365, 24 -> 730, ...) e
    allinea i campi di rinnovo: vuoti se il requisito non richiede rinnovo,
    valorizzati (default) se lo richiede."""
    Competence = apps.get_model("vendors", "Competence")
    for competence in Competence.objects.all():
        if competence.requires_renewal:
            months = competence.validity_period_days
            competence.validity_period_days = (
                round(months * 365 / 12) if months else VALIDITY_DAYS_DEFAULT
            )
            competence.reminder_days_before = REMINDER_DAYS_DEFAULT
        else:
            competence.validity_period_days = None
            competence.reminder_days_before = None
        competence.save(
            update_fields=["validity_period_days", "reminder_days_before"]
        )


def days_to_months(apps, schema_editor):
    Competence = apps.get_model("vendors", "Competence")
    for competence in Competence.objects.filter(
        validity_period_days__isnull=False
    ):
        competence.validity_period_days = round(
            competence.validity_period_days * 12 / 365
        )
        competence.save(update_fields=["validity_period_days"])


class Migration(migrations.Migration):
    dependencies = [
        ("vendors", "0048_vendor_expiry_notifications_expiryreminderlog"),
    ]

    operations = [
        migrations.RenameField(
            model_name="competence",
            old_name="renewal_period_months",
            new_name="validity_period_days",
        ),
        migrations.AlterField(
            model_name="competence",
            name="validity_period_days",
            field=models.PositiveIntegerField(
                blank=True,
                default=VALIDITY_DAYS_DEFAULT,
                help_text=(
                    "Solo per i requisiti che richiedono rinnovo: giorni di "
                    "validità dalla data di rilascio, usati per calcolare la "
                    "data di scadenza (es. 365, 730, 1095)."
                ),
                null=True,
                verbose_name="Periodo validità (giorni)",
            ),
        ),
        migrations.AddField(
            model_name="competence",
            name="reminder_days_before",
            field=models.PositiveIntegerField(
                blank=True,
                default=REMINDER_DAYS_DEFAULT,
                help_text=(
                    "Solo per i requisiti che richiedono rinnovo (tra 10 e "
                    "90): giorni prima della scadenza in cui il requisito "
                    "passa a EXPIRING_SOON e parte il primo promemoria email "
                    "al fornitore. Il secondo promemoria parte sempre a 7 "
                    "giorni."
                ),
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(10),
                    django.core.validators.MaxValueValidator(90),
                ],
                verbose_name="Giorni di preavviso scadenza",
            ),
        ),
        migrations.RunPython(months_to_days, days_to_months),
    ]
