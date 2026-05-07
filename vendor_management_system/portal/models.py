import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class VendorChangeRequest(models.Model):
    """Richiesta di modifica dell'anagrafica fornitore proposta dal fornitore stesso.

    Il fornitore non modifica direttamente il record `Vendor`: invia una richiesta
    in stato PENDING che il back-office approva o rifiuta. Alla approvazione,
    le modifiche memorizzate in `changes` (JSON) vengono applicate al `Vendor`.
    """

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("In attesa")),
        (STATUS_APPROVED, _("Approvata")),
        (STATUS_REJECTED, _("Respinta")),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        verbose_name=_("Fornitore"),
        related_name="change_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendor_change_requests",
        verbose_name=_("Richiesto da"),
    )
    # Diff dei campi modificati: { field_name: {"old": ..., "new": ...} }
    changes = models.JSONField(
        _("Modifiche proposte"),
        default=dict,
        help_text=_("Mappa {campo: {'old': valore_attuale, 'new': valore_proposto}}"),
    )
    status = models.CharField(
        _("Stato"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(_("Creata il"), auto_now_add=True)
    reviewed_at = models.DateTimeField(_("Revisionata il"), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_vendor_change_requests",
        verbose_name=_("Revisionata da"),
    )
    review_notes = models.TextField(_("Note di revisione"), blank=True)

    class Meta:
        verbose_name = _("Richiesta modifica anagrafica")
        verbose_name_plural = _("Richieste modifica anagrafica")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.vendor.name} — {self.get_status_display()} ({self.created_at:%d/%m/%Y})"

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    def apply_to_vendor(self, reviewer, notes: str = ""):
        """Applica le modifiche al Vendor e marca la richiesta APPROVED.

        I campi accettati sono solo quelli presenti come attributi del modello Vendor.
        Eventuali campi sconosciuti vengono ignorati per sicurezza.
        """
        if self.status != self.STATUS_PENDING:
            raise ValueError("Solo richieste in stato PENDING possono essere approvate.")

        vendor = self.vendor
        for field, payload in (self.changes or {}).items():
            if not hasattr(vendor, field):
                continue
            new_value = payload.get("new") if isinstance(payload, dict) else payload
            setattr(vendor, field, new_value)
        vendor.save()

        self.status = self.STATUS_APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.review_notes = notes or self.review_notes
        self.save()

    def reject(self, reviewer, notes: str = ""):
        if self.status != self.STATUS_PENDING:
            raise ValueError("Solo richieste in stato PENDING possono essere rifiutate.")
        self.status = self.STATUS_REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.review_notes = notes or self.review_notes
        self.save()
