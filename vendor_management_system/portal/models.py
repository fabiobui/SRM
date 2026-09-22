import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Whitelist server-side per i servizi: prezzo orario (hourly_rate) e
# contratto collegato (contract) restano di sola competenza back-office, non
# sono mai esposti in un form fornitore. Usata sia da `VendorServiceChangeForm`
# / `VendorServiceAddRequestForm` (portal/forms.py) sia da
# `VendorChangeRequest._create_vendor_service` qui sotto.
EDITABLE_VENDOR_SERVICE_FIELDS = (
    "is_primary",
    "start_date",
    "end_date",
    "notes",
)


class VendorChangeRequest(models.Model):
    """Richiesta di modifica dell'anagrafica, di un servizio esistente, o di
    aggiunta/eliminazione di un servizio, proposta dal fornitore stesso.

    Il fornitore non modifica direttamente il record `Vendor`/`VendorService`:
    invia una richiesta in stato PENDING che il back-office approva o
    rifiuta. Alla approvazione:
    - `request_type=EDIT`: le modifiche in `changes` (JSON) vengono
      applicate al target (`vendor_service` se valorizzato, altrimenti
      `vendor`);
    - `request_type=ADD_SERVICE`: viene creato un nuovo `VendorService` per
      `service_type` con i campi proposti in `changes`;
    - `request_type=DELETE_SERVICE`: `vendor_service` viene cancellato.
    """

    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("In attesa")),
        (STATUS_APPROVED, _("Approvata")),
        (STATUS_REJECTED, _("Respinta")),
    ]

    REQUEST_TYPE_EDIT = "EDIT"
    REQUEST_TYPE_ADD_SERVICE = "ADD_SERVICE"
    REQUEST_TYPE_DELETE_SERVICE = "DELETE_SERVICE"
    REQUEST_TYPE_CHOICES = [
        (REQUEST_TYPE_EDIT, _("Modifica")),
        (REQUEST_TYPE_ADD_SERVICE, _("Aggiunta servizio")),
        (REQUEST_TYPE_DELETE_SERVICE, _("Eliminazione servizio")),
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
    request_type = models.CharField(
        _("Tipo richiesta"),
        max_length=20,
        choices=REQUEST_TYPE_CHOICES,
        default=REQUEST_TYPE_EDIT,
    )
    vendor_service = models.ForeignKey(
        "vendors.VendorService",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Servizio fornitore"),
        related_name="change_requests",
        help_text=_(
            "Se valorizzato, le modifiche si applicano a questo servizio "
            "invece che all'anagrafica del fornitore. Per le richieste di "
            "eliminazione (DELETE_SERVICE) viene azzerato all'approvazione, "
            "prima della cancellazione del servizio, così da non perdere lo "
            "storico della richiesta."
        ),
    )
    service_type = models.ForeignKey(
        "vendors.ServiceType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Servizio richiesto"),
        related_name="add_requests",
        help_text=_(
            "Valorizzato solo per le richieste di aggiunta (ADD_SERVICE): "
            "il servizio del catalogo che il fornitore propone di erogare, "
            "non ancora esistente come VendorService."
        ),
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
        help_text=_(
            "Mappa {campo: {'old': valore_attuale, 'new': valore_proposto}}"
        ),
    )
    status = models.CharField(
        _("Stato"),
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(_("Creata il"), auto_now_add=True)
    reviewed_at = models.DateTimeField(
        _("Revisionata il"), null=True, blank=True
    )
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
        return (
            f"{self.vendor.name} — {self.get_status_display()} "
            f"({self.created_at:%d/%m/%Y})"
        )

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    @property
    def target(self):
        """Oggetto su cui va applicato il diff: il servizio se la richiesta
        riguarda un `VendorService`, altrimenti il `Vendor` stesso.

        Per `ADD_SERVICE` non esiste ancora un target (il `VendorService`
        viene creato solo all'approvazione): ritorna `None`.
        """
        if self.request_type == self.REQUEST_TYPE_ADD_SERVICE:
            return None
        return self.vendor_service or self.vendor

    def apply_to_vendor(self, reviewer, notes: str = ""):
        """Applica le modifiche e marca la richiesta APPROVED.

        - `ADD_SERVICE`: crea un nuovo `VendorService` per `service_type`.
        - `DELETE_SERVICE`: cancella `vendor_service`.
        - `EDIT`: applica il diff `changes` al target (`vendor_service` se
          valorizzato, altrimenti `vendor`). I campi accettati sono solo
          quelli presenti come attributi del target; eventuali campi
          sconosciuti vengono ignorati per sicurezza. Il campo "address" è
          un caso speciale solo quando il target è il `Vendor`:
          `Vendor.address` è una FK a un modello strutturato, quindi il
          testo libero proposto viene scritto sull'`Address` collegato
          (creandolo se assente) invece di un `setattr` diretto.
        """
        if self.status != self.STATUS_PENDING:
            raise ValueError(
                "Solo richieste in stato PENDING possono essere approvate."
            )

        if self.request_type == self.REQUEST_TYPE_ADD_SERVICE:
            self._create_vendor_service()
        elif self.request_type == self.REQUEST_TYPE_DELETE_SERVICE:
            self._delete_vendor_service()
        else:
            target = self.target
            for field, payload in (self.changes or {}).items():
                new_value = (
                    payload.get("new")
                    if isinstance(payload, dict)
                    else payload
                )
                if field == "address" and target is self.vendor:
                    self._apply_address(new_value)
                    continue
                if not hasattr(target, field):
                    continue
                setattr(target, field, new_value)
            target.save()

        self.status = self.STATUS_APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.review_notes = notes or self.review_notes
        self.save()

    def _create_vendor_service(self):
        """Crea il `VendorService` proposto da una richiesta ADD_SERVICE.

        Solo i campi in `EDITABLE_VENDOR_SERVICE_FIELDS` vengono presi da
        `changes`: stessa whitelist server-side usata per le richieste di
        modifica (prezzo orario e contratto restano BO-only).
        """
        from vendor_management_system.vendors.models import VendorService

        field_values = {
            field: (
                payload.get("new") if isinstance(payload, dict) else payload
            )
            for field, payload in (self.changes or {}).items()
            if field in EDITABLE_VENDOR_SERVICE_FIELDS
        }
        VendorService.objects.create(
            vendor=self.vendor,
            service_type=self.service_type,
            **field_values,
        )

    def _delete_vendor_service(self):
        """Cancella il `VendorService` di una richiesta DELETE_SERVICE.

        Il FK `vendor_service` viene azzerato e salvato PRIMA della
        cancellazione del servizio. `vendor_service.delete()` esegue già un
        SET NULL a livello di DB su questa riga (grazie a
        `on_delete=SET_NULL`), ma solo tramite una query diretta: l'istanza
        Python `self` già in memoria non verrebbe aggiornata. Se non la
        stacchiamo qui, il successivo `self.save()` in `apply_to_vendor`
        (per marcare la richiesta APPROVED) riscriverebbe nel DB il
        `vendor_service_id` ormai cancellato, con un riferimento pendente.
        """
        vendor_service = self.vendor_service
        if vendor_service is None:
            return
        self.vendor_service = None
        self.save(update_fields=["vendor_service"])
        vendor_service.delete()

    def _apply_address(self, new_text):
        """Scrive il testo libero proposto sull'Address collegato al vendor.

        Nessuna normalizzazione (via API esterne) in questa fase: il testo
        libero sostituisce interamente `street_address`; gli altri campi
        strutturati dell'indirizzo (città, CAP, ...) restano quelli già
        presenti.
        """
        from vendor_management_system.vendors.models import Address

        vendor = self.vendor
        if vendor.address_id:
            vendor.address.street_address = new_text or ""
            vendor.address.save()
        else:
            vendor.address = Address.objects.create(
                street_address=new_text or ""
            )

    def reject(self, reviewer, notes: str = ""):
        if self.status != self.STATUS_PENDING:
            raise ValueError(
                "Solo richieste in stato PENDING possono essere rifiutate."
            )
        self.status = self.STATUS_REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.review_notes = notes or self.review_notes
        self.save()
