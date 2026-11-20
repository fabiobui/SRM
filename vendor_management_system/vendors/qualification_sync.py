"""Riallineamento periodico di stato di qualifica e Valutazione Finale.

I segnali aggiornano lo stato quando cambiano documenti e requisiti, ma una
scadenza che arriva "da sola" non genera alcuna modifica: il job giornaliero
(``tasks.sync_qualification_status_task``) e il comando
``sync_qualification_status`` usano ``sync_all`` per recuperarle.
"""

from django.utils import timezone

from vendor_management_system.documents.models import Document
from vendor_management_system.vendors.models import Vendor, VendorCompany


def sync_all(dry_run=False):
    """Porta a 'Da Revisionare' gli Approvati con obbligatori non in regola
    (non riapprova mai nessuno) e riallinea i bollini. Restituisce il
    riepilogo: fornitori declassati (fornitore, società, blocchi), numero di
    approvati esaminati (sezioni società e fornitori senza sezioni) e di
    bollini corretti. Prima porta a "Scaduto" lo stato salvato dei documenti
    la cui scadenza è passata."""
    scaduti = Document.objects.filter(
        expiry_date__lt=timezone.now().date(),
        status__in=("PENDING", "UPLOADED", "APPROVED"),
    )
    expired_documents = scaduti.count()
    if not dry_run:
        scaduti.update(status="EXPIRED")
    # Chi porta la qualifica: le sezioni società e i fornitori senza sezioni.
    holders = list(
        VendorCompany.objects.filter(
            qualification_status="APPROVED"
        ).select_related("vendor", "company")
    ) + list(
        Vendor.objects.filter(
            qualification_status="APPROVED", company_sections__isnull=True
        )
    )
    downgraded = []
    for holder in holders:
        blockers = holder.qualification_blockers
        if not blockers:
            continue
        if isinstance(holder, VendorCompany):
            downgraded.append((holder.vendor, holder.company.label, blockers))
        else:
            downgraded.append((holder, "", blockers))
        if not dry_run:
            holder.sync_qualification_status()
    realigned = 0 if dry_run else Vendor.realign_final_evaluations()
    return {
        "downgraded": downgraded,
        "approved": len(holders),
        "realigned": realigned,
        "expired_documents": expired_documents,
    }
