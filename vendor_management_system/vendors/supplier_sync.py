"""Allineamento dei fornitori censiti con le viste FABRIC_HUB.

Lavora SOLO sui fornitori già presenti in anagrafica: non crea fornitori
nuovi e non aggiunge sezioni società. Per ogni fornitore:

- assegna il codice SAGE se i conti delle sue sezioni portano a un solo
  codice non ancora usato da un altro fornitore (altrimenti lo segnala come
  candidato all'accorpamento);
- aggiorna stato e flag dei conti esistenti e aggiunge gli altri conti della
  stessa società (un fornitore può averne più di uno);
- ricalcola "attivo in Embyon" di ogni sezione e quindi la Valutazione Finale.
"""

from collections import defaultdict

from django.db import transaction
from django.utils import timezone

from vendor_management_system.vendors import fabric_hub
from vendor_management_system.vendors.models import (
    Vendor,
    VendorCompany,
    VendorCompanyAccount,
    collapse_account_code,
)
from vendor_management_system.vendors.sections import (
    refresh_section_embyon_active,
)


def index_company_rows(rows):
    """Righe normalizzate di v_supplier_companies indicizzate per (società,
    conto) e per codice SAGE."""
    by_account, by_sage = {}, defaultdict(list)
    for row in rows:
        by_account[(row["company"], row["account_code"])] = row
        by_sage[row["sage_code"]].append(row)
    return by_account, by_sage


def _apply_row(account, row, now):
    account.status = row["status"]
    account.embyon_active = row["embyon_active"]
    account.link_source = row["link_source"]
    account.link_conflict = row["link_conflict"]
    account.in_embyon = row["in_embyon"]
    account.last_synced_at = now
    account.save()


def sync_suppliers(dry_run=False, company_rows=None):
    """Esegue l'allineamento; `company_rows` (righe normalizzate) permette
    ai test di non interrogare il servizio. Restituisce il riepilogo."""
    if company_rows is None:
        company_rows = [
            fabric_hub.normalize_company_row(r)
            for r in fabric_hub.all_supplier_companies()
        ]
    by_account, by_sage = index_company_rows(company_rows)
    now = timezone.now()
    summary = {
        "sage_assigned": [],
        "merge_candidates": [],
        "ambiguous": [],
        "accounts_updated": 0,
        "accounts_added": 0,
        "accounts_missing": [],
    }

    sections = VendorCompany.objects.select_related(
        "vendor", "company"
    ).prefetch_related("accounts")
    sections_by_vendor = defaultdict(list)
    for section in sections:
        sections_by_vendor[section.vendor_id].append(section)

    sage_owner = dict(
        Vendor.objects.exclude(sage_code__isnull=True)
        .exclude(sage_code="")
        .values_list("sage_code", "pk")
    )

    with transaction.atomic():
        for vendor_pk, vendor_sections in sections_by_vendor.items():
            vendor = vendor_sections[0].vendor
            sage = vendor.sage_code
            if not sage:
                found = {
                    by_account[key]["sage_code"]
                    for s in vendor_sections
                    for a in s.accounts.all()
                    if (key := (s.company_id, a.account_code)) in by_account
                }
                if len(found) > 1:
                    summary["ambiguous"].append((vendor, sorted(found)))
                    continue
                if not found:
                    continue
                sage = found.pop()
                owner = sage_owner.get(sage)
                if owner and owner != vendor_pk:
                    summary["merge_candidates"].append((vendor, sage, owner))
                    continue
                summary["sage_assigned"].append((vendor, sage))
                sage_owner[sage] = vendor_pk
                if not dry_run:
                    Vendor.objects.filter(pk=vendor_pk).update(sage_code=sage)

            rows_by_company = defaultdict(list)
            for row in by_sage.get(sage, []):
                rows_by_company[row["company"]].append(row)

            for section in vendor_sections:
                known = {a.account_code: a for a in section.accounts.all()}
                for code, account in known.items():
                    row = by_account.get((section.company_id, code))
                    if row is None:
                        summary["accounts_missing"].append(
                            (vendor, section.company_id, code)
                        )
                        continue
                    summary["accounts_updated"] += 1
                    if not dry_run:
                        _apply_row(account, row, now)
                for row in rows_by_company.get(section.company_id, []):
                    code = row["account_code"]
                    if code in known:
                        continue
                    taken = VendorCompanyAccount.objects.filter(
                        company_id=section.company_id, account_code=code
                    ).exists()
                    if taken:
                        continue
                    summary["accounts_added"] += 1
                    if not dry_run:
                        account = VendorCompanyAccount(
                            section=section,
                            company_id=section.company_id,
                            account_code=collapse_account_code(code),
                        )
                        _apply_row(account, row, now)
                if not dry_run:
                    refresh_section_embyon_active(section)
        if dry_run:
            transaction.set_rollback(True)
    return summary
