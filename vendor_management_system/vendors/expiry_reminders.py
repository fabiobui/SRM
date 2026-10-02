"""Promemoria email di scadenza documenti e abilitazioni verso il fornitore.

Il job giornaliero (``tasks.send_expiry_reminders_task``) e il comando
``send_expiry_reminders`` usano entrambi ``send_expiry_reminders``: una sola
email al giorno per fornitore, con tutti gli elementi in scadenza.

Riguarda solo tipi documento e requisiti che "richiedono rinnovo". Stadi:
primo promemoria entro la soglia (``reminder_days_before`` del tipo
documento o del requisito), ultimo avviso entro
``EXPIRY_REMINDER_SECOND_DAYS``. La finestra è "giorni rimanenti <= soglia",
quindi un giorno saltato dal job viene recuperato al giro dopo;
``ExpiryReminderLog`` impedisce i doppioni.
"""

import logging
from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from vendor_management_system.core.emails import send_templated_email
from vendor_management_system.documents.models import (
    REMINDER_DAYS_DEFAULT,
    REMINDER_DAYS_MAX,
    REMINDER_DAYS_MIN,
    Document,
)
from vendor_management_system.vendors.models import (
    ExpiryReminderLog,
    Vendor,
    VendorCompetence,
)

logger = logging.getLogger(__name__)

SUBJECT = "Promemoria scadenze - Albo Fornitori Fulgard"


@dataclass(frozen=True)
class ReminderItem:
    kind: str
    item_id: str
    label: str
    expiry_date: date
    days_left: int
    stage: str

    @property
    def kind_label(self):
        return dict(ExpiryReminderLog.KIND_CHOICES)[self.kind]

    @property
    def is_last_notice(self):
        return self.stage == ExpiryReminderLog.STAGE_SECOND


def first_threshold(catalog_item):
    """Soglia del primo promemoria di un tipo documento o requisito,
    riportata nei limiti del validator anche se a DB c'è un valore scritto
    senza passare dal form."""
    days = catalog_item.reminder_days_before or REMINDER_DAYS_DEFAULT
    return max(REMINDER_DAYS_MIN, min(REMINDER_DAYS_MAX, days))


def _stage(days_left, first_threshold):
    if days_left <= settings.EXPIRY_REMINDER_SECOND_DAYS:
        return ExpiryReminderLog.STAGE_SECOND
    if days_left <= first_threshold:
        return ExpiryReminderLog.STAGE_FIRST
    return None


def _candidates(vendor, today):
    # Solo tipi/requisiti che richiedono rinnovo: gli altri non hanno
    # preavviso e restano fuori dai promemoria.
    documents = Document.objects.filter(
        vendor=vendor,
        status="APPROVED",
        expiry_date__gte=today,
        document_type__requires_renewal=True,
    ).select_related("document_type")
    for doc in documents:
        yield (
            ExpiryReminderLog.KIND_DOCUMENT,
            str(doc.pk),
            doc.document_type.name,
            doc.expiry_date,
            first_threshold(doc.document_type),
        )
    competences = VendorCompetence.objects.filter(
        vendor=vendor,
        has_competence=True,
        expiry_date__gte=today,
        competence__requires_renewal=True,
    ).select_related("competence")
    for vc in competences:
        yield (
            ExpiryReminderLog.KIND_COMPETENCE,
            str(vc.pk),
            vc.competence.name,
            vc.expiry_date,
            first_threshold(vc.competence),
        )


def due_items(vendor, today):
    """Elementi del fornitore che oggi devono ricevere un promemoria non
    ancora inviato, ordinati per scadenza."""
    already_sent = set(
        ExpiryReminderLog.objects.filter(vendor=vendor).values_list(
            "item_kind", "item_id", "expiry_date", "stage"
        )
    )
    items = []
    for kind, item_id, label, expiry_date, threshold in _candidates(
        vendor, today
    ):
        days_left = (expiry_date - today).days
        stage = _stage(days_left, threshold)
        if stage and (kind, item_id, expiry_date, stage) not in already_sent:
            items.append(
                ReminderItem(
                    kind, item_id, label, expiry_date, days_left, stage
                )
            )
    return sorted(items, key=lambda item: (item.expiry_date, item.label))


def notifiable_vendors():
    return (
        Vendor.objects.filter(
            expiry_notifications_enabled=True, is_active=True
        )
        .exclude(Q(email__isnull=True) | Q(email=""))
        .order_by("name")
    )


def _portal_url():
    if not settings.PORTAL_BASE_URL:
        return ""
    # LOGIN_URL include già l'eventuale prefisso /fornitori.
    return f"{settings.PORTAL_BASE_URL}{settings.LOGIN_URL}"


def send_vendor_reminder(vendor, items):
    """Invia l'email e registra gli elementi notificati. Gli errori di invio
    vengono propagati (già loggati da send_templated_email)."""
    recipients = send_templated_email(
        subject=SUBJECT,
        template_name="expiry_reminder",
        context={
            "vendor": vendor,
            "greeting_name": vendor.reference_contact or vendor.name,
            "items": items,
            "has_last_notice": any(item.is_last_notice for item in items),
            "portal_url": _portal_url(),
        },
        to=[vendor.email],
    )
    ExpiryReminderLog.objects.bulk_create(
        [
            ExpiryReminderLog(
                vendor=vendor,
                item_kind=item.kind,
                item_id=item.item_id,
                item_label=item.label[:255],
                expiry_date=item.expiry_date,
                stage=item.stage,
                recipients=", ".join(recipients)[:500],
            )
            for item in items
        ],
        ignore_conflicts=True,
    )
    return recipients


def send_expiry_reminders(today=None, dry_run=False):
    """Invia i promemoria del giorno. Con ``dry_run`` non invia e non scrive
    log. Restituisce un riepilogo con i fornitori notificati e quelli in
    errore (che verranno ritentati al giro successivo)."""
    today = today or timezone.now().date()
    summary = {"sent": [], "failed": [], "items": 0}
    for vendor in notifiable_vendors():
        items = due_items(vendor, today)
        if not items:
            continue
        if not dry_run:
            try:
                send_vendor_reminder(vendor, items)
            except Exception:  # noqa: BLE001 - già loggato da send_templated_email
                summary["failed"].append((vendor, items))
                continue
        summary["sent"].append((vendor, items))
        summary["items"] += len(items)
    return summary
