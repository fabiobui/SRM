"""Riallineamento periodico di stato di qualifica e Valutazione Finale.

I segnali aggiornano lo stato quando cambiano documenti e requisiti, ma una
scadenza che arriva "da sola" non genera alcuna modifica: il job giornaliero
(``tasks.sync_qualification_status_task``) e il comando
``sync_qualification_status`` usano ``sync_all`` per recuperarle.
"""

from vendor_management_system.vendors.models import Vendor


def sync_all(dry_run=False):
    """Porta a 'Da Revisionare' gli Approvati con obbligatori non in regola
    (non riapprova mai nessuno) e riallinea i bollini. Restituisce il
    riepilogo: fornitori declassati con i loro blocchi, numero di approvati
    esaminati e di bollini corretti."""
    approved = list(Vendor.objects.filter(qualification_status="APPROVED"))
    downgraded = []
    for vendor in approved:
        blockers = vendor.qualification_blockers
        if not blockers:
            continue
        downgraded.append((vendor, blockers))
        if not dry_run:
            vendor.sync_qualification_status()
    realigned = 0 if dry_run else Vendor.realign_final_evaluations()
    return {
        "downgraded": downgraded,
        "approved": len(approved),
        "realigned": realigned,
    }
