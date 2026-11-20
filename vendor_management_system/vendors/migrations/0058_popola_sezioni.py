"""Crea le sezioni società dai dati esistenti.

Per ogni fornitore con "Società Embyon" crea la sezione di quella società,
copiandoci la qualifica attuale e il codice Embyon come conto, e sposta in
quella sezione documenti, requisiti, servizi, contratti e valutazioni. I
fornitori senza società restano con tutto nella sezione Comune.
Imposta infine l'ambito "Comune" sui tipi di documento dell'entità
fornitore e su tutti i requisiti professionali esistenti.
"""

from django.db import migrations

# Documenti dell'entità giuridica, uguali per tutte le società del gruppo.
COMMON_DOCUMENT_CODES = [
    "DURC",
    "VISURA_CAM",
    "CERT_PREF",
    "CASELLARIO",
    "STAT_SOC",
    "ATTO_COST",
    "DOC_IDENT",
    "BILAN_ULT",
    "CERT_BANC",
    "RC_PROF",
    "RC_OPER",
    "INF_INAIL",
    "POLIZZA",
    "ISO_9001",
    "ISO_14001",
    "ISO_45001",
    "ISO_50001",
    "SA8000-CERT",
    "CERT_LAB",
    "AUT_SAN",
    "ITP",
    "DVR",
    "FORM_LAVORAT",
    "ORG_TECN",
    "ATTREZZA",
    "REF_TECN",
    "CV",
]

CHILD_MODELS = [
    ("documents", "Document"),
    ("vendors", "VendorCompetence"),
    ("vendors", "VendorService"),
    ("vendors", "Contract"),
    ("vendors", "VendorEvaluation"),
]


def collapse(code):
    return " ".join((code or "").split())


def forward_sections(apps, schema_editor):
    Company = apps.get_model("vendors", "Company")
    Vendor = apps.get_model("vendors", "Vendor")
    VendorCompany = apps.get_model("vendors", "VendorCompany")
    Account = apps.get_model("vendors", "VendorCompanyAccount")

    by_embyon = {
        c.embyon_company: c
        for c in Company.objects.filter(is_common=False)
        if c.embyon_company
    }
    used_accounts = set(Account.objects.values_list("company", "account_code"))
    for embyon, company in by_embyon.items():
        vendors = Vendor.objects.filter(embyon_company=embyon)
        for vendor in vendors.iterator():
            section, _ = VendorCompany.objects.get_or_create(
                vendor=vendor,
                company=company,
                defaults={
                    "qualification_status": vendor.qualification_status
                    or "PENDING",
                    "qualification_score": vendor.qualification_score,
                    "qualification_date": vendor.qualification_date,
                    "qualification_expiry": vendor.qualification_expiry,
                    "vendor_final_evaluation": vendor.vendor_final_evaluation
                    or "DA VALUTARE",
                    "embyon_active": vendor.embyon_active,
                    "last_audit_date": vendor.last_audit_date,
                    "next_audit_due": vendor.next_audit_due,
                    "review_notes": vendor.review_notes or "",
                },
            )
            code = collapse(vendor.old_code)
            key = (company.code, code)
            if code and not code.upper().startswith("XLS"):
                if key not in used_accounts:
                    Account.objects.create(
                        section=section,
                        company=company,
                        account_code=code,
                        status="ATTIVO" if vendor.embyon_active else "",
                        embyon_active=vendor.embyon_active,
                        link_source="vms",
                    )
                    used_accounts.add(key)
        for app_label, model_name in CHILD_MODELS:
            model = apps.get_model(app_label, model_name)
            model.objects.filter(vendor__embyon_company=embyon).update(
                company=company
            )

    DocumentCatalog = apps.get_model("documents", "DocumentCatalog")
    DocumentCatalog.objects.filter(code__in=COMMON_DOCUMENT_CODES).update(
        scope="COMMON"
    )
    Competence = apps.get_model("vendors", "Competence")
    Competence.objects.update(scope="COMMON")


def backward_sections(apps, schema_editor):
    for app_label, model_name in CHILD_MODELS:
        apps.get_model(app_label, model_name).objects.update(company="COMUNE")
    apps.get_model("vendors", "VendorCompany").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("vendors", "0057_societa_sezioni"),
        ("documents", "0014_sezione_documenti"),
    ]

    operations = [
        migrations.RunPython(forward_sections, backward_sections),
    ]
