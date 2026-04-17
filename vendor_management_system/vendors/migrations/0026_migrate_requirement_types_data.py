# Data migration: populate VendorCompetence type flags from Competence.requirement_type,
# then merge COMP/QUAL codes into REQ

from django.db import migrations


def migrate_requirement_types(apps, schema_editor):
    Competence = apps.get_model('vendors', 'Competence')
    VendorCompetence = apps.get_model('vendors', 'VendorCompetence')

    # Step 1: Set boolean flags on VendorCompetence based on Competence.requirement_type
    for vc in VendorCompetence.objects.select_related('competence').all():
        req_type = vc.competence.requirement_type or ''
        if req_type == 'competenza':
            vc.is_competenza = True
        elif req_type == 'qualifica':
            vc.is_qualifica = True
        elif req_type == 'iscrizione_albo':
            vc.is_iscrizione_albo = True
        vc.save(update_fields=['is_competenza', 'is_qualifica', 'is_iscrizione_albo'])

    # Step 2: Merge COMP-xxx and QUAL-xxx pairs into REQ-xxx
    comp_entries = {}
    for c in Competence.objects.filter(code__startswith='COMP-'):
        number = c.code.replace('COMP-', '')
        comp_entries[number] = c

    qual_entries = {}
    for c in Competence.objects.filter(code__startswith='QUAL-'):
        number = c.code.replace('QUAL-', '')
        qual_entries[number] = c

    # Merge pairs: both COMP-xxx and QUAL-xxx exist with same number
    for number in set(comp_entries.keys()) & set(qual_entries.keys()):
        comp_obj = comp_entries[number]
        qual_obj = qual_entries[number]

        # Keep the COMP entry as the merged REQ entry
        comp_obj.code = f'REQ-{number}'
        comp_obj.save(update_fields=['code'])

        # Update VendorCompetence: those from QUAL get both flags
        for vc in VendorCompetence.objects.filter(competence=qual_obj):
            existing = VendorCompetence.objects.filter(
                vendor=vc.vendor, competence=comp_obj
            ).first()
            if existing:
                # Merge data into existing assignment
                existing.is_competenza = True
                existing.is_qualifica = True
                if vc.has_certification and not existing.has_certification:
                    existing.has_certification = True
                if vc.certification_number and not existing.certification_number:
                    existing.certification_number = vc.certification_number
                if vc.certification_body and not existing.certification_body:
                    existing.certification_body = vc.certification_body
                if vc.issue_date and (not existing.issue_date or vc.issue_date > existing.issue_date):
                    existing.issue_date = vc.issue_date
                if vc.expiry_date and (not existing.expiry_date or vc.expiry_date > existing.expiry_date):
                    existing.expiry_date = vc.expiry_date
                if vc.verified:
                    existing.verified = True
                existing.save()
                vc.delete()
            else:
                # Reassign to the merged competence, set both flags
                vc.competence = comp_obj
                vc.is_competenza = True
                vc.is_qualifica = True
                vc.save(update_fields=['competence', 'is_competenza', 'is_qualifica'])

        # Also set both flags on existing COMP assignments
        VendorCompetence.objects.filter(competence=comp_obj).update(
            is_competenza=True, is_qualifica=True
        )

        # Delete the QUAL entry (now orphaned)
        qual_obj.delete()

    # Step 3: Rename remaining standalone COMP-xxx to REQ-xxx
    for number, comp_obj in comp_entries.items():
        if number not in qual_entries:
            comp_obj.code = f'REQ-{number}'
            comp_obj.save(update_fields=['code'])

    # Step 4: Rename remaining standalone QUAL-xxx to REQ-xxx
    for number, qual_obj in qual_entries.items():
        if number not in comp_entries:
            qual_obj.code = f'REQ-{number}'
            qual_obj.save(update_fields=['code'])

    # ISCR-xxx entries are left as-is


def reverse_migration(apps, schema_editor):
    """Best-effort rollback: copy flags back to requirement_type."""
    VendorCompetence = apps.get_model('vendors', 'VendorCompetence')
    Competence = apps.get_model('vendors', 'Competence')

    # Set requirement_type based on first VendorCompetence found for each competence
    for comp in Competence.objects.all():
        vc = VendorCompetence.objects.filter(competence=comp).first()
        if vc:
            if vc.is_iscrizione_albo:
                comp.requirement_type = 'iscrizione_albo'
            elif vc.is_qualifica:
                comp.requirement_type = 'qualifica'
            elif vc.is_competenza:
                comp.requirement_type = 'competenza'
            comp.save(update_fields=['requirement_type'])


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0025_restructure_competence_requirement_types'),
    ]

    operations = [
        migrations.RunPython(migrate_requirement_types, reverse_migration),
    ]
