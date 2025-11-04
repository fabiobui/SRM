# Imports
import uuid

from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

# Nuovo Model per Category
class Category(models.Model):
    """
    Modello per gestire le categorie merceologiche dei fornitori
    """
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Core fields
    code = models.CharField(
        _("Codice Categoria"),
        max_length=20,
        unique=True,
        help_text=_("Codice univoco della categoria (es. 'SERV', 'FORN', 'MANU')")
    )
    
    name = models.CharField(
        _("Nome Categoria"),
        max_length=100,
        help_text=_("Nome della categoria")
    )
    
    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata della categoria")
    )
    
    # Hierarchical structure (optional)
    parent = models.ForeignKey(
        'self',
        verbose_name=_("Categoria Padre"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='subcategories',
        help_text=_("Categoria padre per struttura gerarchica")
    )
    
    # Status and classification
    is_active = models.BooleanField(
        _("È Attiva"),
        default=True,
        help_text=_("Categoria attiva e utilizzabile")
    )
    
    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"),
        default=100,
        help_text=_("Ordine di visualizzazione")
    )
    
    # Color coding for UI
    color_code = models.CharField(
        _("Codice Colore"),
        max_length=7,
        blank=True,
        null=True,
        help_text=_("Codice colore esadecimale (es. #FF5733)")
    )
    
    # Metadata
    created_at = models.DateTimeField(
        _("Creato il"),
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        _("Aggiornato il"),
        auto_now=True
    )
    
    # Business rules
    requires_certification = models.BooleanField(
        _("Richiede Certificazione"),
        default=False,
        help_text=_("Categoria che richiede certificazioni specifiche")
    )
    
    default_risk_level = models.CharField(
        _("Livello di Rischio Predefinito"),
        max_length=20,
        choices=[
            ('LOW', _('Basso')),
            ('MEDIUM', _('Medio')),
            ('HIGH', _('Alto')),
        ],
        default='MEDIUM',
        help_text=_("Livello di rischio di default per questa categoria")
    )

    class Meta:
        verbose_name = _("Categoria")
        verbose_name_plural = _("Categorie")
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active', 'sort_order']),
            models.Index(fields=['parent']),
        ]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
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
        return self.vendors.filter(is_active=True).count() if hasattr(self, 'vendors') else 0
    
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
                    raise ValidationError(_("Una categoria non può essere genitore di se stessa"))
                parent = parent.parent
        
        # Valida il codice colore
        if self.color_code:
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', self.color_code):
                from django.core.exceptions import ValidationError
                raise ValidationError(_("Il codice colore deve essere in formato esadecimale (es. #FF5733)"))

    def save(self, *args, **kwargs):
        # Auto-genera il code se non specificato
        if not self.code:
            self.code = self.name[:20].upper().replace(' ', '_')
        
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


