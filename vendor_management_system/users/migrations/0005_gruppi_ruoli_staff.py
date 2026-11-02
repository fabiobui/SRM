from django.db import migrations
from django.db.models import Q

# Nomi dei gruppi prima di questa migrazione, da rinominare in place.
GRUPPI_RINOMINATI = {
    "Administrators": "Admin",
    "BackOffice Users": "BO User",
}
GRUPPO_PER_RUOLO = {
    "admin": "Admin",
    "bo_user": "BO User",
    "vendor": "Vendors",
}


def allinea_gruppi_e_staff(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("users", "User")
    Appartenenza = User.groups.through

    for vecchio, nuovo in GRUPPI_RINOMINATI.items():
        gruppo_vecchio = Group.objects.filter(name=vecchio).first()
        if gruppo_vecchio is None:
            continue
        if Group.objects.filter(name=nuovo).exists():
            gruppo_vecchio.delete()
        else:
            gruppo_vecchio.name = nuovo
            gruppo_vecchio.save(update_fields=["name"])

    for nome in GRUPPO_PER_RUOLO.values():
        Group.objects.get_or_create(name=nome)
    gruppi = {
        g.name: g
        for g in Group.objects.filter(name__in=GRUPPO_PER_RUOLO.values())
    }

    # Il gruppo dipende solo dal ruolo: si rifanno tutte le appartenenze.
    Appartenenza.objects.all().delete()
    Appartenenza.objects.bulk_create(
        [
            Appartenenza(
                user_id=utente.pk,
                group_id=gruppi[GRUPPO_PER_RUOLO[utente.role]].pk,
            )
            for utente in User.objects.all()
            if utente.role in GRUPPO_PER_RUOLO
        ]
    )

    User.objects.filter(Q(role="admin") | Q(is_superuser=True)).update(
        is_staff=True
    )
    User.objects.exclude(Q(role="admin") | Q(is_superuser=True)).update(
        is_staff=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_alter_user_managers"),
    ]

    operations = [
        migrations.RunPython(
            allinea_gruppi_e_staff, migrations.RunPython.noop
        ),
    ]
