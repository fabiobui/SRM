import logging

from celery import shared_task

from vendor_management_system.vendors.expiry_reminders import (
    send_expiry_reminders,
)
from vendor_management_system.vendors.qualification_sync import sync_all
from vendor_management_system.vendors.supplier_sync import sync_suppliers

logger = logging.getLogger(__name__)


# Limiti più ampi di quelli globali (60s soft): un invio SMTP per fornitore
# può durare fino a EMAIL_TIMEOUT secondi.
@shared_task(soft_time_limit=15 * 60, time_limit=20 * 60)
def send_expiry_reminders_task():
    """Job giornaliero (Celery beat) dei promemoria scadenze al fornitore."""
    summary = send_expiry_reminders()
    logger.info(
        "Promemoria scadenze: %d fornitori notificati (%d elementi), "
        "%d invii non riusciti",
        len(summary["sent"]),
        summary["items"],
        len(summary["failed"]),
    )
    return {
        "sent": len(summary["sent"]),
        "items": summary["items"],
        "failed": len(summary["failed"]),
    }


@shared_task(soft_time_limit=15 * 60, time_limit=20 * 60)
def sync_qualification_status_task():
    """Job giornaliero (Celery beat): declassa gli Approvati con obbligatori
    scaduti o non in regola e riallinea la Valutazione Finale."""
    summary = sync_all()
    logger.info(
        "Sync qualifica: %d fornitori declassati su %d approvati, "
        "%d valutazioni finali riallineate",
        len(summary["downgraded"]),
        summary["approved"],
        summary["realigned"],
    )
    return {
        "downgraded": len(summary["downgraded"]),
        "approved": summary["approved"],
        "realigned": summary["realigned"],
    }


@shared_task(soft_time_limit=15 * 60, time_limit=20 * 60)
def sync_fabric_suppliers_task():
    """Job giornaliero (Celery beat): codice SAGE e conti Embyon dei
    fornitori censiti dalle viste FABRIC_HUB, prima del sync qualifica."""
    summary = sync_suppliers()
    logger.info(
        "Sync FABRIC_HUB: %d codici SAGE assegnati, %d conti aggiornati, "
        "%d aggiunti, %d candidati all'accorpamento",
        len(summary["sage_assigned"]),
        summary["accounts_updated"],
        summary["accounts_added"],
        len(summary["merge_candidates"]),
    )
    return {
        "sage_assigned": len(summary["sage_assigned"]),
        "accounts_updated": summary["accounts_updated"],
        "accounts_added": summary["accounts_added"],
        "merge_candidates": len(summary["merge_candidates"]),
    }
