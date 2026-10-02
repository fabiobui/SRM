import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Limiti della soglia di preavviso scadenza configurabile per tipo documento.
REMINDER_DAYS_DEFAULT = 30
REMINDER_DAYS_MIN = 10
REMINDER_DAYS_MAX = 90

# Campi dei cataloghi (documenti e requisiti) significativi solo se il tipo
# "richiede rinnovo".
RENEWAL_ONLY_FIELDS = ("validity_period_days", "reminder_days_before")


def clear_renewal_fields(catalog, save_kwargs):
    """Svuota i campi di rinnovo se il tipo non richiede rinnovo, anche con un
    save(update_fields=...) parziale."""
    if catalog.requires_renewal:
        return
    for field in RENEWAL_ONLY_FIELDS:
        setattr(catalog, field, None)
    update_fields = save_kwargs.get("update_fields")
    if update_fields is not None:
        save_kwargs["update_fields"] = {*update_fields, *RENEWAL_ONLY_FIELDS}


# Etichetta e colore per ogni codice di validity_status (usato dagli admin).
VALIDITY_STATUS_META = {
    "NOT_VALID": ("NOT VALID", "red"),
    "EXPIRED": ("EXPIRED", "red"),
    "EXPIRING_SOON": ("EXPIRING_SOON", "orange"),
    "VALID": ("VALID", "green"),
}


class DocumentCatalog(models.Model):
    """Tipi di documenti da richiedere ai fornitori"""

    id = models.CharField(
        _("Document Type ID"),
        max_length=10,
        unique=True,
        primary_key=True,
        editable=False,
        help_text=_("Unique ID for Document Type"),
    )

    # Core fields
    code = models.CharField(
        _("Codice Documento"),
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text=_(
            "Codice univoco del tipo di documento (es. 'DURC', 'VISURA')"
        ),
    )

    name = models.CharField(
        _("Document Type Name"),
        max_length=255,
        help_text=_("Name of document type (e.g. DURC, ISO 9001, etc.)"),
    )

    description = models.TextField(
        _("Description"),
        help_text=_("Description of this document type"),
        blank=True,
        null=True,
    )

    # Categorization
    document_category = models.CharField(
        _("Categoria Documento"),
        max_length=50,
        choices=[
            ("LEGAL", _("Legale/Amministrativo")),
            ("FINANCIAL", _("Finanziario")),
            ("SAFETY", _("Sicurezza")),
            ("QUALITY", _("Qualità")),
            ("TECHNICAL", _("Tecnico")),
            ("INSURANCE", _("Assicurativo")),
            ("CERTIFICATION", _("Certificazioni")),
            ("OTHER", _("Altro")),
        ],
        default="LEGAL",
        blank=True,
        null=True,
        help_text=_("Categoria del documento"),
    )

    # Requirements (is_required già esiste, manteniamo quello)
    is_required = models.BooleanField(
        _("È obbligatorio"),
        default=True,
        help_text=_(
            "Indica se il documento è obbligatorio per la qualifica del "
            "fornitore"
        ),
    )

    requires_renewal = models.BooleanField(
        _("Richiede Rinnovo"),
        default=True,
        help_text=_("Documento con scadenza che necessita rinnovo"),
    )

    # Vuoto per i tipi senza rinnovo (lo svuota save()).
    validity_period_days = models.PositiveIntegerField(
        _("Periodo validità (giorni)"),
        help_text=_(
            "Solo per i documenti che richiedono rinnovo: giorni di validità "
            "dalla data di emissione, usati per calcolare la data di scadenza."
        ),
        default=365,
        null=True,
        blank=True,
    )

    # Soglia di EXPIRING_SOON e del primo promemoria email al fornitore.
    # Vuota per i tipi senza rinnovo, che restano fuori dai promemoria.
    reminder_days_before = models.IntegerField(
        _("Giorni di preavviso scadenza"),
        help_text=_(
            "Solo per i documenti che richiedono rinnovo (tra 10 e 90): "
            "giorni prima della scadenza in cui il documento passa a "
            "EXPIRING_SOON e parte il primo promemoria email al fornitore. "
            "Il secondo promemoria parte sempre a 7 giorni."
        ),
        default=REMINDER_DAYS_DEFAULT,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(REMINDER_DAYS_MIN),
            MaxValueValidator(REMINDER_DAYS_MAX),
        ],
    )

    # Business rules
    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Tipo di documento attivo e utilizzabile"),
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"),
        default=100,
        help_text=_("Ordine di visualizzazione"),
    )

    # Metadata
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    # Related categories
    applicable_categories = models.ManyToManyField(
        "vendors.Category",
        verbose_name=_("Categorie Applicabili"),
        blank=True,
        related_name="required_documents",
        help_text=_("Categorie per cui questo documento è richiesto"),
    )

    # Template and instructions
    template_file = models.FileField(
        _("File Template"),
        upload_to="document_templates/",
        blank=True,
        null=True,
        help_text=_("Template o modello del documento"),
    )

    instructions = models.TextField(
        _("Istruzioni"),
        blank=True,
        null=True,
        help_text=_(
            "Istruzioni per il fornitore su come compilare/ottenere il "
            "documento"
        ),
    )

    class Meta:
        verbose_name = _("Tipo di Documento Contrattuale")
        verbose_name_plural = _("Catalogo Documenti Contrattuali")
        ordering = ["document_category", "sort_order", "name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["document_category", "is_active"]),
            models.Index(fields=["is_required"]),
        ]

    def __str__(self):
        if self.code:
            return f"{self.code} - {self.name}"
        return self.name

    def clean(self):
        super().clean()
        if self.requires_renewal:
            required = _(
                "Obbligatorio per i documenti che richiedono rinnovo."
            )
            errors = {
                field: required
                for field in RENEWAL_ONLY_FIELDS
                if getattr(self, field) is None
            }
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = str(uuid.uuid4()).replace("-", "")[:10].upper()
        clear_renewal_fields(self, kwargs)
        super().save(*args, **kwargs)


