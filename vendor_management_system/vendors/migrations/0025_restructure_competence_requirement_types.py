# Step 1: Add boolean type flags on VendorCompetence (keep requirement_type on Competence for now)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0024_competencezone_country_alter_vendor_competences_zone_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendorcompetence',
            name='is_competenza',
            field=models.BooleanField(default=False, help_text='Indica se il requisito è assegnato come competenza', verbose_name='Competenza'),
        ),
        migrations.AddField(
            model_name='vendorcompetence',
            name='is_iscrizione_albo',
            field=models.BooleanField(default=False, help_text="Indica se il requisito è un'iscrizione all'albo", verbose_name='Iscrizione Albo'),
        ),
        migrations.AddField(
            model_name='vendorcompetence',
            name='is_qualifica',
            field=models.BooleanField(default=False, help_text='Indica se il requisito è assegnato come qualifica', verbose_name='Qualifica'),
        ),
    ]
