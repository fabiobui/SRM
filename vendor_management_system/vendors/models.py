# Imports
import uuid

from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Import DocumentCatalog and Document from documents app
from vendor_management_system.documents.models import (
    REMINDER_DAYS_DEFAULT,
    REMINDER_DAYS_MAX,
    REMINDER_DAYS_MIN,
    RENEWAL_ONLY_FIELDS,
    Document,
    DocumentCatalog,
    clear_renewal_fields,
)

# ============================================================================
# Modelli Geografici (Nazione, Regione, Provincia)
# ============================================================================


class Country(models.Model):
    """Tabella delle Nazioni"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        _("Codice ISO"),
        max_length=3,
        unique=True,
        help_text=_("Codice ISO 3166-1 alpha-2 (es. 'IT', 'DE', 'FR')"),
    )
    name = models.CharField(
        _("Nome Nazione"), max_length=100, help_text=_("Nome della nazione")
    )
    is_active = models.BooleanField(_("È Attiva"), default=True)
    sort_order = models.PositiveIntegerField(_("Ordine"), default=100)

    class Meta:
        verbose_name = _("Nazione")
        verbose_name_plural = _("Nazioni")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Region(models.Model):
    """Tabella delle Regioni"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        _("Codice Regione"),
        max_length=10,
        unique=True,
        help_text=_("Codice univoco della regione (es. 'LOM', 'VEN')"),
    )
    name = models.CharField(
        _("Nome Regione"), max_length=100, help_text=_("Nome della regione")
    )
    country = models.ForeignKey(
        Country,
        verbose_name=_("Nazione"),
        on_delete=models.CASCADE,
        related_name="regions",
        help_text=_("Nazione di appartenenza"),
    )
    is_active = models.BooleanField(_("È Attiva"), default=True)
    sort_order = models.PositiveIntegerField(_("Ordine"), default=100)

    class Meta:
        verbose_name = _("Regione")
        verbose_name_plural = _("Regioni")
        ordering = ["country__name", "sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.country.code})"


class Province(models.Model):
    """Tabella delle Province"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        _("Sigla Provincia"),
        max_length=10,
        unique=True,
        help_text=_("Sigla della provincia (es. 'MI', 'RM', 'RA')"),
    )
    name = models.CharField(
        _("Nome Provincia"),
        max_length=100,
        help_text=_("Nome della provincia"),
    )
    region = models.ForeignKey(
        Region,
        verbose_name=_("Regione"),
        on_delete=models.CASCADE,
        related_name="provinces",
        help_text=_("Regione di appartenenza"),
    )
    is_active = models.BooleanField(_("È Attiva"), default=True)
    sort_order = models.PositiveIntegerField(_("Ordine"), default=100)

    class Meta:
        verbose_name = _("Provincia")
        verbose_name_plural = _("Province")
        ordering = ["region__name", "sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


# Nuovo Model per Category
class Category(models.Model):
    """
    Modello per gestire le categorie merceologiche dei fornitori
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core fields
    code = models.CharField(
        _("Codice Classificazione"),
        max_length=20,
        unique=True,
        help_text=_(
            "Codice univoco della classificazione (es. 'SERV', 'FORN', 'MANU')"
        ),
    )

    name = models.CharField(
        _("Nome Classificazione"),
        max_length=100,
        help_text=_("Nome della classificazione"),
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata della classificazione"),
    )

    # Hierarchical structure (optional)
    parent = models.ForeignKey(
        "self",
        verbose_name=_("Classificazione Padre"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subcategories",
        help_text=_("Classificazione padre per struttura gerarchica"),
    )

    # Status and classification
    is_active = models.BooleanField(
        _("È Attiva"),
        default=True,
        help_text=_("Classificazione attiva e utilizzabile"),
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"),
        default=100,
        help_text=_("Ordine di visualizzazione"),
    )

    # Color coding for UI
    color_code = models.CharField(
        _("Codice Colore"),
        max_length=7,
        blank=True,
        null=True,
        help_text=_("Codice colore esadecimale (es. #FF5733)"),
    )

    # Metadata
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    # Business rules
    requires_certification = models.BooleanField(
        _("Richiede Certificazione"),
        default=False,
        help_text=_("Categoria che richiede certificazioni specifiche"),
    )

    default_risk_level = models.CharField(
        _("Livello di Rischio Predefinito"),
        max_length=20,
        choices=[
            ("LOW", _("Basso")),
            ("MEDIUM", _("Medio")),
            ("HIGH", _("Alto")),
        ],
        default="MEDIUM",
        help_text=_("Livello di rischio di default per questa categoria"),
    )

    class Meta:
        verbose_name = _("Classificazione")
        verbose_name_plural = _("Classificazioni")
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active", "sort_order"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    @property
    def full_name(self):
        """Ritorna il nome completo inclusi i parent"""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name

    @property
    def level(self):
        """Ritorna il livello di profondità nella gerarchia"""
        if self.parent:
            return self.parent.level + 1
        return 0

    @property
    def vendor_count(self):
        """Ritorna il numero di vendor in questa categoria"""
        return (
            self.vendors.filter(is_active=True).count()
            if hasattr(self, "vendors")
            else 0
        )

    @property
    def total_vendor_count(self):
        """Ritorna il numero totale di vendor incluse le sottocategorie"""
        count = self.vendor_count
        for subcategory in self.subcategories.all():
            count += subcategory.total_vendor_count
        return count

    def clean(self):
        """Validazioni custom"""
        super().clean()

        # Evita cicli nella gerarchia
        if self.parent:
            parent = self.parent
            while parent:
                if parent == self:
                    from django.core.exceptions import ValidationError

                    raise ValidationError(
                        _("Una categoria non può essere genitore di se stessa")
                    )
                parent = parent.parent

        # Valida il codice colore
        if self.color_code:
            import re

            if not re.match(r"^#[0-9A-Fa-f]{6}$", self.color_code):
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    _(
                        "Il codice colore deve essere in formato "
                        "esadecimale (es. #FF5733)"
                    )
                )

    def save(self, *args, **kwargs):
        # Auto-genera il code se non specificato
        if not self.code:
            self.code = self.name[:20].upper().replace(" ", "_")

        self.full_clean()
        super().save(*args, **kwargs)

    def get_descendants(self, include_self=False):
        """Ritorna tutti i discendenti di questa categoria"""
        descendants = []
        if include_self:
            descendants.append(self)

        for child in self.subcategories.all():
            descendants.extend(child.get_descendants(include_self=True))

        return descendants

    def get_ancestors(self, include_self=False):
        """Ritorna tutti gli antenati di questa categoria"""
        ancestors = []
        if include_self:
            ancestors.append(self)

        if self.parent:
            ancestors.extend(self.parent.get_ancestors(include_self=True))

        return ancestors


def category_scope_ids(category):
    """Id della classificazione indicata e di tutti i suoi antenati.

    Serve a far comparire su un fornitore anche i set (CompetenceSet,
    ServiceSet) definiti su una classificazione padre: un set legato a
    'MDL' resta valido per un fornitore classificato 'MEDICO COMPETENTE',
    figlio di MDL.
    """
    ids, seen = [], set()
    while category and category.pk not in seen:
        seen.add(category.pk)
        ids.append(category.pk)
        category = category.parent
    return ids


def vendor_category_scope_ids(vendor):
    """Id di tutte le classificazioni del fornitore e dei loro antenati.

    Unione di `Vendor.category` (principale) e `Vendor.additional_categories`
    (aggiuntive), ciascuna con i propri antenati. Lista vuota se il
    fornitore non ha alcuna classificazione (o non è ancora salvato).
    """
    ids, seen = [], set()
    categories = []
    if vendor.category_id:
        categories.append(vendor.category)
    if vendor.pk:
        categories.extend(vendor.additional_categories.all())
    for category in categories:
        for pk in category_scope_ids(category):
            if pk not in seen:
                seen.add(pk)
                ids.append(pk)
    return ids


# Model for Competence
class Competence(models.Model):
    """
    Modello per gestire le competenze/qualifiche dei fornitori
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Core fields
    code = models.CharField(
        _("Codice Requisito"),
        max_length=50,
        unique=True,
        help_text=_(
            "Codice univoco del requisito professionale (es. 'RSPP', 'ASPP')"
        ),
    )

    name = models.CharField(
        _("Nome Requisito Professionale"),
        max_length=255,
        help_text=_("Nome del requisito professionale"),
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata del requisito professionale"),
    )

    # Categorization
    competence_category = models.CharField(
        _("Categoria Requisito Professionale"),
        max_length=50,
        choices=[
            ("SAFETY", _("Sicurezza")),
            ("QUALITY", _("Qualità")),
            ("TECHNICAL", _("Tecnico")),
            ("ENERGY", _("Energia")),
            ("ENVIRONMENT", _("Ambiente")),
            ("DOCTOR", _("Medico/Infermieristico")),
            ("AUDIT", _("Audit/Certificazioni")),
            ("OTHER", _("Altro")),
        ],
        default="TECHNICAL",
        help_text=_("Categoria del requisito professionale"),
    )

    # Requirements
    requires_certification = models.BooleanField(
        _("Richiede Certificazione"),
        default=True,
        help_text=_(
            "Indica se il requisito professionale richiede una "
            "certificazione formale"
        ),
    )

    requires_renewal = models.BooleanField(
        _("Richiede Rinnovo"),
        default=False,
        help_text=_(
            "Indica se il requisito professionale ha una scadenza e "
            "necessita rinnovo"
        ),
    )

    # Vuoti per i requisiti senza rinnovo (li svuota save()).
    validity_period_days = models.PositiveIntegerField(
        _("Periodo validità (giorni)"),
        default=365,
        null=True,
        blank=True,
        help_text=_(
            "Solo per i requisiti che richiedono rinnovo: giorni di validità "
            "dalla data di rilascio, usati per calcolare la data di "
            "scadenza (es. 365, 730, 1095)."
        ),
    )

    reminder_days_before = models.PositiveIntegerField(
        _("Giorni di preavviso scadenza"),
        default=REMINDER_DAYS_DEFAULT,
        null=True,
        blank=True,
        validators=[
            validators.MinValueValidator(REMINDER_DAYS_MIN),
            validators.MaxValueValidator(REMINDER_DAYS_MAX),
        ],
        help_text=_(
            "Solo per i requisiti che richiedono rinnovo (tra 10 e 90): "
            "giorni prima della scadenza in cui il requisito passa a "
            "EXPIRING_SOON e parte il primo promemoria email al fornitore. "
            "Il secondo promemoria parte sempre a 7 giorni."
        ),
    )

    # Business rules
    is_mandatory = models.BooleanField(
        _("È Obbligatorio"),
        default=False,
        help_text=_(
            "Requisito professionale obbligatorio per alcune categorie "
            "di fornitori"
        ),
    )

    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Requisito professionale attivo e utilizzabile"),
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
        Category,
        verbose_name=_("Categorie Applicabili"),
        blank=True,
        related_name="required_competences",
        help_text=_("Categorie per cui questa competenza è rilevante"),
    )

    class Meta:
        verbose_name = _("Abilitazione/Requisito Professionale")
        verbose_name_plural = _(
            "Catalogo Abilitazioni e Requisiti Professionali"
        )
        ordering = ["competence_category", "sort_order", "name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["competence_category", "is_active"]),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        super().clean()
        if self.requires_renewal:
            required = _(
                "Obbligatorio per i requisiti che richiedono rinnovo."
            )
            errors = {
                field: required
                for field in RENEWAL_ONLY_FIELDS
                if getattr(self, field) is None
            }
            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        clear_renewal_fields(self, kwargs)
        super().save(*args, **kwargs)


# Model for VendorCompetence (through table)
class VendorCompetence(models.Model):
    """
    Modello per associare competenze ai fornitori con informazioni aggiuntive
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relations
    vendor = models.ForeignKey(
        "Vendor",
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="vendor_competences",
    )

    competence = models.ForeignKey(
        Competence,
        verbose_name=_("Requisito Professionale"),
        on_delete=models.CASCADE,
        related_name="vendor_assignments",
    )

    # Tipo Requisito
    is_competenza = models.BooleanField(
        _("Competenza"),
        default=False,
        help_text=_("Indica se il requisito è assegnato come competenza"),
    )

    is_qualifica = models.BooleanField(
        _("Qualifica"),
        default=False,
        help_text=_("Indica se il requisito è assegnato come qualifica"),
    )

    is_iscrizione_albo = models.BooleanField(
        _("Iscrizione Albo"),
        default=False,
        help_text=_("Indica se il requisito è un'iscrizione all'albo"),
    )

    # Status
    has_competence = models.BooleanField(
        _("Possiede Requisito Professionale"),
        default=True,
        help_text=_("Il fornitore possiede questo requisito professionale"),
    )

    has_certification = models.BooleanField(
        _("Possiede Certificazione"),
        default=False,
        help_text=_("Il fornitore possiede questa certificazione"),
    )

    # Certification details
    certification_number = models.CharField(
        _("Numero Certificazione"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Numero del certificato/attestato"),
    )

    certification_body = models.CharField(
        _("Ente Certificatore"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Ente che ha rilasciato la certificazione"),
    )

    issue_date = models.DateField(
        _("Data Rilascio"),
        null=True,
        blank=True,
        help_text=_("Data di rilascio della certificazione"),
    )

    expiry_date = models.DateField(
        _("Data Scadenza"),
        null=True,
        blank=True,
        help_text=_("Data di scadenza della certificazione"),
    )

    # Verification
    verified = models.BooleanField(
        _("Verificata"),
        default=False,
        help_text=_("Competenza verificata dall'azienda"),
    )

    rejected = models.BooleanField(
        _("Respinta"),
        default=False,
        help_text=_(
            "Documento respinto dal gestore, in attesa di un nuovo caricamento"
        ),
    )

    verified_by = models.CharField(
        _("Verificata da"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Persona che ha verificato la competenza"),
    )

    verified_date = models.DateField(
        _("Data Verifica"),
        null=True,
        blank=True,
        help_text=_("Data di verifica"),
    )

    # Documentation
    document_file = models.FileField(
        _("File Documento"),
        upload_to="vendor_competences/%Y/%m/",
        blank=True,
        null=True,
        help_text=_("File del certificato/attestato"),
    )

    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True,
        help_text=_("Note aggiuntive sulla competenza"),
    )

    # Nuova versione caricata dal fornitore mentre il requisito verificato è
    # ancora valido: resta in attesa di revisione e sostituisce i campi sopra
    # solo se l'ufficio la approva. Una sola per requisito.
    pending_document_file = models.FileField(
        _("Nuova versione: file"),
        upload_to="vendor_competences/pending/%Y/%m/",
        null=True,
        blank=True,
    )
    pending_certification_number = models.CharField(
        _("Nuova versione: numero certificazione"),
        max_length=100,
        null=True,
        blank=True,
    )
    pending_issue_date = models.DateField(
        _("Nuova versione: data rilascio"), null=True, blank=True
    )
    pending_expiry_date = models.DateField(
        _("Nuova versione: data scadenza"), null=True, blank=True
    )
    pending_notes = models.TextField(_("Nuova versione: note"), blank=True)
    pending_uploaded_at = models.DateTimeField(
        _("Nuova versione: caricata il"), null=True, blank=True
    )

    # Metadata
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    class Meta:
        verbose_name = _("Abilitazione/Requisito Professionale Assegnato")
        verbose_name_plural = _(
            "Abilitazioni e Requisiti Professionali Assegnati"
        )
        unique_together = [["vendor", "competence"]]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vendor", "competence"]),
            models.Index(fields=["expiry_date"]),
            models.Index(fields=["verified"]),
        ]

    def __str__(self):
        return f"{self.vendor.name} - {self.competence.name}"

    def save(self, *args, **kwargs):
        # Un requisito verificato non può risultare anche respinto.
        if self.verified:
            self.rejected = False
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Verifica se la certificazione è scaduta"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def satisfies_requirement(self):
        """Requisito che soddisfa la qualifica: posseduto, documento
        caricato, verificato dal gestore e non scaduto."""
        return (
            self.has_competence
            and bool(self.document_file)
            and self.verified
            and not self.is_expired
        )

    @property
    def is_delivered(self):
        """Requisito consegnato dal fornitore: posseduto, documento caricato,
        non scaduto e non respinto (anche se non ancora verificato)."""
        return (
            self.has_competence
            and bool(self.document_file)
            and not self.rejected
            and not self.is_expired
        )

    @property
    def has_pending_revision(self):
        return bool(self.pending_document_file)

    def submit_upload(
        self,
        document_file,
        certification_number=None,
        issue_date=None,
        expiry_date=None,
        notes="",
    ):
        """Upload del fornitore. Se il requisito è verificato e ancora valido
        la nuova versione resta in attesa di revisione (ritorna True) e il
        requisito non cambia; altrimenti lo sostituisce subito (False)."""
        if self.satisfies_requirement:
            self.pending_document_file = document_file
            self.pending_certification_number = certification_number
            self.pending_issue_date = issue_date
            self.pending_expiry_date = expiry_date
            self.pending_notes = notes or ""
            self.pending_uploaded_at = timezone.now()
            self.save()
            return True
        self.document_file = document_file
        self.certification_number = certification_number
        self.issue_date = issue_date
        self.expiry_date = expiry_date
        self.notes = notes or ""
        self.verified = False
        self.rejected = False
        self.verified_by = None
        self.verified_date = None
        self._clear_pending_revision()
        self.save()
        return False

    def apply_pending_revision(self):
        """La revisione in attesa diventa il requisito in vigore."""
        self.document_file = self.pending_document_file
        self.certification_number = self.pending_certification_number
        self.issue_date = self.pending_issue_date
        self.expiry_date = self.pending_expiry_date
        self.notes = self.pending_notes
        self._clear_pending_revision()
        self.save()

    def discard_pending_revision(self):
        self._clear_pending_revision()
        self.save()

    def _clear_pending_revision(self):
        self.pending_document_file = None
        self.pending_certification_number = None
        self.pending_issue_date = None
        self.pending_expiry_date = None
        self.pending_notes = ""
        self.pending_uploaded_at = None

    @property
    def days_to_expiry(self):
        """Ritorna i giorni rimanenti alla scadenza"""
        if self.expiry_date:
            delta = self.expiry_date - timezone.now().date()
            return delta.days
        return None

    @property
    def expiry_status(self):
        """Ritorna lo stato della scadenza"""
        if not self.expiry_date:
            return "NO_EXPIRY"

        days = self.days_to_expiry
        if days < 0:
            return "EXPIRED"
        # Come per i documenti: soglia del requisito a catalogo, assente
        # per i requisiti senza rinnovo.
        reminder_days = self.competence.reminder_days_before
        if self.competence.requires_renewal and reminder_days is not None:
            if days <= reminder_days:
                return "EXPIRING_SOON"
        return "VALID"


class CompetenceSet(models.Model):
    """Set di requisiti professionali: insieme predefinito di requisiti da
    assegnare in blocco a un fornitore dal tab Requisiti Professionali
    dell'admin."""

    name = models.CharField(
        _("Nome Set"),
        max_length=255,
        help_text=_(
            "Nome del set di requisiti (es. 'MDL - Medico Competente')"
        ),
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione del set di requisiti professionali"),
    )

    category = models.ForeignKey(
        Category,
        verbose_name=_("Classificazione"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="competence_sets",
        help_text=_(
            "Classificazione del fornitore a cui si applica il set "
            "(vuoto = applicabile a tutte le classificazioni)"
        ),
    )

    competences = models.ManyToManyField(
        Competence,
        verbose_name=_("Abilitazioni e Requisiti Professionali"),
        related_name="competence_sets",
        help_text=_("Abilitazioni e requisiti professionali inclusi nel set"),
    )

    is_active = models.BooleanField(
        _("Attivo"), default=True, help_text=_("Set attivo e selezionabile")
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine"), default=0, help_text=_("Ordine di visualizzazione")
    )

    class Meta:
        verbose_name = _("Set Abilitazioni e Requisiti Professionali")
        verbose_name_plural = _("Set Abilitazioni e Requisiti Professionali")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# Model for Address
class Address(models.Model):
    """
    Modello per gestire gli indirizzi in modo strutturato
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Address fields
    street_address = models.CharField(
        _("Indirizzo Strada"),
        max_length=255,
        help_text=_("Via, numero civico"),
    )

    street_address_2 = models.CharField(
        _("Indirizzo Strada 2"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Appartamento, scala, interno (opzionale)"),
    )

    city = models.CharField(_("Città"), max_length=100, help_text=_("Città"))

    state_province = models.CharField(
        _("Stato/Provincia"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Provincia/Stato"),
    )
    region = models.CharField(
        _("Regione"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Regione"),
    )

    postal_code = models.CharField(
        _("Codice Postale"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Codice postale/CAP"),
    )

    country = models.CharField(
        _("Paese"), max_length=100, default="Italia", help_text=_("Paese")
    )

    # Geographic coordinates (optional)
    latitude = models.DecimalField(
        _("Latitudine"),
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_("Latitudine (opzionale)"),
    )

    longitude = models.DecimalField(
        _("Longitudine"),
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_("Longitudine (opzionale)"),
    )

    # Metadata fields
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    # Additional info
    address_type = models.CharField(
        _("Tipo Indirizzo"),
        max_length=50,
        choices=[
            ("LEGAL", _("Sede legale")),
            ("OPERATIONAL", _("Sede operativa")),
            ("BILLING", _("Indirizzo fatturazione")),
            ("SHIPPING", _("Indirizzo spedizione")),
            ("OTHER", _("Altro")),
        ],
        default="LEGAL",
        help_text=_("Tipo di indirizzo"),
    )

    is_active = models.BooleanField(
        _("È Attivo"), default=True, help_text=_("Indirizzo attivo")
    )

    class Meta:
        verbose_name = _("Indirizzo")
        verbose_name_plural = _("Indirizzi")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city", "country"]),
            models.Index(fields=["postal_code"]),
        ]

    def __str__(self):
        """Rappresentazione string dell'indirizzo"""
        address_parts = [self.street_address]

        if self.street_address_2:
            address_parts.append(self.street_address_2)

        address_parts.extend([f"{self.postal_code} {self.city}", self.country])

        return ", ".join(address_parts)

    @property
    def full_address(self):
        """Ritorna l'indirizzo completo formattato"""
        return str(self)

    @property
    def short_address(self):
        """Ritorna una versione abbreviata dell'indirizzo"""
        return f"{self.street_address}, {self.city}"


class QualificationType(models.Model):
    """
    Tabella dei titoli di studio o tipi di qualifica
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        _("Codice Titolo"),
        max_length=50,
        unique=True,
        help_text=_(
            "Codice univoco del titolo di studio o qualifica (es. 'DIP', "
            "'LAU', 'MAS')"
        ),
    )

    name = models.CharField(
        _("Nome Titolo"),
        max_length=255,
        help_text=_(
            "Nome completo del titolo di studio (es. 'Diploma tecnico', "
            "'Laurea triennale')"
        ),
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione aggiuntiva del titolo di studio"),
    )

    level = models.CharField(
        _("Livello EQF"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_(
            "Livello di qualifica secondo il Quadro Europeo delle "
            "Qualifiche (EQF)"
        ),
    )

    # nuovo: struttura gerarchica padre-figlio
    parent = models.ForeignKey(
        "self",
        verbose_name=_("Titolo/Qualifica Padre"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sub_qualifications",
        help_text=_(
            "Titolo/Qualifica padre (es. 'Laurea' per 'Laurea triennale', "
            "'Laurea magistrale', ecc.)"
        ),
    )

    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Titolo/Qualifica attivo e selezionabile"),
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"), default=100
    )

    class Meta:
        verbose_name = _("Titolo")
        verbose_name_plural = _("Titoli")
        ordering = ["sort_order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name


class ServiceType(models.Model):
    """
    Tabella unica per Tipologie e Servizi Specifici
    (relazione gerarchica self-referenziata)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    code = models.CharField(
        _("Codice Servizio"),
        max_length=50,
        unique=True,
        help_text=_(
            "Codice univoco del servizio o tipologia (es. 'CONSULENZA', "
            "'CONS_SIC')"
        ),
    )

    name = models.CharField(
        _("Nome Servizio"),
        max_length=255,
        help_text=_("Nome della tipologia o del servizio specifico"),
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata del servizio"),
    )

    parent = models.ForeignKey(
        "self",
        verbose_name=_("Tipologia Padre"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subservices",
        help_text=_(
            "Tipologia padre (lascia vuoto se è una categoria principale)"
        ),
    )

    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Indica se il servizio è attivo"),
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"), default=100
    )

    class Meta:
        verbose_name = _("Tipo/Servizio Erogato")
        verbose_name_plural = _("Tipologie e Servizi Erogati")
        ordering = ["sort_order", "name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    @property
    # utile per distinguere le tipologie principali
    def is_category(self):
        return self.parent is None


class VendorService(models.Model):
    """
    Modello per associare servizi ai fornitori con informazioni aggiuntive
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relations
    vendor = models.ForeignKey(
        "Vendor",
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="vendor_services",
    )

    service_type = models.ForeignKey(
        ServiceType,
        verbose_name=_("Servizio"),
        on_delete=models.CASCADE,
        related_name="vendor_assignments",
    )

    # Additional info
    hourly_rate = models.DecimalField(
        _("Prezzo Orario"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Prezzo orario del servizio per questo fornitore"),
    )

    is_primary = models.BooleanField(
        _("Servizio Principale"),
        default=False,
        help_text=_("Indica se questo è il servizio principale del fornitore"),
    )

    start_date = models.DateField(
        _("Data Inizio Erogazione"),
        null=True,
        blank=True,
        help_text=_("Data di inizio erogazione del servizio"),
    )

    end_date = models.DateField(
        _("Data Fine Erogazione"),
        null=True,
        blank=True,
        help_text=_("Data di fine erogazione del servizio (se applicabile)"),
    )

    contract = models.ForeignKey(
        "Contract",
        verbose_name=_("Contratto"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_services",
        help_text=_("Contratto associato a questo servizio"),
    )

    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True,
        help_text=_("Note aggiuntive sul servizio erogato"),
    )

    # Metadata
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    class Meta:
        verbose_name = _("Servizio Erogato")
        verbose_name_plural = _("Servizi Erogati")
        unique_together = [["vendor", "service_type"]]
        ordering = ["-is_primary", "-created_at"]
        indexes = [
            models.Index(fields=["vendor", "service_type"]),
            models.Index(fields=["is_primary"]),
        ]

    def __str__(self):
        primary = " (Principale)" if self.is_primary else ""
        return f"{self.vendor.name} - {self.service_type.name}{primary}"

    @property
    def is_active(self):
        """Verifica se il servizio è ancora attivo"""
        if self.end_date:
            return self.end_date >= timezone.now().date()
        return True


class ServiceSet(models.Model):
    """Set di servizi: insieme predefinito di servizi da assegnare in blocco a
    un fornitore dal tab Servizi dell'admin."""

    name = models.CharField(
        _("Nome Set"),
        max_length=255,
        help_text=_("Nome del set di servizi (es. 'MEDICINA DEL LAVORO')"),
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione del set di servizi"),
    )

    category = models.ForeignKey(
        Category,
        verbose_name=_("Classificazione"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_sets",
        help_text=_(
            "Classificazione del fornitore a cui si applica il set "
            "(vuoto = applicabile a tutte le classificazioni)"
        ),
    )

    service_types = models.ManyToManyField(
        ServiceType,
        verbose_name=_("Servizi Erogati"),
        related_name="service_sets",
        help_text=_("Servizi erogati inclusi nel set"),
    )

    is_active = models.BooleanField(
        _("Attivo"), default=True, help_text=_("Set attivo e selezionabile")
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine"), default=0, help_text=_("Ordine di visualizzazione")
    )

    class Meta:
        verbose_name = _("Set Servizi Erogati")
        verbose_name_plural = _("Set Servizi Erogati")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Contract(models.Model):
    """
    Contratto associato a un fornitore, con collegamento ai servizi erogati.
    Un fornitore può avere più contratti.
    """

    CONTRACT_STATUS_CHOICES = [
        ("DRAFT", _("Bozza")),
        ("ACTIVE", _("Attivo")),
        ("EXPIRED", _("Scaduto")),
        ("TERMINATED", _("Risolto")),
        ("SUSPENDED", _("Sospeso")),
    ]

    CONTRACT_TYPE_CHOICES = [
        ("ACCORDO_QUADRO", _("Accordo quadro")),
        ("ORDINE", _("Ordine")),
        ("ORDINE_RICORRENTE", _("Ordine ricorrente")),
        ("DEROGA", _("Deroga")),
        ("FORNITURA_OCCASIONALE", _("Fornitura occasionale")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        "Vendor",
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    contract_number = models.CharField(
        _("Numero Contratto"),
        max_length=50,
        unique=True,
        help_text=_("Codice identificativo del contratto"),
    )
    title = models.CharField(
        _("Titolo"),
        max_length=255,
        help_text=_("Descrizione breve del contratto"),
    )
    contract_type = models.CharField(
        _("Tipo contratto"),
        max_length=30,
        choices=CONTRACT_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text=_("Tipologia del contratto"),
    )
    reference_person = models.CharField(
        _("Persona di riferimento"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Persona di riferimento per il contratto"),
    )
    status = models.CharField(
        _("Stato"),
        max_length=20,
        choices=CONTRACT_STATUS_CHOICES,
        default="DRAFT",
    )
    start_date = models.DateField(
        _("Data Inizio"), help_text=_("Data di decorrenza del contratto")
    )
    end_date = models.DateField(
        _("Data Fine"),
        null=True,
        blank=True,
        help_text=_("Data di scadenza del contratto"),
    )
    amount = models.DecimalField(
        _("Importo"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Importo totale del contratto"),
    )
    notes = models.TextField(
        _("Note/Ulteriori condizioni contrattuali"), blank=True, null=True
    )
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    class Meta:
        verbose_name = _("Contratto")
        verbose_name_plural = _("Contratti")
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["vendor", "status"]),
            models.Index(fields=["contract_number"]),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.title}"

    @property
    def is_active(self):
        if self.status != "ACTIVE":
            return False
        if self.end_date:
            return self.end_date >= timezone.now().date()
        return True


class EvaluationFrequency(models.Model):
    """
    Frequenza di valutazione espressa in mesi
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        _("Nome"),
        max_length=50,
        unique=True,
        help_text=_("Nome della frequenza (es. Mensile, Trimestrale)"),
    )
    months = models.PositiveIntegerField(
        _("Mesi"),
        unique=True,
        help_text=_("Numero di mesi tra una valutazione e la successiva"),
    )
    is_active = models.BooleanField(_("Attiva"), default=True)

    class Meta:
        verbose_name = _("Frequenza di Valutazione")
        verbose_name_plural = _("Frequenze di Valutazione")
        ordering = ["months"]

    def __str__(self):
        return f"{self.name} ({self.months} mesi)"


class EvaluationCriterion(models.Model):
    """
    Singolo criterio di valutazione appartenente a una categoria
    """

    EVALUATION_CATEGORY_CHOICES = [
        ("COMM", "Valutazione Commerciale"),
        ("CONS", "Valutazione del Servizio (Consulting)"),
        ("FCB", "Valutazione del Servizio (FCB)"),
        ("MED", "Valutazione del Servizio (MED)"),
        ("PROD_NONTEC", "Valutazione Prodotto non tecnologico"),
        ("PROD_TEC", "Valutazione Prodotto tecnologico"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(
        _("Categoria di Valutazione"),
        max_length=20,
        choices=EVALUATION_CATEGORY_CHOICES,
    )
    code = models.CharField(
        _("Codice Criterio"),
        max_length=50,
        unique=True,
        help_text=_(
            "Codice univoco del criterio (es. COMM_01, FCB_03, PROD_TEC_02)"
        ),
    )
    name = models.CharField(
        _("Nome del Criterio"),
        max_length=255,
        help_text=_(
            "Nome del criterio di valutazione (es. 'Efficienza del servizio')"
        ),
    )
    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata del criterio"),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Criterio di Valutazione")
        verbose_name_plural = _("Criteri di Valutazione")
        ordering = ["category", "code"]

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


# Modifica al Model Vendor esistente
class Vendor(models.Model):
    # Qualification Status Choices
    QUALIFICATION_STATUS_CHOICES = [
        ("PENDING", _("In attesa")),
        ("APPROVED", _("Approvato")),
        ("REJECTED", _("Respinto")),
        ("TO_REVIEW", _("Da Revisionare")),
    ]

    # Risk Level Choices
    RISK_LEVEL_CHOICES = [
        ("LOW", _("Basso")),
        ("MEDIUM", _("Medio")),
        ("HIGH", _("Alto")),
    ]
    VENDOR_TYPE_CHOICES = [
        ("Società", _("Società")),
        ("Professionista", _("Professionista")),
        ("Dipendente", _("Dipendente")),
        (
            "Dipendente + Libero professionista",
            _("Dipendente + Libero professionista"),
        ),
        ("Disoccupato", _("Disoccupato")),
        ("Libero Professionista", _("Libero Professionista")),
        ("Presso Studio", _("Presso Studio")),
        ("Prestazione Occasionale", _("Prestazione Occasionale")),
        ("Società/professionista", _("Società/professionista")),
        ("Subappaltatore", _("Subappaltatore")),
        ("Internazionale", _("Internazionale")),
        ("Formatore", _("Formatore")),
        ("Consulente", _("Consulente")),
        ("Laboratorio", _("Laboratorio")),
    ]

    SERVICE_TYPE_CHOICES = [
        ("ALTRO", "Altro"),
        ("ANALISI_LABORATORIO", "Analisi di laboratorio"),
        ("COMMERCIALE", "Commerciale"),
        ("CONSULENZA", "Consulenza"),
        ("FORNITURA", "Fornitura"),
        ("INDAGINI_STRUMENTALI", "Indagini strumentali"),
    ]

    CLUSTER_CORSO_CHOICES = [
        ("01", "GenSpDirPre"),
        ("02", "GenSpDirPre; Antincendio; Attrezzature"),
        ("03", "GenSpDirPre; Segnaletica Stradale"),
        ("04", "Antincendio"),
        ("05", "Primo Soccorso"),
        ("06", "Primo Soccorso BLSD"),
        ("08", "Attrezzature"),
        ("09", "Elearning"),
        ("11", "Manageriale"),
        ("12", "Attestati"),
        ("19", "Tutti"),
        ("20", "Ambientale"),
    ]

    CONTRACTUAL_STATUS_CHOICES = [
        ("00", "Da verificare"),
        ("02", "Fare RAI"),
        ("03", "RAI Effettuata"),
        ("04", "Contrattualizzato"),
        ("05", "Da contrattualizzare ad esigenza"),
        ("06", "Contratto Scaduto"),
        ("99", "Non Usare"),
    ]

    VENDOR_FINAL_EVALUATION_CHOICES = [
        ("DA VALUTARE", _("Da Valutare")),
        ("NEGATIVO", _("Negativo")),
        ("POSITIVO", _("Positivo")),
        ("MOLTO POSITIVO", _("Molto Positivo")),
    ]

    VENDOR_MEDICAL_SERVICE_CHOICES = [
        ("ALTRI_PROF", "Altri Professionisti"),
        ("ALTRO", "ALTRO"),
        ("AMBULANZE", "Ambulanze"),
        ("CENTRO_MEDICO", "Centro medico/Poliambulatorio"),
        ("DOCENTE", "Docente"),
        ("FORN_SANITARIE", "Forniture sanitarie/Elettromedicali"),
        ("INFERMIERE", "Infermiere"),
        ("LABORATORIO", "Laboratorio"),
        ("MEDICINA_LAVORO", "Medicina del Lavoro"),
        ("MEDICO_COMPETENTE", "Medico Competente"),
        ("MEDICO_GENERICO", "Medico Generico"),
        ("MEDICO_SPECIALISTA", "Medico Specialista"),
        ("RIFIUTI", "Rifiuti"),
        ("SOCIETA_SANITARIA", "Società Infermieri-Medici-Assistenti sociali"),
    ]

    # Società del gruppo presenti in Embyon (colonna DITTA di
    # Embyon_Fornitori_T).
    # I valori devono restare identici a quelli dell'anagrafica Embyon: sono la
    # chiave con cui il CODCONTO viene identificato (lo stesso fornitore ha un
    # codice diverso per ogni Società).
    EMBYON_COMPANY_CHOICES = [
        ("CmaSrl", "CmaSrl"),
        ("Evimed", "Evimed"),
        ("GsProtec", "GsProtec"),
        ("Igeam", "Igeam"),
        ("Sicura", "Sicura"),
    ]

    old_code = models.CharField(
        _("Codice Embyon"),
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        help_text=_("Codice Embyon (ex Vecchio codice fornitore)"),
    )

    albo_excel_row = models.PositiveIntegerField(
        _("Riga excel Albo Fornitore"),
        blank=True,
        null=True,
        db_index=True,
        help_text=_(
            "Numero di riga del foglio Excel dell'Albo Fornitori da cui il "
            "fornitore è stato importato (l'intestazione è la riga 1)"
        ),
    )

    managed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Utenti gestione fornitore"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_vendors",
        limit_choices_to={"role__in": ["admin", "bo_user"]},
        help_text=_(
            "Utente Back Office o Admin responsabile della gestione del "
            "fornitore (utente primario)"
        ),
    )
    secondary_managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Utenti gestione fornitore secondari"),
        blank=True,
        related_name="secondary_managed_vendors",
        limit_choices_to={"role__in": ["admin", "bo_user"]},
        help_text=_(
            "Ulteriori utenti Back Office o Admin di riferimento per il "
            "fornitore (opzionali)"
        ),
    )

    # Foreign Key to Address model
    address = models.ForeignKey(
        Address,
        verbose_name=_("Indirizzo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors",
        help_text=_("Indirizzo del fornitore"),
    )

    # Core Fields
    vendor_code = models.CharField(
        _("Codice Fornitore"),
        max_length=10,
        unique=True,
        primary_key=True,
        editable=False,
        help_text=_("Codice univoco del fornitore"),
        validators=[
            validators.RegexValidator(
                regex=r"^[A-Z0-9]+$",
                message=_(
                    "Il codice fornitore deve essere alfanumerico maiuscolo"
                ),
            )
        ],
    )
    name = models.CharField(
        _("Nome del Fornitore"),
        max_length=255,
        help_text=_("Nome del fornitore"),
        blank=True,
    )
    contact_details = models.TextField(
        _("Dettagli di Contatto del Fornitore"),
        help_text=_("Dettagli di contatto del fornitore"),
        blank=True,
    )
    # address = models.TextField(_("Address of Vendor"),
    # help_text=_("Indirizzo del fornitore"), blank=True)

    # New General Information Fields
    vat_number = models.CharField(
        _("Partita IVA"),
        max_length=20,
        help_text=_("Partita IVA"),
        blank=True,
        null=True,
    )
    fiscal_code = models.CharField(
        _("Codice Fiscale"),
        max_length=16,
        help_text=_("Codice fiscale"),
        blank=True,
        null=True,
    )
    email = models.EmailField(
        _("Email"), help_text=_("Email principale"), blank=True, null=True
    )
    expiry_notifications_enabled = models.BooleanField(
        _("Notifiche scadenze via email"),
        default=False,
        help_text=_(
            "Invia all'email principale i promemoria di scadenza di documenti "
            "e abilitazioni. Senza email il promemoria non parte."
        ),
    )
    reference_contact = models.CharField(
        _("Contatto di Riferimento"),
        max_length=100,
        help_text=_("Riferimento principale"),
        blank=True,
        null=True,
    )
    pec = models.EmailField(
        _("PEC"),
        blank=True,
        null=True,
        help_text=_("Posta Elettronica Certificata"),
    )
    phone = models.CharField(
        _("Telefono"),
        max_length=100,
        help_text=_("Telefono di riferimento"),
        blank=True,
        null=True,
    )
    website = models.URLField(
        _("Sito Web"), blank=True, null=True, help_text=_("Sito web aziendale")
    )
    vendor_type = models.CharField(
        _("Tipo di Fornitore"),
        max_length=50,
        choices=VENDOR_TYPE_CHOICES,
        default="Società",
        help_text=_("Tipo di fornitore"),
        blank=True,
        null=True,
    )
    user_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Utente di aggiornamento"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendors",
        help_text=_("Utente di aggiornamento associato al fornitore"),
    )
    qualification_type = models.ForeignKey(
        QualificationType,
        verbose_name=_("Titolo di Studio / Tipo di Qualifica"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors",
        help_text=_("Titolo di studio o qualifica del fornitore"),
    )

    # NUOVO: relazione many-to-many con ServiceType
    services = models.ManyToManyField(
        ServiceType,
        verbose_name=_("Servizi Erogati"),
        through="VendorService",
        blank=True,
        related_name="vendors_providing_service",
        help_text=_("Servizi erogati dal fornitore"),
    )

    cluster_corso = models.CharField(
        _("Cluster Corso"),
        max_length=50,
        choices=CLUSTER_CORSO_CHOICES,
        blank=True,
        null=True,
        help_text=_("Raggruppamento di corso per tipologia di servizio"),
    )

    vendor_task_description = models.TextField(
        _("Descrizione Attività Fornitore"),
        blank=True,
        null=True,
        help_text=_("Descrizione delle attività svolte dal fornitore"),
    )
    mobile_device = models.BooleanField(
        _("Dispositivo Mobile"),
        default=False,
        help_text=_(
            "Indica se il fornitore utilizza dispositivi mobili per le "
            "operazioni"
        ),
    )
    ambulatory_service = models.TextField(
        _("Servizio Ambulatoriale"),
        blank=True,
        null=True,
        help_text=_(
            "Descrizione dei servizi ambulatoriali offerti dal fornitore"
        ),
    )
    laboratory_service = models.BooleanField(
        _("Servizio di Laboratorio"),
        default=False,
        help_text=_("Indica se il fornitore offre servizi di laboratorio"),
    )
    laboratory_independent = models.BooleanField(
        _("Laboratorio Indipendente"),
        default=False,
        null=True,
        help_text=_("Indica se il laboratorio è indipendente"),
    )
    licensed_physician_year = models.IntegerField(
        _("Medico autorizzato dall'anno"),
        null=True,
        blank=True,
        help_text=_("Medico autorizzato dall'anno"),
    )
    vendor_medical_service = models.CharField(
        _("Servizio Sanitario/Professionale"),
        max_length=50,
        choices=VENDOR_MEDICAL_SERVICE_CHOICES,
        default="ALTRO",
        blank=True,
        null=True,
        help_text=_("Tipologia di servizio medico o sanitario fornito"),
    )
    date_of_establishment = models.DateField(
        _("Data di Specializzazione/Fondazione"),
        null=True,
        blank=True,
        help_text=_("Data di Specializzazione o Fondazione"),
    )
    other_medical_service = models.TextField(
        _("Altri Servizi Medici"),
        blank=True,
        null=True,
        help_text=_(
            "Descrizione di altri servizi medici offerti dal fornitore"
        ),
    )
    doctor_registration = models.TextField(
        _("Titolo Iscrizione Albo Medici"),
        blank=True,
        null=True,
        help_text=_(
            "Descrizione del titolo di iscrizione all'albo dei medici"
        ),
    )
    doctor_cv = models.BooleanField(
        _("CV del Medico Disponibile"),
        default=False,
        help_text=_("Indica se il curriculum vitae del medico è disponibile"),
    )
    doctor_cv2 = models.BooleanField(
        _("CV2 del Medico Disponibile"),
        default=False,
        help_text=_(
            "Indica se il secondo curriculum vitae del medico è disponibile"
        ),
    )

    # Contractual Fields
    contractual_status = models.CharField(
        _("Stato Contrattuale"),
        max_length=2,
        choices=CONTRACTUAL_STATUS_CHOICES,
        default="00",
        help_text=_("Indica lo stato contrattuale del fornitore"),
    )
    contractual_start_date = models.DateField(
        _("Data Inizio Contratto"),
        null=True,
        blank=True,
        help_text=_("Data di inizio del contratto con il fornitore"),
    )
    contractual_end_date = models.DateField(
        _("Data Fine Contratto"),
        null=True,
        blank=True,
        help_text=_("Data di fine del contratto con il fornitore"),
    )
    contractual_terms = models.TextField(
        _("Termini Contrattuali"),
        blank=True,
        null=True,
        help_text=_("Termini e condizioni del contratto con il fornitore"),
    )
    reference_person = models.CharField(
        _("Persona di Riferimento"),
        max_length=100,
        help_text=_("Persona di riferimento"),
        blank=True,
        null=True,
    )
    vendor_management_update = models.CharField(
        _("Gestione aggiornamenti"),
        max_length=100,
        help_text=_("Gestione aggiornamenti del fornitore"),
        blank=True,
        null=True,
    )
    embyon_company = models.CharField(
        _("Società Embyon"),
        max_length=50,
        choices=EMBYON_COMPANY_CHOICES,
        help_text=_(
            "Società Embyon (DITTA) presso cui il fornitore è censito"
        ),
        blank=True,
        null=True,
    )
    embyon_active = models.BooleanField(
        _("Attivo in Embyon"),
        default=True,
        help_text=_("Indica se il fornitore risulta attivo in Embyon"),
    )

    # Performance Fields (existing)
    on_time_delivery_rate = models.FloatField(
        _("Tasso di Consegna Puntuale"),
        help_text=_("Rating di Consegna Puntuale del Fornitore"),
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(100),
        ],
        null=True,
        blank=True,
    )
    quality_rating_avg = models.FloatField(
        _("Valutazione Media Qualità"),
        help_text=_("Rating Medio di Qualità del Fornitore"),
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(5),
        ],
        null=True,
        blank=True,
    )
    average_response_time = models.FloatField(
        _("Tempo di Risposta Medio"),
        help_text=_("Tempo di Risposta Medio del Fornitore in Ore"),
        validators=[validators.MinValueValidator(0)],
        null=True,
        blank=True,
    )
    fulfillment_rate = models.FloatField(
        _("Tasso di Adempimento"),
        help_text=_("Rating di Adempimento del Fornitore"),
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(100),
        ],
        null=True,
        blank=True,
    )

    # Qualification/Compliance Fields
    qualification_status = models.CharField(
        _("Stato di Qualifica"),
        max_length=20,
        choices=QUALIFICATION_STATUS_CHOICES,
        default="PENDING",
        help_text=_("Stato della qualifica del fornitore"),
        blank=True,
        null=True,
    )
    qualification_score = models.FloatField(
        _("Punteggio di Qualifica"),
        validators=[
            validators.MinValueValidator(0),
            validators.MaxValueValidator(100),
        ],
        null=True,
        blank=True,
        help_text=_("Punteggio medio di qualifica (0-100)"),
    )
    qualification_date = models.DateField(
        _("Data di Qualifica"),
        null=True,
        blank=True,
        help_text=_("Data di qualifica o revisione"),
    )
    qualification_expiry = models.DateField(
        _("Scadenza Qualifica"),
        null=True,
        blank=True,
        help_text=_("Scadenza della qualifica (es. ogni 12 mesi)"),
    )
    vendor_final_evaluation = models.CharField(
        _("Valutazione Finale del Fornitore"),
        max_length=20,
        choices=VENDOR_FINAL_EVALUATION_CHOICES,
        default="DA VALUTARE",
        help_text=_("Valutazione finale complessiva del fornitore"),
        blank=True,
        null=True,
    )

    category = models.ForeignKey(
        Category,
        verbose_name=_("Classificazione"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors",
        help_text=_("Classificazione principale del fornitore"),
    )
    additional_categories = models.ManyToManyField(
        Category,
        verbose_name=_("Classificazioni aggiuntive"),
        blank=True,
        related_name="additional_vendors",
        help_text=_(
            "Ulteriori classificazioni del fornitore, oltre a quella "
            "principale (opzionali)"
        ),
    )
    # Copertura territoriale del fornitore. Le province sono
    # l'unica verità: la copertura di una regione è DERIVATA (risulta
    # coperta quando lo sono tutte le sue province), così non esistono due
    # fonti in contraddizione. Le nazioni estere stanno in un campo a
    # parte perché a catalogo non hanno regioni/province.
    competence_provinces = models.ManyToManyField(
        Province,
        verbose_name=_("Province di competenza"),
        blank=True,
        related_name="competent_vendors",
        help_text=_(
            "Province italiane in cui il fornitore opera. La copertura di "
            "una regione è derivata: risulta selezionata quando lo sono "
            "tutte le sue province."
        ),
    )
    competence_countries = models.ManyToManyField(
        Country,
        verbose_name=_("Nazioni estere di competenza"),
        blank=True,
        related_name="competent_vendors",
        help_text=_(
            "Nazioni senza articolazione in regioni/province a catalogo, "
            "selezionabili solo a livello nazione. L'Italia non va mai "
            "qui: la sua copertura si esprime con le province."
        ),
    )
    first_supply_date = models.DateField(
        _("Data Prima Fornitura"),
        null=True,
        blank=True,
        help_text=_(
            "Data del primo servizio di fornitura erogato dal fornitore"
        ),
    )
    # Competences relationship
    competences = models.ManyToManyField(
        Competence,
        verbose_name=_("Competenze"),
        through="VendorCompetence",
        blank=True,
        related_name="vendors_with_competence",
        help_text=_("Competenze possedute dal fornitore"),
    )

    # Document relationship (nuovo)
    vendor_documents = models.ManyToManyField(
        Document,
        verbose_name=_("Documenti"),
        blank=True,
        related_name="vendors",
        help_text=_("Documenti associati al fornitore"),
    )

    risk_level = models.CharField(
        _("Livello di Affidabilità/Rischio"),
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default="MEDIUM",
        help_text=_("Valutazione dell'affidabilità/rischio del fornitore"),
        blank=True,
        null=True,
    )
    # Audit and Management Fields
    last_audit_date = models.DateField(
        _("Data Ultimo Audit"),
        null=True,
        blank=True,
        help_text=_("Ultimo audit condotto"),
    )
    next_audit_due = models.DateField(
        _("Prossimo Audit Previsto"),
        null=True,
        blank=True,
        help_text=_("Prossima data audit prevista"),
    )
    review_notes = models.TextField(
        _("Note di Revisione"),
        blank=True,
        null=True,
        help_text=_("Note di revisione e valutazione"),
    )
    is_active = models.BooleanField(
        _("È Attivo"), default=True, help_text=_("Fornitore attivo")
    )
    is_ico_consultant = models.BooleanField(
        _("È Consulente ICO"),
        default=False,
        help_text=_("Indica se il fornitore è un consulente ICO"),
    )
    albo_zucchetti = models.CharField(
        _("Inserito in Albo Zucchetti"), max_length=20, blank=True, null=True
    )

    class Meta:
        verbose_name = _("Fornitore")
        verbose_name_plural = _("Fornitori")
        ordering = ["name"]

    # String representation
    def __str__(self):
        return self.name

    # Save method
    def save(self, *args, **kwargs):
        # If vendor code is not specified
        if not self.vendor_code:
            # Generate a new vendor code
            self.vendor_code = str(uuid.uuid4()).replace("-", "")[:10].upper()

        # Un fornitore nuovo senza stato parte sempre "In attesa".
        if self._state.adding and not self.qualification_status:
            self.qualification_status = "PENDING"

        # Un fornitore esistente non può restare "Approvato" se la
        # documentazione obbligatoria non è in regola.
        if (
            not self._state.adding
            and self.qualification_status == "APPROVED"
            and self.qualification_blockers
        ):
            self.qualification_status = "TO_REVIEW"

        # Save the model
        super().save(*args, **kwargs)

    @property
    def qualification_blockers(self):
        """Elenco (stringhe leggibili) dei documenti e requisiti OBBLIGATORI
        assegnati che impediscono la qualifica: non caricati, non approvati
        dal gestore o scaduti. Lista vuota = fornitore approvabile."""
        return self._mandatory_gaps("satisfies_requirement")

    def _mandatory_gaps(self, check):
        """Obbligatori assegnati per cui la property `check` è falsa."""
        if self._state.adding:
            return []
        gaps = []
        # L'obbligatorietà è definita a catalogo: Document.document_type
        # .is_required e Competence.is_mandatory.
        for doc in Document.objects.filter(
            vendor=self, document_type__is_required=True
        ).select_related("document_type"):
            if not getattr(doc, check):
                gaps.append(f"Documento: {doc.document_type.name}")
        for req in self.vendor_competences.filter(
            competence__is_mandatory=True
        ).select_related("competence"):
            if not getattr(req, check):
                gaps.append(f"Requisito: {req.competence.name}")
        return gaps

    def sync_qualification_status(self):
        """Riallinea lo stato di qualifica dopo una modifica ai record
        assegnati: se è 'Approvato' ma non è più in regola passa a 'Da
        Revisionare'. Non riapprova mai in automatico."""
        if self.qualification_status == "APPROVED" and self.pk:
            if self.qualification_blockers:
                Vendor.objects.filter(pk=self.pk).update(
                    qualification_status="TO_REVIEW"
                )
                self.qualification_status = "TO_REVIEW"

    def submit_for_review_if_complete(self):
        """Dopo un upload del fornitore: se è 'In attesa' o 'Respinto' e ha
        consegnato tutti i documenti/requisiti obbligatori (caricati, non
        scaduti, non respinti) passa a 'Da Revisionare'. Chi è 'Approvato'
        non viene mai toccato qui."""
        if self.qualification_status in ("PENDING", "REJECTED", "", None):
            if not self._mandatory_gaps("is_delivered"):
                Vendor.objects.filter(pk=self.pk).update(
                    qualification_status="TO_REVIEW"
                )
                self.qualification_status = "TO_REVIEW"

    # Properties for better data visualization
    @property
    def is_qualified(self):
        """Returns True if vendor is approved, documentation is in order and
        qualification is not expired"""
        if self.qualification_status != "APPROVED":
            return False
        if self.qualification_blockers:
            return False
        if self.qualification_expiry:
            return self.qualification_expiry > timezone.now().date()
        return True

    @property
    def audit_overdue(self):
        """Returns True if next audit is overdue"""
        if self.next_audit_due:
            return self.next_audit_due < timezone.now().date()
        return False

    @property
    def primary_service(self):
        """Ritorna il servizio principale del fornitore"""
        primary = self.vendor_services.filter(is_primary=True).first()
        return primary.service_type if primary else None

    @property
    def active_services(self):
        """Ritorna i servizi attivi del fornitore"""
        return self.vendor_services.filter(
            models.Q(end_date__isnull=True)
            | models.Q(end_date__gte=timezone.now().date())
        )

    @property
    def active_competences(self):
        """Ritorna le competenze attive del fornitore"""
        return self.vendor_competences.filter(
            has_competence=True, competence__is_active=True
        )

    @property
    def expired_competences(self):
        """Ritorna le competenze scadute"""
        return self.vendor_competences.filter(
            has_competence=True, expiry_date__lt=timezone.now().date()
        )

    @property
    def expiring_competences(self):
        """Ritorna le competenze in scadenza (entro i giorni di preavviso
        del requisito, solo per i requisiti che richiedono rinnovo)"""
        today = timezone.now().date()
        candidates = self.vendor_competences.filter(
            has_competence=True,
            expiry_date__gte=today,
            competence__requires_renewal=True,
        ).select_related("competence")
        return [vc for vc in candidates if vc.expiry_status == "EXPIRING_SOON"]

    @property
    def missing_mandatory_competences(self):
        """Ritorna le competenze obbligatorie mancanti per la categoria del
        fornitore"""
        if not self.category:
            return Competence.objects.none()

        # Competenze obbligatorie per la categoria
        required = self.category.required_competences.filter(
            is_mandatory=True, is_active=True
        )

        # Competenze già possedute
        possessed_ids = self.vendor_competences.filter(
            has_competence=True
        ).values_list("competence_id", flat=True)

        # Ritorna quelle mancanti
        return required.exclude(id__in=possessed_ids)

    @property
    def valid_documents(self):
        """Ritorna i documenti validi del fornitore"""
        return self.vendor_documents.filter(status="APPROVED").exclude(
            expiry_date__lt=timezone.now().date()
        )

    @property
    def expired_documents(self):
        """Ritorna i documenti scaduti"""
        return self.vendor_documents.filter(
            expiry_date__lt=timezone.now().date()
        )

    @property
    def invalid_documents(self):
        """Ritorna i documenti NON validi: non 'Approvato' (NOT VALID) oppure
        scaduti. Complementare di valid_documents."""
        return self.vendor_documents.filter(
            ~models.Q(status="APPROVED")
            | models.Q(expiry_date__lt=timezone.now().date())
        )

    @property
    def expiring_documents(self):
        """Ritorna i documenti in scadenza (entro i giorni di preavviso)"""
        documents_expiring = []
        for doc in self.vendor_documents.filter(
            status="APPROVED", expiry_date__isnull=False
        ):
            if doc.expiry_date >= timezone.now().date():
                days_to_expiry = (doc.expiry_date - timezone.now().date()).days
                if (
                    doc.document_type.reminder_days_before is not None
                    and days_to_expiry
                    <= doc.document_type.reminder_days_before
                ):
                    documents_expiring.append(doc)
        return documents_expiring

    @property
    def missing_mandatory_documents(self):
        """Ritorna i documenti obbligatori mancanti per la categoria del
        fornitore"""
        if not self.category:
            return DocumentCatalog.objects.none()

        required = DocumentCatalog.objects.filter(is_required=True)

        submitted_ids = self.vendor_documents.filter(
            status__in=["APPROVED", "UPLOADED"]
        ).values_list("document_type_id", flat=True)

        return required.exclude(id__in=submitted_ids)

    @property
    def is_documentation_complete(self):
        """Verifica se tutta la documentazione obbligatoria è presente e
        valida.
        Un documento obbligatorio è valido solo se 'Approvato' e non scaduto:
        qualunque obbligatorio NOT VALID rende la documentazione incompleta."""
        missing = self.missing_mandatory_documents
        invalid = self.invalid_documents.filter(
            document_type__is_required=True
        )
        return not missing.exists() and not invalid.exists()

    # Alias di compatibilità: mantiene self.documents.filter(...)
    @property
    def documents(self):
        return self.vendor_documents


def generate_operational_attributes_id():
    """uuid.uuid4() già convertito a stringa, per il campo id di
    VendorOperationalAttributes."""
    return str(uuid.uuid4())


class VendorOperationalAttributes(models.Model):
    """
    Attributi operativi del fornitore: capacità, mezzi e attrezzature proprie,
    condizioni economiche, disponibilità operative e livello di autonomia.
    """

    AUTONOMY_CATEGORY_CHOICES = [
        (1, _("Solo Manodopera (serve capocantiere + PM Sicura)")),
        (2, _("Autonomia limitata (serve PM Sicura)")),
        (3, _("Totale autonomia")),
    ]

    id = models.CharField(
        primary_key=True,
        editable=False,
        default=generate_operational_attributes_id,
        max_length=36,
    )

    vendor = models.OneToOneField(
        "Vendor",
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="operational_attributes",
    )

    # Capacità Operativa
    total_operators = models.PositiveIntegerField(
        _("Numero Totale Operatori"),
        blank=True,
        null=True,
        help_text=_("Numero totale di operatori disponibili"),
    )

    # Mezzi e Attrezzature Proprie
    equipped_vans = models.BooleanField(
        _("Furgoni attrezzati (carrofficina)"), default=False
    )

    aerial_platforms = models.BooleanField(
        _("Piattaforme - PLE"), default=False
    )

    aerial_platforms_notes = models.TextField(
        _("Note Piattaforme - PLE"),
        blank=True,
        null=True,
        help_text=_("Tipologia, altezza, portata"),
    )

    mobile_scaffolding = models.BooleanField(
        _("Ponteggio mobile"), default=False
    )

    mobile_scaffolding_notes = models.TextField(
        _("Note Ponteggio mobile"),
        blank=True,
        null=True,
        help_text=_("Tipologia, altezza"),
    )

    equipped_vehicle_for_inspections = models.BooleanField(
        _("Mezzo attrezzato (per revisione e collaudi sul posto)"),
        default=False,
    )

    lifting_equipment = models.BooleanField(
        _("Mezzi di sollevamento (camion gru/carrello elevatore)"),
        default=False,
    )

    lifting_equipment_notes = models.TextField(
        _("Note Mezzi di sollevamento"),
        blank=True,
        null=True,
        help_text=_("Tipologia, altezza, portata"),
    )

    atex_equipment = models.BooleanField(
        _("Strumentazione ATEX"), default=False
    )

    # Condizioni Economiche
    standard_hourly_labor_cost = models.DecimalField(
        _("Costo Orario Standard Manodopera (€)"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )

    travel_cost = models.DecimalField(
        _("Costo Trasferta (€)"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )

    mileage_reimbursement = models.BooleanField(
        _("Rimborso Chilometrico"), default=False
    )

    mileage_reimbursement_value = models.DecimalField(
        _("Valore Rimborso Chilometrico (€/km)"),
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )

    consumable_materials_supply = models.BooleanField(
        _("Fornitura Materiali di consumo (tubo, cavo…)"), default=False
    )

    specialist_materials_supply = models.BooleanField(
        _("Fornitura materiale specialistico"), default=False
    )

    # Disponibilità Operative
    site_survey_availability = models.BooleanField(
        _("Disponibilità Sopralluoghi per Sicura"), default=False
    )

    travel_availability = models.BooleanField(
        _("Disponibilità Trasferte"), default=False
    )

    # Disponibilità Attività in Fermata Impianto/Weekend
    weekend_holiday_shutdown_availability = models.BooleanField(
        _("Disponibilità attività in fermata impianto / weekend/festivi"),
        default=False,
    )

    night_shutdown_availability = models.BooleanField(
        _("Disponibilità attività in fermata impianto / notturno"),
        default=False,
    )

    # Disponibilità Commissioning/Avviamenti
    commissioning_support_availability = models.BooleanField(
        _("Disponibilità supporto commissioning / collaudi"), default=False
    )

    # Livello Autonomia
    autonomy_category = models.PositiveSmallIntegerField(
        _("Categoria Autonomia"),
        choices=AUTONOMY_CATEGORY_CHOICES,
        blank=True,
        null=True,
    )

    # Esperienza Settori Specifici
    experience_logistics = models.BooleanField(_("Logistica"), default=False)
    experience_data_center = models.BooleanField(
        _("Data center"), default=False
    )
    experience_industry_manufacturing = models.BooleanField(
        _("Industria/manufatturiero"), default=False
    )
    experience_tertiary_offices_hospitality = models.BooleanField(
        _("Terziario/uffici/alberghiero"), default=False
    )
    experience_food_pharma = models.BooleanField(
        _("Alimentare/farmaceutico"), default=False
    )
    experience_healthcare = models.BooleanField(
        _("Ospedaliero"), default=False
    )
    experience_retail = models.BooleanField(_("Retail"), default=False)
    experience_oil_gas = models.BooleanField(_("Oil & Gas"), default=False)
    experience_public_administration = models.BooleanField(
        _("Pubblica Amministrazione"), default=False
    )

    class Meta:
        verbose_name = _("Attributi Operativi")
        verbose_name_plural = _("Attributi Operativi")

    def __str__(self):
        return f"Attributi Operativi - {self.vendor.name}"


class Evaluator(models.Model):
    """
    Valutatore che può essere associato alle valutazioni dei fornitori
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(_("Nome"), max_length=100)
    last_name = models.CharField(_("Cognome"), max_length=100)
    email = models.EmailField(_("Email"), unique=True, blank=True, null=True)
    role = models.CharField(
        _("Ruolo"),
        max_length=150,
        blank=True,
        null=True,
        help_text=_("Ruolo o qualifica del valutatore"),
    )
    department = models.CharField(
        _("Dipartimento"), max_length=150, blank=True, null=True
    )
    is_active = models.BooleanField(_("Attivo"), default=True)
    created_at = models.DateTimeField(_("Data Creazione"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Data Aggiornamento"), auto_now=True)

    class Meta:
        verbose_name = _("Valutatore")
        verbose_name_plural = _("Valutatori")
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class VendorEvaluation(models.Model):
    """
    Punteggio assegnato a un fornitore per un determinato criterio
    """

    EVALUATION_SCALE = [
        (1, "Scarso"),
        (2, "Insufficiente"),
        (3, "Non sufficiente"),
        (4, "Al limite della sufficienza"),
        (5, "Sufficiente"),
        (6, "Buono"),
        (7, "Ottimo"),
        (8, "Eccellente"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        "Vendor",
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="evaluations",
    )
    criterion = models.ForeignKey(
        EvaluationCriterion,
        verbose_name=_("Criterio di Valutazione"),
        on_delete=models.CASCADE,
        related_name="vendor_scores",
    )
    score = models.PositiveSmallIntegerField(
        _("Punteggio"),
        choices=EVALUATION_SCALE,
        help_text=_("Valutazione da 1 (Scarso) a 8 (Eccellente)"),
    )
    evaluator = models.ForeignKey(
        Evaluator,
        verbose_name=_("Valutatore"),
        on_delete=models.SET_NULL,
        related_name="evaluations",
        blank=True,
        null=True,
    )
    evaluation_frequency = models.ForeignKey(
        EvaluationFrequency,
        verbose_name=_("Frequenza di Valutazione"),
        on_delete=models.SET_NULL,
        related_name="evaluations",
        blank=True,
        null=True,
        default=None,
    )

    def save(self, *args, **kwargs):
        if self.evaluation_frequency_id is None:
            try:
                self.evaluation_frequency = EvaluationFrequency.objects.get(
                    months=12
                )
            except EvaluationFrequency.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    notes = models.TextField(_("Note"), blank=True, null=True)
    evaluated_at = models.DateField(_("Data Valutazione"), auto_now_add=True)

    class Meta:
        verbose_name = _("Valutazione")
        verbose_name_plural = _("Valutazioni")
        unique_together = ("vendor", "criterion")

    def __str__(self):
        return (
            f"{self.vendor.name} - {self.criterion.name}: "
            f"{self.get_score_display()}"
        )


class ExpiryReminderLog(models.Model):
    """Promemoria di scadenza già inviati al fornitore.

    Una riga per elemento, scadenza e stadio: impedisce di reinviare lo
    stesso promemoria. Se l'elemento viene rinnovato la scadenza cambia,
    quindi i promemoria ripartono per il nuovo ciclo.
    """

    KIND_DOCUMENT = "DOCUMENT"
    KIND_COMPETENCE = "COMPETENCE"
    KIND_CHOICES = [
        (KIND_DOCUMENT, _("Documento")),
        (KIND_COMPETENCE, _("Abilitazione/Requisito")),
    ]

    STAGE_FIRST = "FIRST"
    STAGE_SECOND = "SECOND"
    STAGE_CHOICES = [
        (STAGE_FIRST, _("Primo promemoria")),
        (STAGE_SECOND, _("Ultimo avviso (7 giorni)")),
    ]

    vendor = models.ForeignKey(
        Vendor,
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="expiry_reminders",
    )
    item_kind = models.CharField(
        _("Tipo elemento"), max_length=20, choices=KIND_CHOICES
    )
    # Document ha un id CharField, VendorCompetence un uuid: niente FK.
    item_id = models.CharField(_("ID elemento"), max_length=64)
    item_label = models.CharField(_("Elemento"), max_length=255)
    expiry_date = models.DateField(_("Data scadenza"))
    stage = models.CharField(_("Stadio"), max_length=10, choices=STAGE_CHOICES)
    recipients = models.CharField(_("Destinatari"), max_length=500)
    sent_at = models.DateTimeField(_("Inviato il"), auto_now_add=True)

    class Meta:
        verbose_name = _("Promemoria scadenza inviato")
        verbose_name_plural = _("Promemoria scadenze inviati")
        ordering = ["-sent_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["item_kind", "item_id", "expiry_date", "stage"],
                name="unique_expiry_reminder_per_stage",
            )
        ]

    def __str__(self):
        return f"{self.vendor.name} - {self.item_label} ({self.stage})"


@receiver([post_save, post_delete], sender=Document)
def _sync_vendor_on_document_change(sender, instance, **kwargs):
    vendor = Vendor.objects.filter(pk=instance.vendor_id).first()
    if vendor:
        vendor.sync_qualification_status()


@receiver([post_save, post_delete], sender=VendorCompetence)
def _sync_vendor_on_competence_change(sender, instance, **kwargs):
    vendor = Vendor.objects.filter(pk=instance.vendor_id).first()
    if vendor:
        vendor.sync_qualification_status()


def _sync_approved_vendors(vendors):
    for vendor in vendors.filter(qualification_status="APPROVED"):
        vendor.sync_qualification_status()


@receiver(post_save, sender=DocumentCatalog)
def _sync_vendors_on_document_catalog_change(sender, instance, **kwargs):
    """Se cambia l'obbligatorietà di un tipo di documento, riallinea lo stato
    di qualifica dei fornitori a cui è assegnato."""
    _sync_approved_vendors(
        Vendor.objects.filter(
            pk__in=Document.objects.filter(document_type=instance).values(
                "vendor"
            )
        )
    )


@receiver(post_save, sender=Competence)
def _sync_vendors_on_competence_catalog_change(sender, instance, **kwargs):
    """Come sopra, per i requisiti professionali."""
    _sync_approved_vendors(
        Vendor.objects.filter(
            pk__in=VendorCompetence.objects.filter(competence=instance).values(
                "vendor"
            )
        )
    )