# Model for Competence
class Competence(models.Model):
    """
    Modello per gestire le competenze/qualifiche dei fornitori
    """
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Core fields
    code = models.CharField(
        _("Codice Competenza"),
        max_length=50,
        unique=True,
        help_text=_("Codice univoco della competenza (es. 'RSPP', 'ASPP')")
    )
    
    name = models.CharField(
        _("Nome Competenza"),
        max_length=255,
        help_text=_("Nome della competenza/qualifica")
    )
    
    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata della competenza")
    )
    
    # Categorization
    competence_category = models.CharField(
        _("Categoria Competenza"),
        max_length=50,
        choices=[
            ('SAFETY', _('Sicurezza')),
            ('QUALITY', _('Qualità')),
            ('TECHNICAL', _('Tecnico')),
            ('ENERGY', _('Energia')),
            ('ENVIRONMENT', _('Ambiente')),
            ('AUDIT', _('Audit/Certificazioni')),
            ('OTHER', _('Altro')),
        ],
        default='TECHNICAL',
        help_text=_("Categoria della competenza")
    )
    
    # Requirements
    requires_certification = models.BooleanField(
        _("Richiede Certificazione"),
        default=True,
        help_text=_("Indica se la competenza richiede una certificazione formale")
    )
    
    requires_renewal = models.BooleanField(
        _("Richiede Rinnovo"),
        default=False,
        help_text=_("Indica se la competenza ha una scadenza e necessita rinnovo")
    )
    
    renewal_period_months = models.PositiveIntegerField(
        _("Periodo Rinnovo (mesi)"),
        null=True,
        blank=True,
        help_text=_("Numero di mesi prima della scadenza (es. 12, 24, 36)")
    )
    
    # Business rules
    is_mandatory = models.BooleanField(
        _("È Obbligatoria"),
        default=False,
        help_text=_("Competenza obbligatoria per alcune categorie di fornitori")
    )
    
    is_active = models.BooleanField(
        _("È Attiva"),
        default=True,
        help_text=_("Competenza attiva e utilizzabile")
    )
    
    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"),
        default=100,
        help_text=_("Ordine di visualizzazione")
    )
    
    # Metadata
    created_at = models.DateTimeField(
        _("Creato il"),
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        _("Aggiornato il"),
        auto_now=True
    )
    
    # Related categories
    applicable_categories = models.ManyToManyField(
        Category,
        verbose_name=_("Categorie Applicabili"),
        blank=True,
        related_name="required_competences",
        help_text=_("Categorie per cui questa competenza è rilevante")
    )

    class Meta:
        verbose_name = _("Competenza")
        verbose_name_plural = _("Competenze")
        ordering = ['competence_category', 'sort_order', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['competence_category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


# Model for VendorCompetence (through table)
class VendorCompetence(models.Model):
    """
    Modello per associare competenze ai fornitori con informazioni aggiuntive
    """
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Relations
    vendor = models.ForeignKey(
        'Vendor',
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="vendor_competences"
    )
    
    competence = models.ForeignKey(
        Competence,
        verbose_name=_("Competenza"),
        on_delete=models.CASCADE,
        related_name="vendor_assignments"
    )
    
    # Status
    has_competence = models.BooleanField(
        _("Possiede Competenza"),
        default=True,
        help_text=_("Il fornitore possiede questa competenza")
    )
    
    # Certification details
    certification_number = models.CharField(
        _("Numero Certificazione"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Numero del certificato/attestato")
    )
    
    certification_body = models.CharField(
        _("Ente Certificatore"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Ente che ha rilasciato la certificazione")
    )
    
    issue_date = models.DateField(
        _("Data Rilascio"),
        null=True,
        blank=True,
        help_text=_("Data di rilascio della certificazione")
    )
    
    expiry_date = models.DateField(
        _("Data Scadenza"),
        null=True,
        blank=True,
        help_text=_("Data di scadenza della certificazione")
    )
    
    # Verification
    verified = models.BooleanField(
        _("Verificata"),
        default=False,
        help_text=_("Competenza verificata dall'azienda")
    )
    
    verified_by = models.CharField(
        _("Verificata da"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Persona che ha verificato la competenza")
    )
    
    verified_date = models.DateField(
        _("Data Verifica"),
        null=True,
        blank=True,
        help_text=_("Data di verifica")
    )
    
    # Documentation
    document_file = models.FileField(
        _("File Documento"),
        upload_to='vendor_competences/%Y/%m/',
        blank=True,
        null=True,
        help_text=_("File del certificato/attestato")
    )
    
    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True,
        help_text=_("Note aggiuntive sulla competenza")
    )
    
    # Metadata
    created_at = models.DateTimeField(
        _("Creato il"),
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        _("Aggiornato il"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Competenza Fornitore")
        verbose_name_plural = _("Competenze Fornitori")
        unique_together = [['vendor', 'competence']]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'competence']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['verified']),
        ]

    def __str__(self):
        return f"{self.vendor.name} - {self.competence.name}"
    
    @property
    def is_expired(self):
        """Verifica se la certificazione è scaduta"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
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
            return 'NO_EXPIRY'
        
        days = self.days_to_expiry
        if days < 0:
            return 'EXPIRED'
        elif days <= 30:
            return 'EXPIRING_SOON'
        elif days <= 90:
            return 'EXPIRING'
        return 'VALID'


# Model for DocumentType
class DocumentType(models.Model):
    """
    Modello per gestire i tipi di documenti richiesti ai fornitori
    """
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Core fields
    code = models.CharField(
        _("Codice Documento"),
        max_length=50,
        unique=True,
        help_text=_("Codice univoco del tipo di documento (es. 'DURC', 'VISURA')")
    )
    
    name = models.CharField(
        _("Nome Documento"),
        max_length=255,
        help_text=_("Nome del tipo di documento")
    )
    
    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata del documento")
    )
    
    # Categorization
    document_category = models.CharField(
        _("Categoria Documento"),
        max_length=50,
        choices=[
            ('LEGAL', _('Legale/Amministrativo')),
            ('FINANCIAL', _('Finanziario')),
            ('SAFETY', _('Sicurezza')),
            ('QUALITY', _('Qualità')),
            ('TECHNICAL', _('Tecnico')),
            ('INSURANCE', _('Assicurativo')),
            ('CERTIFICATION', _('Certificazioni')),
            ('OTHER', _('Altro')),
        ],
        default='LEGAL',
        help_text=_("Categoria del documento")
    )
    
    # Requirements
    is_mandatory = models.BooleanField(
        _("È Obbligatorio"),
        default=True,
        help_text=_("Documento obbligatorio per la qualifica")
    )
    
    requires_renewal = models.BooleanField(
        _("Richiede Rinnovo"),
        default=True,
        help_text=_("Documento con scadenza che necessita rinnovo")
    )
    
    default_validity_days = models.PositiveIntegerField(
        _("Validità Predefinita (giorni)"),
        null=True,
        blank=True,
        help_text=_("Numero di giorni di validità standard (es. 120 per DURC)")
    )
    
    # Business rules
    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Tipo di documento attivo e utilizzabile")
    )
    
    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"),
        default=100,
        help_text=_("Ordine di visualizzazione")
    )
    
    # Alert settings
    alert_days_before_expiry = models.PositiveIntegerField(
        _("Giorni Preavviso Scadenza"),
        default=30,
        help_text=_("Giorni prima della scadenza per inviare alert")
    )
    
    # Metadata
    created_at = models.DateTimeField(
        _("Creato il"),
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        _("Aggiornato il"),
        auto_now=True
    )
    
    # Related categories
    applicable_categories = models.ManyToManyField(
        Category,
        verbose_name=_("Categorie Applicabili"),
        blank=True,
        related_name="required_documents",
        help_text=_("Categorie per cui questo documento è richiesto")
    )
    
    # Template and instructions
    template_file = models.FileField(
        _("File Template"),
        upload_to='document_templates/',
        blank=True,
        null=True,
        help_text=_("Template o modello del documento")
    )
    
    instructions = models.TextField(
        _("Istruzioni"),
        blank=True,
        null=True,
        help_text=_("Istruzioni per il fornitore su come compilare/ottenere il documento")
    )

    class Meta:
        verbose_name = _("Tipo Documento")
        verbose_name_plural = _("Tipi Documento")
        ordering = ['document_category', 'sort_order', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['document_category', 'is_active']),
            models.Index(fields=['is_mandatory']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


# Model for VendorDocument
class VendorDocument(models.Model):
    """
    Modello per associare documenti specifici ai fornitori
    """
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Relations
    vendor = models.ForeignKey(
        'Vendor',
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="vendor_documents"
    )
    
    document_type = models.ForeignKey(
        DocumentType,
        verbose_name=_("Tipo Documento"),
        on_delete=models.CASCADE,
        related_name="vendor_submissions"
    )
    
    # Document details
    document_number = models.CharField(
        _("Numero Documento"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Numero o riferimento del documento")
    )
    
    issue_date = models.DateField(
        _("Data Emissione"),
        null=True,
        blank=True,
        help_text=_("Data di emissione del documento")
    )
    
    expiry_date = models.DateField(
        _("Data Scadenza"),
        null=True,
        blank=True,
        help_text=_("Data di scadenza del documento")
    )
    
    # Status
    status = models.CharField(
        _("Stato"),
        max_length=20,
        choices=[
            ('PENDING', _('In attesa')),
            ('SUBMITTED', _('Inviato')),
            ('UNDER_REVIEW', _('In revisione')),
            ('APPROVED', _('Approvato')),
            ('REJECTED', _('Respinto')),
            ('EXPIRED', _('Scaduto')),
        ],
        default='PENDING',
        help_text=_("Stato del documento")
    )
    
    # Verification
    verified = models.BooleanField(
        _("Verificato"),
        default=False,
        help_text=_("Documento verificato dall'azienda")
    )
    
    verified_by = models.CharField(
        _("Verificato da"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Persona che ha verificato il documento")
    )
    
    verified_date = models.DateField(
        _("Data Verifica"),
        null=True,
        blank=True,
        help_text=_("Data di verifica")
    )
    
    # File storage
    document_file = models.FileField(
        _("File Documento"),
        upload_to='vendor_documents/%Y/%m/',
        blank=True,
        null=True,
        help_text=_("File del documento caricato")
    )
    
    # Additional info
    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True,
        help_text=_("Note aggiuntive sul documento")
    )
    
    rejection_reason = models.TextField(
        _("Motivo Rifiuto"),
        blank=True,
        null=True,
        help_text=_("Motivo del rifiuto (se applicabile)")
    )
    
    # Metadata
    created_at = models.DateTimeField(
        _("Creato il"),
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        _("Aggiornato il"),
        auto_now=True
    )
    
    # Upload tracking
    uploaded_by = models.CharField(
        _("Caricato da"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Utente che ha caricato il documento")
    )

    class Meta:
        verbose_name = _("Documento Fornitore")
        verbose_name_plural = _("Documenti Fornitori")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'document_type']),
            models.Index(fields=['status']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['verified']),
        ]

    def __str__(self):
        return f"{self.vendor.name} - {self.document_type.name}"
    
    @property
    def is_expired(self):
        """Verifica se il documento è scaduto"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
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
            return 'NO_EXPIRY'
        
        days = self.days_to_expiry
        if days < 0:
            return 'EXPIRED'
        elif days <= self.document_type.alert_days_before_expiry:
            return 'EXPIRING_SOON'
        return 'VALID'
    
    @property
    def is_valid(self):
        """Verifica se il documento è valido (approvato e non scaduto)"""
        return self.status == 'APPROVED' and not self.is_expired and self.verified
    
    def save(self, *args, **kwargs):
        """Override save per aggiornare automaticamente lo stato se scaduto"""
        if self.is_expired and self.status not in ['EXPIRED', 'REJECTED']:
            self.status = 'EXPIRED'
        super().save(*args, **kwargs)


# Model for Address
class Address(models.Model):
    """
    Modello per gestire gli indirizzi in modo strutturato
    """
    # Primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Address fields
    street_address = models.CharField(
        _("Indirizzo Strada"),
        max_length=255,
        help_text=_("Via, numero civico")
    )
    
    street_address_2 = models.CharField(
        _("Indirizzo Strada 2"),
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Appartamento, scala, interno (opzionale)")
    )
    
    city = models.CharField(
        _("Città"),
        max_length=100,
        help_text=_("Città")
    )
    
    state_province = models.CharField(
        _("Stato/Provincia"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Provincia/Stato")
    )
    
    postal_code = models.CharField(
        _("Codice Postale"),
        max_length=20,
        help_text=_("Codice postale/CAP")
    )
    
    country = models.CharField(
        _("Paese"),
        max_length=100,
        default="Italia",
        help_text=_("Paese")
    )
    
    # Geographic coordinates (optional)
    latitude = models.DecimalField(
        _("Latitudine"),
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_("Latitudine (opzionale)")
    )
    
    longitude = models.DecimalField(
        _("Longitudine"),
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        help_text=_("Longitudine (opzionale)")
    )
    
    # Metadata fields
    created_at = models.DateTimeField(
        _("Creato il"),
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        _("Aggiornato il"),
        auto_now=True
    )
    
    # Additional info
    address_type = models.CharField(
        _("Tipo Indirizzo"),
        max_length=50,
        choices=[
            ('LEGAL', _('Sede legale')),
            ('OPERATIONAL', _('Sede operativa')),
            ('BILLING', _('Indirizzo fatturazione')),
            ('SHIPPING', _('Indirizzo spedizione')),
            ('OTHER', _('Altro')),
        ],
        default='LEGAL',
        help_text=_("Tipo di indirizzo")
    )
    
    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Indirizzo attivo")
    )
    
    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True,
        help_text=_("Note aggiuntive sull'indirizzo")
    )

    class Meta:
        verbose_name = _("Indirizzo")
        verbose_name_plural = _("Indirizzi")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['city', 'country']),
            models.Index(fields=['postal_code']),
        ]

    def __str__(self):
        """Rappresentazione string dell'indirizzo"""
        address_parts = [self.street_address]
        
        if self.street_address_2:
            address_parts.append(self.street_address_2)
            
        address_parts.extend([
            f"{self.postal_code} {self.city}",
            self.country
        ])
        
        return ", ".join(address_parts)
    
    @property
    def full_address(self):
        """Ritorna l'indirizzo completo formattato"""
        return str(self)
    
    @property
    def short_address(self):
        """Ritorna una versione abbreviata dell'indirizzo"""
        return f"{self.street_address}, {self.city}"


