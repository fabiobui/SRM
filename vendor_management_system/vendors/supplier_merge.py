"""Accorpamento dei fornitori censiti più volte (uno per società).

Si accorpano solo i fornitori GIÀ presenti in anagrafica, agganciati alle
viste FABRIC_HUB tramite il conto Embyon della loro sezione società. Per
ogni codice SAGE con più fornitori:

- il superstite è il record con la modifica più recente (storico admin,
  richieste dal portale, aggiornamenti di documenti/requisiti/servizi/
  contratti); la sua anagrafica resta, i campi vuoti si completano dagli
  altri record, senza sovrascrivere nulla;
- documenti, requisiti, servizi, contratti e valutazioni restano nella
  sezione della società d'origine; le sezioni (con la loro qualifica) e
  tutti gli altri collegamenti (utenti portale, richieste, tecnici e mezzi,
  promemoria, ordini...) passano al superstite;
- i gruppi con due record della stessa società o con conflitti di
  collegamento nelle viste vengono saltati e riportati, mai forzati.

I fornitori non agganciati restano invariati e finiscono nel report dei
codici Embyon non presenti nelle viste.
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.db import transaction
from django.db.models import Max

from vendor_management_system.documents.models import Document
from vendor_management_system.vendors.models import (
    COMMON_SECTION,
    Company,
    Contract,
    Vendor,
    VendorCompetence,
    VendorEvaluation,
    VendorOperationalAttributes,
    VendorService,
    collapse_account_code,
)

REPORTS_DIR = Path(settings.BASE_DIR) / "data_migration_scripts" / "reports"

SECTION_MODELS = [Document, VendorCompetence, VendorService, Contract]
SECTION_MODELS += [VendorEvaluation]

# Campi anagrafici completati dai record accorpati se vuoti nel superstite.
FILLABLE_FIELDS = [
    "vat_number",
    "fiscal_code",
    "email",
    "pec",
    "phone",
    "website",
    "reference_contact",
    "contact_details",
    "address",
    "category",
    "vendor_type",
    "managed_by",
    "first_supply_date",
    "date_of_establishment",
    "sage_code",
]


def _is_placeholder(code):
    return (code or "").upper().startswith("XLS")


def match_vendors(company_rows):
    """Aggancia i fornitori alle viste. Restituisce (gruppi per SAGE,
    non agganciati) dove i non agganciati sono (vendor, motivo, dettaglio)."""
    by_account = {}
    by_code = defaultdict(set)
    conflicts = set()
    for row in company_rows:
        by_account[(row["company"], row["account_code"])] = row
        by_code[row["account_code"]].add(row["company"])
        if row["link_conflict"]:
            conflicts.add(row["sage_code"])

    embyon_to_company = {
        c.embyon_company: c.code
        for c in Company.objects.real()
        if c.embyon_company
    }
    groups = defaultdict(list)
    unmatched = []
    vendors = Vendor.objects.prefetch_related("company_sections__accounts")
    for vendor in vendors:
        code = collapse_account_code(vendor.old_code)
        sections = list(vendor.company_sections.all())
        accounts = [
            (s.company_id, a.account_code)
            for s in sections
            for a in s.accounts.all()
        ]
        if not accounts and code and not _is_placeholder(code):
            company = embyon_to_company.get(vendor.embyon_company)
            if company:
                accounts = [(company, code)]
        sage_codes = {
            by_account[key]["sage_code"]
            for key in accounts
            if key in by_account
        }
        if vendor.sage_code:
            sage_codes.add(vendor.sage_code)
        if len(sage_codes) == 1:
            sage = sage_codes.pop()
            if sage in conflicts:
                unmatched.append((vendor, "link_conflict", sage))
            else:
                groups[sage].append(vendor)
            continue
        if len(sage_codes) > 1:
            detail = ", ".join(sorted(sage_codes))
            unmatched.append((vendor, "sage_ambiguo", detail))
        elif not code:
            unmatched.append((vendor, "senza_codice", ""))
        elif _is_placeholder(code):
            unmatched.append((vendor, "placeholder_xls", code))
        elif not vendor.embyon_company:
            unmatched.append((vendor, "senza_societa", code))
        else:
            other = by_code.get(code) or set()
            reason = "societa_diversa" if other else "non_trovato"
            unmatched.append((vendor, reason, ", ".join(sorted(other))))
    return groups, unmatched


def last_activity(vendor):
    """Data dell'ultima modifica nota del fornitore (o None)."""
    content_type = ContentType.objects.get_for_model(Vendor)
    dates = [
        LogEntry.objects.filter(
            content_type=content_type, object_id=vendor.pk
        ).aggregate(m=Max("action_time"))["m"]
    ]
    for model, field in (
        (Document, "uploaded_at"),
        (Document, "reviewed_at"),
        (VendorCompetence, "updated_at"),
        (VendorService, "updated_at"),
        (Contract, "updated_at"),
    ):
        dates.append(
            model.objects.filter(vendor=vendor).aggregate(m=Max(field))["m"]
        )
    from vendor_management_system.portal.models import VendorChangeRequest

    for field in ("created_at", "reviewed_at"):
        dates.append(
            VendorChangeRequest.objects.filter(vendor=vendor).aggregate(
                m=Max(field)
            )["m"]
        )
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def _children_count(vendor):
    return sum(m.objects.filter(vendor=vendor).count() for m in SECTION_MODELS)


