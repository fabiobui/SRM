from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0006_documentset"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="DocumentType",
            new_name="DocumentCatalog",
        ),
        migrations.RenameIndex(
            model_name="documentcatalog",
            old_name="documents_d_code_abe763_idx",
            new_name="documents_d_code_0b5080_idx",
        ),
        migrations.RenameIndex(
            model_name="documentcatalog",
            old_name="documents_d_documen_9c6fde_idx",
            new_name="documents_d_documen_a6b840_idx",
        ),
        migrations.RenameIndex(
            model_name="documentcatalog",
            old_name="documents_d_is_requ_5b4a7c_idx",
            new_name="documents_d_is_requ_f0c63b_idx",
        ),
        migrations.AlterModelOptions(
            name="documentcatalog",
            options={
                "ordering": ["document_category", "sort_order", "name"],
                "verbose_name": "Tipo di Documento",
                "verbose_name_plural": "Catalogo Documenti",
            },
        ),
        migrations.AlterModelOptions(
            name="document",
            options={
                "ordering": ["-uploaded_at"],
                "verbose_name": "Documento",
                "verbose_name_plural": "Registro Documenti",
            },
        ),
    ]
