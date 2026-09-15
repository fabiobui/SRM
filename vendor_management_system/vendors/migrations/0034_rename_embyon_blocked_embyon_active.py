from django.db import migrations, models


def invert_embyon_flag(apps, schema_editor):
    """I valori esistenti rappresentavano 'bloccato in Embyon'; ora il campo
    rappresenta 'attivo in Embyon', quindi invertiamo i valori salvati."""
    Vendor = apps.get_model('vendors', 'Vendor')
    Vendor.objects.update(embyon_active=models.Case(
        models.When(embyon_active=True, then=models.Value(False)),
        default=models.Value(True),
        output_field=models.BooleanField(),
    ))


def revert_embyon_flag(apps, schema_editor):
    Vendor = apps.get_model('vendors', 'Vendor')
    Vendor.objects.update(embyon_active=models.Case(
        models.When(embyon_active=True, then=models.Value(False)),
        default=models.Value(True),
        output_field=models.BooleanField(),
    ))


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0033_merge_20260519_1411'),
    ]

    operations = [
        migrations.RenameField(
            model_name='vendor',
            old_name='embyon_blocked',
            new_name='embyon_active',
        ),
        migrations.AlterField(
            model_name='vendor',
            name='embyon_active',
            field=models.BooleanField(
                default=True,
                help_text='Indica se il fornitore risulta attivo in Embyon',
                verbose_name='Attivo in Embyon',
            ),
        ),
        migrations.RunPython(invert_embyon_flag, revert_embyon_flag),
    ]