def choose_survivor(vendors, forced=None):
    """Il record con la modifica più recente; a parità chi ha più elementi
    collegati, poi il codice fornitore. `forced` = vendor_code imposto."""
    if forced:
        for vendor in vendors:
            if vendor.pk == forced:
                return vendor

    def key(vendor):
        activity = last_activity(vendor)
        return (
            activity is not None,
            activity.timestamp() if activity else 0,
            _children_count(vendor),
            vendor.pk,
        )

    return max(vendors, key=key)


def group_skip_reason(vendors):
    """Motivo per non accorpare automaticamente un gruppo (o None)."""
    seen = defaultdict(list)
    for vendor in vendors:
        for section in vendor.company_sections.all():
            seen[section.company_id].append(vendor.pk)
    clashes = [code for code, pks in seen.items() if len(pks) > 1]
    if clashes:
        return "stessa_societa: " + ", ".join(sorted(clashes))
    return None


def _backup(donor, directory):
    directory.mkdir(parents=True, exist_ok=True)
    payload = serializers.serialize("json", [donor])
    (directory / f"{donor.pk}.json").write_text(payload, encoding="utf-8")


def _move_common_items(donor):
    """Elementi del donatore rimasti nella sezione Comune: passano alla sua
    sezione società d'origine (regola: niente va in Comune nell'accorpamento,
    e così non si scontrano con quelli del superstite)."""
    sections = list(
        donor.company_sections.values_list("company_id", flat=True)
    )
    if len(sections) != 1:
        return
    for model in SECTION_MODELS:
        model.objects.filter(vendor=donor, company_id=COMMON_SECTION).update(
            company_id=sections[0]
        )


def merge_into(survivor, donor, sage_code, backup_dir=None):
    """Accorpa `donor` in `survivor` e cancella `donor`. Restituisce il
    conteggio degli elementi spostati per modello."""
    moved = {}
    if backup_dir is not None:
        _backup(donor, backup_dir)
    _move_common_items(donor)

    # Attributi operativi (uno solo per fornitore): restano quelli del
    # superstite, completati con i campi vuoti del donatore.
    donor_attrs = VendorOperationalAttributes.objects.filter(
        vendor=donor
    ).first()
    if donor_attrs is not None:
        survivor_attrs = VendorOperationalAttributes.objects.filter(
            vendor=survivor
        ).first()
        if survivor_attrs is None:
            donor_attrs.vendor = survivor
            donor_attrs.save()
        else:
            for field in donor_attrs._meta.concrete_fields:
                if field.primary_key or field.name == "vendor":
                    continue
                if getattr(survivor_attrs, field.attname) in (None, ""):
                    setattr(
                        survivor_attrs,
                        field.attname,
                        getattr(donor_attrs, field.attname),
                    )
            survivor_attrs.save()
            donor_attrs.delete()

    for rel in Vendor._meta.related_objects:
        if rel.one_to_one:
            continue
        field = rel.field
        model = rel.related_model
        if rel.many_to_many:
            accessor = rel.get_accessor_name()
            for obj in getattr(donor, accessor).all():
                getattr(obj, field.name).add(survivor)
            continue
        count = model.objects.filter(**{field.name: donor}).update(
            **{field.name: survivor}
        )
        if count:
            moved[model._meta.label] = moved.get(model._meta.label, 0) + count

    for field in Vendor._meta.many_to_many:
        # Le M2M con tabella "through" (requisiti, servizi) sono già passate
        # con lo spostamento delle loro righe.
        if not field.remote_field.through._meta.auto_created:
            continue
        getattr(survivor, field.name).add(*getattr(donor, field.name).all())
    if donor.managed_by_id and donor.managed_by_id != survivor.managed_by_id:
        survivor.secondary_managers.add(donor.managed_by_id)

    for name in FILLABLE_FIELDS:
        field = Vendor._meta.get_field(name)
        if getattr(survivor, field.attname) in (None, "") and name != (
            "sage_code"
        ):
            setattr(survivor, field.attname, getattr(donor, field.attname))
    survivor.sage_code = sage_code
    Vendor.objects.filter(pk=donor.pk).delete()
    survivor.save()
    survivor.refresh_aggregate_qualification()
    return moved


