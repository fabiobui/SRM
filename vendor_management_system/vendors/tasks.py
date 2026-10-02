import logging

from celery import shared_task

from vendor_management_system.vendors.expiry_reminders import (
    send_expiry_reminders,
)

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