# Modifica al Model Vendor esistente
class Vendor(models.Model):
    # Qualification Status Choices
    QUALIFICATION_STATUS_CHOICES = [
        ('PENDING', _('In attesa')),
        ('APPROVED', _('Approvato')),
        ('REJECTED', _('Respinto')),
    ]
    
    # Risk Level Choices
    RISK_LEVEL_CHOICES = [
        ('LOW', _('Basso')),
        ('MEDIUM', _('Medio')),
        ('HIGH', _('Alto')),
    ]
    # Foreign Key to Address model
    address = models.ForeignKey(
        Address,
        verbose_name=_("Indirizzo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors",
        help_text=_("Indirizzo del fornitore")
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
                message=_("Il codice fornitore deve essere alfanumerico maiuscolo"),
            )
        ],
    )
    name = models.CharField(
        _("Nome del Fornitore"), max_length=255, help_text=_("Nome del fornitore"), blank=True
    )
    contact_details = models.TextField(
        _("Dettagli di Contatto del Fornitore"), help_text=_("Dettagli di contatto del fornitore"), blank=True
    )
    #address = models.TextField(_("Address of Vendor"), help_text=_("Indirizzo del fornitore"), blank=True)
    
    # New General Information Fields
    vat_number = models.CharField(
        _("Partita IVA"),
        max_length=20,
        help_text=_("Partita IVA"),
        blank=True, null=True
    )
    fiscal_code = models.CharField(
        _("Codice Fiscale"),
        max_length=16,
        help_text=_("Codice fiscale"),
        blank=True, null=True
    )
    email = models.EmailField(
        _("Email"),
        help_text=_("Email principale"),
        blank=True, null=True
    )
    reference_contact = models.CharField(
        _("Contatto di Riferimento"),
        max_length=100,
        help_text=_("Riferimento principale"),
        blank=True, null=True
    )
    phone = models.CharField(
        _("Telefono"),
        max_length=20,
        help_text=_("Telefono di riferimento"),
        blank=True, null=True
    )
    website = models.URLField(
        _("Sito Web"),
        blank=True, null=True,
        help_text=_("Sito web aziendale")
    )
    
    # Performance Fields (existing)
    on_time_delivery_rate = models.FloatField(
        _("Tasso di Consegna Puntuale"),
        help_text=_("Rating di Consegna Puntuale del Fornitore"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        null=True, blank=True,
    )
    quality_rating_avg = models.FloatField(
        _("Valutazione Media Qualità"),
        help_text=_("Rating Medio di Qualità del Fornitore"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(5)],
        null=True, blank=True,
    )
    average_response_time = models.FloatField(
        _("Tempo di Risposta Medio"),
        help_text=_("Tempo di Risposta Medio del Fornitore in Ore"),
        validators=[validators.MinValueValidator(0)],
        null=True,  blank=True,
    )
    fulfillment_rate = models.FloatField(
        _("Tasso di Adempimento"),
        help_text=_("Rating di Adempimento del Fornitore"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        null=True, blank=True,
    )
    
    # Qualification/Compliance Fields
    qualification_status = models.CharField(
        _("Stato di Qualifica"),
        max_length=20,
        choices=QUALIFICATION_STATUS_CHOICES,
        default='PENDING',
        help_text=_("Stato della qualifica del fornitore"),
        blank=True, null=True
    )
    qualification_score = models.FloatField(
        _("Punteggio di Qualifica"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        null=True, blank=True,
        help_text=_("Punteggio medio di qualifica (0-100)")
    )
    qualification_date = models.DateField(
        _("Data di Qualifica"),
        null=True, blank=True,
        help_text=_("Data di qualifica o revisione")
    )
    qualification_expiry = models.DateField(
        _("Scadenza Qualifica"),
        null=True, blank=True,
        help_text=_("Scadenza della qualifica (es. ogni 12 mesi)")
    )
    
    category = models.ForeignKey(
        Category,
        verbose_name=_("Categoria"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors",
        help_text=_("Categoria merceologica del fornitore")
    )
    
    # Competences relationship
    competences = models.ManyToManyField(
        Competence,
        verbose_name=_("Competenze"),
        through='VendorCompetence',
        blank=True,
        related_name="vendors_with_competence",
        help_text=_("Competenze possedute dal fornitore")
    )

    risk_level = models.CharField(
        _("Livello di Rischio"),
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='MEDIUM',
        help_text=_("Valutazione del rischio fornitore"),
        blank=True, null=True
    )
    country = models.CharField(
        _("Paese"),
        max_length=100,
        help_text=_("Paese sede legale"),
        blank=True, null=True,
        default="Italia"
    )
    iso_certifications = models.TextField(
        _("Certificazioni ISO"),
        blank=True, null=True,
        help_text=_("Elenco delle certificazioni ISO possedute")
    )
    
    # Audit and Management Fields
    last_audit_date = models.DateField(
        _("Data Ultimo Audit"),
        null=True, blank=True,
        help_text=_("Ultimo audit condotto")
    )
    next_audit_due = models.DateField(
        _("Prossimo Audit Previsto"),
        null=True, blank=True,
        help_text=_("Prossima data audit prevista")
    )
    review_notes = models.TextField(
        _("Note di Revisione"),
        blank=True, null=True,
        help_text=_("Note di revisione e valutazione")
    )
    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Fornitore attivo")
    )

    # Metadata
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

        # Save the model
        super(Vendor, self).save(*args, **kwargs)
    
    # Properties for better data visualization
    @property
    def is_qualified(self):
        """Returns True if vendor is approved and qualification is not expired"""
        if self.qualification_status != 'APPROVED':
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
    def active_competences(self):
        """Ritorna le competenze attive del fornitore"""
        return self.vendor_competences.filter(
            has_competence=True,
            competence__is_active=True
        )
    
    @property
    def expired_competences(self):
        """Ritorna le competenze scadute"""
        return self.vendor_competences.filter(
            has_competence=True,
            expiry_date__lt=timezone.now().date()
        )
    
    @property
    def expiring_competences(self):
        """Ritorna le competenze in scadenza nei prossimi 90 giorni"""
        from datetime import timedelta
        expiry_threshold = timezone.now().date() + timedelta(days=90)
        return self.vendor_competences.filter(
            has_competence=True,
            expiry_date__lte=expiry_threshold,
            expiry_date__gte=timezone.now().date()
        )
    
    @property
    def missing_mandatory_competences(self):
        """Ritorna le competenze obbligatorie mancanti per la categoria del fornitore"""
        if not self.category:
            return Competence.objects.none()
        
        # Competenze obbligatorie per la categoria
        required = self.category.required_competences.filter(is_mandatory=True, is_active=True)
        
        # Competenze già possedute
        possessed_ids = self.vendor_competences.filter(
            has_competence=True
        ).values_list('competence_id', flat=True)
        
        # Ritorna quelle mancanti
        return required.exclude(id__in=possessed_ids)
    
    @property
    def valid_documents(self):
        """Ritorna i documenti validi del fornitore"""
        return self.vendor_documents.filter(
            status='APPROVED',
            verified=True
        ).exclude(
            expiry_date__lt=timezone.now().date()
        )
    
    @property
    def expired_documents(self):
        """Ritorna i documenti scaduti"""
        return self.vendor_documents.filter(
            expiry_date__lt=timezone.now().date()
        )
    
    @property
    def expiring_documents(self):
        """Ritorna i documenti in scadenza (entro i giorni di preavviso)"""
        from datetime import timedelta
        documents_expiring = []
        for doc in self.vendor_documents.filter(
            status='APPROVED',
            expiry_date__isnull=False
        ):
            if doc.expiry_date >= timezone.now().date():
                days_to_expiry = (doc.expiry_date - timezone.now().date()).days
                if days_to_expiry <= doc.document_type.alert_days_before_expiry:
                    documents_expiring.append(doc)
        return documents_expiring
    
    @property
    def missing_mandatory_documents(self):
        """Ritorna i documenti obbligatori mancanti per la categoria del fornitore"""
        if not self.category:
            return DocumentType.objects.none()
        
        # Documenti obbligatori per la categoria
        required = self.category.required_documents.filter(is_mandatory=True, is_active=True)
        
        # Documenti già caricati e validi
        submitted_ids = self.vendor_documents.filter(
            status__in=['APPROVED', 'SUBMITTED', 'UNDER_REVIEW']
        ).values_list('document_type_id', flat=True)
        
        # Ritorna quelli mancanti
        return required.exclude(id__in=submitted_ids)
    
    @property
    def is_documentation_complete(self):
        """Verifica se tutta la documentazione obbligatoria è presente e valida"""
        missing = self.missing_mandatory_documents
        expired = self.expired_documents.filter(document_type__is_mandatory=True)
        return not missing.exists() and not expired.exists()