def merge_shared_suppliers(
    company_rows,
    apply=False,
    survivor_map=None,
    only_sage=None,
    backup_dir=None,
):
    """Pianifica (e con `apply` esegue) l'accorpamento. Restituisce il
    riepilogo con righe pronte per i report CSV."""
    survivor_map = survivor_map or {}
    groups, unmatched = match_vendors(company_rows)
    plan, skipped, linked = [], [], []
    for sage, vendors in sorted(groups.items()):
        if only_sage and sage != only_sage:
            continue
        if len(vendors) == 1:
            vendor = vendors[0]
            if vendor.sage_code != sage:
                linked.append((vendor, sage))
                if apply:
                    Vendor.objects.filter(pk=vendor.pk).update(sage_code=sage)
            continue
        reason = group_skip_reason(vendors)
        if reason:
            skipped.append((sage, vendors, reason))
            continue
        survivor = choose_survivor(vendors, survivor_map.get(sage))
        donors = [v for v in vendors if v.pk != survivor.pk]
        entry = {"sage": sage, "survivor": survivor, "donors": donors}
        if apply:
            with transaction.atomic():
                entry["moved"] = {}
                for donor in donors:
                    for label, n in merge_into(
                        survivor, donor, sage, backup_dir
                    ).items():
                        entry["moved"][label] = (
                            entry["moved"].get(label, 0) + n
                        )
        plan.append(entry)
    return {
        "merged": plan,
        "skipped": skipped,
        "linked": linked,
        "unmatched": unmatched,
    }


def _vendor_cells(vendor):
    return [
        vendor.pk,
        vendor.name,
        vendor.old_code or "",
        vendor.embyon_company or "",
        vendor.vat_number or "",
        vendor.fiscal_code or "",
    ]


def write_reports(summary, directory=REPORTS_DIR):
    """Scrive i CSV di esito (cartella non servita da Django: contengono
    dati dei fornitori)."""
    directory.mkdir(parents=True, exist_ok=True)
    head = [
        "codice_fornitore",
        "ragione_sociale",
        "codice_embyon",
        "societa_embyon",
        "partita_iva",
        "codice_fiscale",
    ]
    with open(
        directory / "merge_report.csv", "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["sage_code", "ruolo", *head, "elementi_spostati"])
        for entry in summary["merged"]:
            moved = json.dumps(entry.get("moved", {}), ensure_ascii=False)
            w.writerow(
                [
                    entry["sage"],
                    "superstite",
                    *_vendor_cells(entry["survivor"]),
                    "",
                ]
            )
            for donor in entry["donors"]:
                w.writerow(
                    [entry["sage"], "accorpato", *_vendor_cells(donor), moved]
                )
    with open(
        directory / "merge_skipped.csv", "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["sage_code", "motivo", *head])
        for sage, vendors, reason in summary["skipped"]:
            for vendor in vendors:
                w.writerow([sage, reason, *_vendor_cells(vendor)])
    with open(
        directory / "embyon_codes_not_in_views.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([*head, "motivo", "dettaglio"])
        for vendor, reason, detail in summary["unmatched"]:
            w.writerow([*_vendor_cells(vendor), reason, detail])
