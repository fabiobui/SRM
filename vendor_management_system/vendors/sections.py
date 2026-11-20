"""Sezioni del fornitore (Comune + una per società) e chi può modificarle.

Regola: la sezione Comune è modificabile da tutti gli Admin; la sezione di
una società solo dagli Admin di quella società (``User.company``, da LDAP).
Il superuser modifica tutto. La revisione back office segue la stessa
regola per i BO User. Chi non ha una società modifica solo la Comune.
"""

from django.utils import timezone

from vendor_management_system.vendors.models import (
    COMMON_SECTION,
    SCOPE_COMMON,
    Company,
    Vendor,
    VendorCompany,
    VendorCompanyAccount,
    collapse_account_code,
)

SECTION_PARAM = "sezione"


def _same_company(user, code):
    return bool(code) and code == getattr(user, "company_id", None)


def can_edit_section(user, code):
    """L'utente può modificare la sezione `code` del fornitore?"""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    if getattr(user, "role", None) != "admin":
        return False
    return code == COMMON_SECTION or _same_company(user, code)


def can_review_section(user, code):
    """L'utente può approvare/respingere gli elementi della sezione?"""
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    if getattr(user, "role", None) not in ("admin", "bo_user"):
        return False
    return code == COMMON_SECTION or _same_company(user, code)


def reviewable_sections(user):
    """Codici di sezione che l'utente può rivedere; None = tutte."""
    if getattr(user, "is_superuser", False):
        return None
    codes = [COMMON_SECTION]
    if getattr(user, "company_id", None):
        codes.append(user.company_id)
    return codes


def vendor_sections(vendor):
    """Sezioni del fornitore in ordine: Comune, poi le società."""
    common = Company.objects.get(code=COMMON_SECTION)
    companies = [
        s.company
        for s in VendorCompany.objects.filter(vendor=vendor).select_related(
            "company"
        )
    ]
    return [common, *companies]


def resolve_section(vendor, code):
    """Company della sezione `code` se il fornitore ce l'ha, altrimenti None.
    La sezione Comune esiste sempre."""
    if not code:
        return None
    code = code.upper()
    if code == COMMON_SECTION:
        return Company.objects.filter(code=COMMON_SECTION).first()
    section = (
        VendorCompany.objects.filter(vendor=vendor, company_id=code)
        .select_related("company")
        .first()
    )
    return section.company if section else None


def default_section_for(vendor, catalog_scope):
    """Sezione di default di un elemento nuovo caricato senza indicazione
    (portale): Comune se il tipo è comune o se il fornitore lavora con più
    società (decide poi il back office), altrimenti l'unica società."""
    if catalog_scope == SCOPE_COMMON:
        return COMMON_SECTION, True
    codes = list(
        VendorCompany.objects.filter(vendor=vendor).values_list(
            "company_id", flat=True
        )
    )
    if len(codes) == 1:
        return codes[0], True
    return COMMON_SECTION, not codes


def duplicates_in_other_sections(queryset, current_code):
    """Elementi dello stesso tipo già presenti in altre sezioni."""
    return queryset.exclude(company_id=current_code).select_related("company")


def create_section_with_accounts(vendor, company, accounts):
    """Crea (se manca) la sezione `company` del fornitore e i suoi conti.

    `accounts` sono righe normalizzate di v_supplier_companies (chiavi
    company, account_code, status, embyon_active, ...): si usano solo quelle
    della società, saltando i conti già assegnati ad altri fornitori."""
    section, _ = VendorCompany.objects.get_or_create(
        vendor=vendor, company=company
    )
    for row in accounts:
        if (row.get("company") or "").upper() != company.code:
            continue
        code = collapse_account_code(row.get("account_code"))
        if not code:
            continue
        taken = VendorCompanyAccount.objects.filter(
            company=company, account_code=code
        ).exclude(section=section)
        if taken.exists():
            continue
        VendorCompanyAccount.objects.update_or_create(
            section=section,
            account_code=code,
            defaults={
                "company": company,
                "status": row.get("status") or "",
                "embyon_active": bool(row.get("embyon_active", True)),
                "link_source": row.get("link_source") or "",
                "link_conflict": bool(row.get("link_conflict")),
                "in_embyon": bool(row.get("in_embyon", True)),
                "last_synced_at": timezone.now(),
            },
        )
    refresh_section_embyon_active(section)
    return section


def refresh_section_embyon_active(section):
    """La sezione è attiva in Embyon se almeno un suo conto lo è (senza
    conti resta com'è)."""
    flags = list(section.accounts.values_list("embyon_active", flat=True))
    if flags and section.embyon_active != any(flags):
        section.embyon_active = any(flags)
        section.save()


def account_code_variants(code):
    """Grafie del conto Embyon presenti nei dati storici: "F 6546",
    "F  6546" (padding a 6 cifre come in Embyon), "F6546"."""
    collapsed = collapse_account_code(code)
    letters = "".join(ch for ch in collapsed if not ch.isdigit()).strip()
    digits = "".join(ch for ch in collapsed if ch.isdigit())
    variants = {collapsed, collapsed.replace(" ", "")}
    if letters and digits:
        variants.add(letters + digits.rjust(6))
    return [v for v in variants if v]


def find_registered_vendor(row):
    """Fornitore già censito per un risultato delle viste FABRIC_HUB: per
    codice SAGE, poi per conto di una sua società (sezioni o vecchio
    codice Embyon del record)."""
    sage = row.get("sage_code")
    if sage:
        vendor = Vendor.objects.filter(sage_code=sage).first()
        if vendor:
            return vendor
    for account in row.get("companies") or []:
        code = collapse_account_code(account.get("account_code"))
        if not code:
            continue
        found = (
            VendorCompanyAccount.objects.filter(
                company_id=account.get("company"), account_code=code
            )
            .select_related("section__vendor")
            .first()
        )
        if found:
            return found.section.vendor
        company = Company.objects.filter(pk=account.get("company")).first()
        legacy = Vendor.objects.filter(
            old_code__in=account_code_variants(code)
        )
        if company and company.embyon_company:
            legacy = legacy.filter(embyon_company=company.embyon_company)
        vendor = legacy.first()
        if vendor:
            return vendor
    return None


# Attributi operativi, tecnici e mezzi dei subappaltatori riguardano solo la
# società che lavora con i subappaltatori.
SUBCONTRACTOR_SECTION = "SICURA"


def subcontractor_section(vendor):
    """Sezione che ospita attributi operativi, tecnici e mezzi: Sicura se il
    fornitore ce l'ha, la Comune se non ha sezioni società (fornitori
    storici), altrimenti nessuna (None)."""
    codes = set(
        VendorCompany.objects.filter(vendor=vendor).values_list(
            "company_id", flat=True
        )
    )
    if not codes:
        return COMMON_SECTION
    return SUBCONTRACTOR_SECTION if SUBCONTRACTOR_SECTION in codes else None


def can_review_subcontractor(user, vendor):
    """Il BO può validare tecnici, mezzi e loro documenti del fornitore?"""
    code = subcontractor_section(vendor)
    return code is not None and can_review_section(user, code)
