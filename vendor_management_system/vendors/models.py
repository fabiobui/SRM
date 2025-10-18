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