class Document(models.Model):
    """Documenti caricati dai fornitori"""

    STATUS_CHOICES = [
        ("PENDING", _("In attesa di caricamento")),
        ("UPLOADED", _("Caricato - da verificare")),
        ("APPROVED", _("Approvato")),
        ("REJECTED", _("Respinto")),
        ("EXPIRED", _("Scaduto")),
    ]

    id = models.CharField(
        _("Document ID"),
        max_length=10,
        unique=True,
        primary_key=True,
        editable=False,
        help_text=_("Unique ID for Document"),
    )
    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.CASCADE,
        verbose_name=_("Vendor"),
        help_text=_("Vendor who owns this document"),
        related_name="documents",
    )
    document_type = models.ForeignKey(
        DocumentCatalog,
        on_delete=models.CASCADE,
        verbose_name=_("Tipo di Documento"),
        help_text=_("Tipo di documento"),
    )
    file = models.FileField(
        _("File Documento"),
        upload_to="vendor_documents/%Y/%m/",
        help_text=_("Carica il file del documento"),
        null=True,
        blank=True,
    )
    issue_date = models.DateField(
        _("Data di Emissione"),
        help_text=_("Data di emissione del documento"),
        null=True,
        blank=True,
    )
    expiry_date = models.DateField(
        _("Data di Scadenza"),
        help_text=_("Data di scadenza del documento"),
        null=True,
        blank=True,
    )
    status = models.CharField(
        _("Stato"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
        help_text=_("Stato corrente del documento"),
    )
    notes = models.TextField(
        _("Note"),
        help_text=_("Note aggiuntive su questo documento"),
        blank=True,
    )
    uploaded_at = models.DateTimeField(
        _("Data di Caricamento"),
        auto_now_add=True,
        help_text=_("Data di caricamento del documento"),
    )
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        verbose_name=_("Revisionato da"),
        help_text=_("Utente che ha revisionato questo documento"),
        null=True,
        blank=True,
        related_name="reviewed_documents",
    )
    reviewed_at = models.DateTimeField(
        _("Reviewed At"),
        help_text=_("When document was reviewed"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Documento Contrattuale")
        verbose_name_plural = _("Registro Documenti Contrattuali")
        ordering = ["-uploaded_at"]
        unique_together = ["vendor", "document_type"]

    def __str__(self):
        return f"{self.vendor.name} - {self.document_type.name}"

    @property
    def is_expiring_soon(self):
        """Documento entro i giorni di preavviso del suo tipo. Mai per i tipi
        senza rinnovo, che non hanno preavviso."""
        reminder_days = self.document_type.reminder_days_before
        if not self.expiry_date or reminder_days is None:
            return False
        days_to_expiry = (self.expiry_date - timezone.now().date()).days
        return days_to_expiry <= reminder_days

    @property
    def is_expired(self):
        """Check if document is expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()

    @property
    def is_valid(self):
        """Documento valido solo se lo stato di lavorazione è 'Approvato'
        e il documento non è scaduto. Qualunque altro stato è NOT VALID."""
        return self.status == "APPROVED" and not self.is_expired

    @property
    def satisfies_requirement(self):
        """Documento che soddisfa un requisito di qualifica: caricato (file
        presente), approvato dal gestore e non scaduto."""
        return bool(self.file) and self.is_valid

    @property
    def validity_status(self):
        """Stato di validità del documento (fonte unica per admin/inline):
        NOT_VALID se non approvato, altrimenti in base alla scadenza."""
        if self.status != "APPROVED":
            return "NOT_VALID"
        if self.is_expired:
            return "EXPIRED"
        if self.is_expiring_soon:
            return "EXPIRING_SOON"
        return "VALID"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = str(uuid.uuid4()).replace("-", "")[:10].upper()

        # Auto-update status based on expiry
        if self.is_expired and self.status != "EXPIRED":
            self.status = "EXPIRED"

        super().save(*args, **kwargs)


class DocumentSet(models.Model):
    """Set documentale: insieme predefinito di tipi di documento da assegnare
    in blocco a un fornitore dal tab Documenti dell'admin."""

    name = models.CharField(
        _("Nome Set"),
        max_length=255,
        help_text=_(
            "Nome del set documentale (es. 'Set base appalti', 'Set "
            "sanitario')"
        ),
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione del set documentale"),
    )

    category = models.ForeignKey(
        "vendors.Category",
        verbose_name=_("Classificazione"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_sets",
        help_text=_(
            "Classificazione del fornitore a cui si applica il set "
            "(vuoto = applicabile a tutte le classificazioni)"
        ),
    )

    document_types = models.ManyToManyField(
        DocumentCatalog,
        verbose_name=_("Tipi di Documento"),
        related_name="document_sets",
        help_text=_("Tipi di documento inclusi nel set"),
    )

    default_status = models.CharField(
        _("Stato Predefinito"),
        max_length=20,
        choices=Document.STATUS_CHOICES,
        default="PENDING",
        help_text=_("Stato applicato ai documenti creati dal set"),
    )

    is_active = models.BooleanField(
        _("Attivo"), default=True, help_text=_("Set attivo e selezionabile")
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine"), default=0, help_text=_("Ordine di visualizzazione")
    )

    class Meta:
        verbose_name = _("Set Documentale")
        verbose_name_plural = _("Set Documentali")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name
