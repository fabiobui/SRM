# Step 3: Remove old requirement_type field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0026_migrate_requirement_types_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='competence',
            name='requirement_type',
        ),
    ]
