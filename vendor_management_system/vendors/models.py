# Imports
import uuid

from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings

# Import DocumentType and Document from documents app
from vendor_management_system.documents.models import DocumentType, Document


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
        help_text=_("Codice ISO 3166-1 alpha-2 (es. 'IT', 'DE', 'FR')")
    )
    name = models.CharField(
        _("Nome Nazione"),
        max_length=100,
        help_text=_("Nome della nazione")
    )
    is_active = models.BooleanField(_("È Attiva"), default=True)
    sort_order = models.PositiveIntegerField(_("Ordine"), default=100)

    class Meta:
        verbose_name = _("Nazione")
        verbose_name_plural = _("Nazioni")
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Region(models.Model):
    """Tabella delle Regioni"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        _("Codice Regione"),
        max_length=10,
        unique=True,
        help_text=_("Codice univoco della regione (es. 'LOM', 'VEN')")
    )
    name = models.CharField(
        _("Nome Regione"),
        max_length=100,
        help_text=_("Nome della regione")
    )
    country = models.ForeignKey(
        Country,
        verbose_name=_("Nazione"),
        on_delete=models.CASCADE,
        related_name="regions",
        help_text=_("Nazione di appartenenza")
    )
    is_active = models.BooleanField(_("È Attiva"), default=True)
    sort_order = models.PositiveIntegerField(_("Ordine"), default=100)

    class Meta:
        verbose_name = _("Regione")
        verbose_name_plural = _("Regioni")
        ordering = ['country__name', 'sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.country.code})"


class Province(models.Model):
    """Tabella delle Province"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        _("Sigla Provincia"),
        max_length=10,
        unique=True,
        help_text=_("Sigla della provincia (es. 'MI', 'RM', 'RA')")
    )
    name = models.CharField(
        _("Nome Provincia"),
        max_length=100,
        help_text=_("Nome della provincia")
    )
    region = models.ForeignKey(
        Region,
        verbose_name=_("Regione"),
        on_delete=models.CASCADE,
        related_name="provinces",
        help_text=_("Regione di appartenenza")
    )
    is_active = models.BooleanField(_("È Attiva"), default=True)
    sort_order = models.PositiveIntegerField(_("Ordine"), default=100)

    class Meta:
        verbose_name = _("Provincia")
        verbose_name_plural = _("Province")
        ordering = ['region__name', 'sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"


# ============================================================================
# Modello Zona di Competenza
# ============================================================================

class CompetenceZone(models.Model):
    """
    Zona di competenza geografica, definita tramite regole di inclusione/esclusione
    a livello di Nazione, Regione o Provincia.

    Esempi:
    - "Tutta l'Italia" → 1 regola: INCLUDE Nazione=Italia
    - "Italia escluse isole" → INCLUDE Italia + EXCLUDE Sicilia + EXCLUDE Sardegna
    - "Lombardia e Veneto" → INCLUDE Lombardia + INCLUDE Veneto
    - "Lombardia e Ravenna" → INCLUDE Lombardia + INCLUDE Provincia Ravenna
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        _("Nome Zona"),
        max_length=255,
        unique=True,
        help_text=_("Nome descrittivo della zona (es. 'Tutta l'Italia', 'Nord Italia')")
    )
    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata della zona di competenza")
    )
    is_active = models.BooleanField(_("È Attiva"), default=True)
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    class Meta:
        verbose_name = _("Zona di Competenza")
        verbose_name_plural = _("Zone di Competenza")
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def rules_summary(self):
        """Ritorna un riepilogo testuale delle regole"""
        parts = []
        for rule in self.rules.all().order_by('rule_type'):
            prefix = "+" if rule.rule_type == 'INCLUDE' else "-"
            parts.append(f"{prefix} {rule.geographic_target}")
        return "; ".join(parts) if parts else _("Nessuna regola definita")


class CompetenceZoneRule(models.Model):
    """
    Singola regola di inclusione/esclusione per una zona di competenza.
    Esattamente uno tra country, region e province deve essere valorizzato.
    """
    RULE_TYPE_CHOICES = [
        ('INCLUDE', _('Includi')),
        ('EXCLUDE', _('Escludi')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(
        CompetenceZone,
        verbose_name=_("Zona di Competenza"),
        on_delete=models.CASCADE,
        related_name="rules"
    )
    rule_type = models.CharField(
        _("Tipo Regola"),
        max_length=10,
        choices=RULE_TYPE_CHOICES,
        default='INCLUDE',
        help_text=_("Includi o escludi questa area geografica")
    )
    country = models.ForeignKey(
        Country,
        verbose_name=_("Nazione"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="zone_rules",
        help_text=_("Seleziona per regola a livello nazionale")
    )
    region = models.ForeignKey(
        Region,
        verbose_name=_("Regione"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="zone_rules",
        help_text=_("Seleziona per regola a livello regionale")
    )
    province = models.ForeignKey(
        Province,
        verbose_name=_("Provincia"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="zone_rules",
        help_text=_("Seleziona per regola a livello provinciale")
    )

    class Meta:
        verbose_name = _("Regola Zona di Competenza")
        verbose_name_plural = _("Regole Zone di Competenza")
        ordering = ['rule_type', 'id']

    def __str__(self):
        return f"{self.get_rule_type_display()} {self.geographic_target}"

    @property
    def geographic_target(self):
        """Ritorna la descrizione dell'area geografica di questa regola"""
        if self.province:
            return f"Provincia: {self.province.name}"
        elif self.region:
            return f"Regione: {self.region.name}"
        elif self.country:
            return f"Nazione: {self.country.name}"
        return _("Non definito")

    @property
    def level(self):
        """Ritorna il livello geografico della regola"""
        if self.province:
            return 'PROVINCE'
        elif self.region:
            return 'REGION'
        elif self.country:
            return 'COUNTRY'
        return None

    def clean(self):
        """Valida che esattamente uno dei 3 livelli sia valorizzato"""
        from django.core.exceptions import ValidationError
        filled = sum([
            self.country_id is not None,
            self.region_id is not None,
            self.province_id is not None,
        ])
        if filled == 0:
            raise ValidationError(
                _("Selezionare almeno una tra Nazione, Regione o Provincia.")
            )
        if filled > 1:
            raise ValidationError(
                _("Selezionare solo una tra Nazione, Regione o Provincia per ogni regola.")
            )


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
        _("Codice Requisito"),
        max_length=50,
        unique=True,
        help_text=_("Codice univoco del requisito professionale (es. 'RSPP', 'ASPP')")
    )
    
    name = models.CharField(
        _("Nome Requisito Professionale"),
        max_length=255,
        help_text=_("Nome del requisito professionale")
    )
    
    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata del requisito professionale")
    )
    
    # Categorization
    competence_category = models.CharField(
        _("Categoria Requisito Professionale"),
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
        help_text=_("Categoria del requisito professionale")
    )
    
    # Requirements
    requires_certification = models.BooleanField(
        _("Richiede Certificazione"),
        default=True,
        help_text=_("Indica se il requisito professionale richiede una certificazione formale")
    )
    
    requires_renewal = models.BooleanField(
        _("Richiede Rinnovo"),
        default=False,
        help_text=_("Indica se il requisito professionale ha una scadenza e necessita rinnovo")
    )
    
    renewal_period_months = models.PositiveIntegerField(
        _("Periodo Rinnovo (mesi)"),
        null=True,
        blank=True,
        help_text=_("Numero di mesi prima della scadenza (es. 12, 24, 36)")
    )
    
    # Business rules
    is_mandatory = models.BooleanField(
        _("È Obbligatorio"),
        default=False,
        help_text=_("Requisito professionale obbligatorio per alcune categorie di fornitori")
    )
    
    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Requisito professionale attivo e utilizzabile")
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
        verbose_name = _("Requisito Professionale")
        verbose_name_plural = _("Catalogo Requisiti Professionali")
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
        verbose_name=_("Requisito Professionale"),
        on_delete=models.CASCADE,
        related_name="vendor_assignments"
    )
    
    # Tipo Requisito
    is_competenza = models.BooleanField(
        _("Competenza"),
        default=False,
        help_text=_("Indica se il requisito è assegnato come competenza")
    )

    is_qualifica = models.BooleanField(
        _("Qualifica"),
        default=False,
        help_text=_("Indica se il requisito è assegnato come qualifica")
    )

    is_iscrizione_albo = models.BooleanField(
        _("Iscrizione Albo"),
        default=False,
        help_text=_("Indica se il requisito è un'iscrizione all'albo")
    )

    # Status
    has_competence = models.BooleanField(
        _("Possiede Requisito Professionale"),
        default=True,
        help_text=_("Il fornitore possiede questo requisito professionale")
    )

    has_certification = models.BooleanField(
        _("Possiede Certificazione"),
        default=False,
        help_text=_("Il fornitore possiede questa certificazione")
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
        verbose_name = _("Requisito Professionale Assegnato")
        verbose_name_plural = _("Requisiti Professionali Assegnati")
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
    region = models.CharField(
        _("Regione"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Regione")
    )
    
    postal_code = models.CharField(
        _("Codice Postale"),
        max_length=20,
        blank=True,
        null=True,
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

class QualificationType(models.Model):
    """
    Tabella dei titoli di studio o tipi di qualifica
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    code = models.CharField(
        _("Codice Titolo"),
        max_length=50,
        unique=True,
        help_text=_("Codice univoco del titolo di studio o qualifica (es. 'DIP', 'LAU', 'MAS')")
    )

    name = models.CharField(
        _("Nome Titolo"),
        max_length=255,
        help_text=_("Nome completo del titolo di studio (es. 'Diploma tecnico', 'Laurea triennale')")
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione aggiuntiva del titolo di studio")
    )

    level = models.CharField(
        _("Livello EQF"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Livello di qualifica secondo il Quadro Europeo delle Qualifiche (EQF)")
    )

    # nuovo: struttura gerarchica padre-figlio
    parent = models.ForeignKey(
        'self',
        verbose_name=_("Titolo/Qualifica Padre"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sub_qualifications",
        help_text=_("Titolo/Qualifica padre (es. 'Laurea' per 'Laurea triennale', 'Laurea magistrale', ecc.)")
    )

    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Titolo/Qualifica attivo e selezionabile")
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"),
        default=100
    )

    class Meta:
        verbose_name = _("Titolo")
        verbose_name_plural = _("Titoli")
        ordering = ['sort_order', 'name']

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
        help_text=_("Codice univoco del servizio o tipologia (es. 'CONSULENZA', 'CONS_SIC')")
    )

    name = models.CharField(
        _("Nome Servizio"),
        max_length=255,
        help_text=_("Nome della tipologia o del servizio specifico")
    )

    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata del servizio")
    )

    parent = models.ForeignKey(
        'self',
        verbose_name=_("Tipologia Padre"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="subservices",
        help_text=_("Tipologia padre (lascia vuoto se è una categoria principale)")
    )

    is_active = models.BooleanField(
        _("È Attivo"),
        default=True,
        help_text=_("Indica se il servizio è attivo")
    )

    sort_order = models.PositiveIntegerField(
        _("Ordine di Ordinamento"),
        default=100
    )

    class Meta:
        verbose_name = _("Tipo/Servizio")
        verbose_name_plural = _("Tipologie e Servizi")
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
        related_name="vendor_services"
    )
    
    service_type = models.ForeignKey(
        ServiceType,
        verbose_name=_("Servizio"),
        on_delete=models.CASCADE,
        related_name="vendor_assignments"
    )
    
    # Additional info
    hourly_rate = models.DecimalField(
        _("Prezzo Orario"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Prezzo orario del servizio per questo fornitore")
    )
    
    is_primary = models.BooleanField(
        _("Servizio Principale"),
        default=False,
        help_text=_("Indica se questo è il servizio principale del fornitore")
    )
    
    start_date = models.DateField(
        _("Data Inizio Erogazione"),
        null=True,
        blank=True,
        help_text=_("Data di inizio erogazione del servizio")
    )
    
    end_date = models.DateField(
        _("Data Fine Erogazione"),
        null=True,
        blank=True,
        help_text=_("Data di fine erogazione del servizio (se applicabile)")
    )
    
    contract = models.ForeignKey(
        'Contract',
        verbose_name=_("Contratto"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_services",
        help_text=_("Contratto associato a questo servizio")
    )

    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True,
        help_text=_("Note aggiuntive sul servizio erogato")
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
        verbose_name = _("Servizio Fornitore")
        verbose_name_plural = _("Servizi Fornitori")
        unique_together = [['vendor', 'service_type']]
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['vendor', 'service_type']),
            models.Index(fields=['is_primary']),
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


class Contract(models.Model):
    """
    Contratto associato a un fornitore, con collegamento ai servizi erogati.
    Un fornitore può avere più contratti.
    """
    CONTRACT_STATUS_CHOICES = [
        ('DRAFT', _('Bozza')),
        ('ACTIVE', _('Attivo')),
        ('EXPIRED', _('Scaduto')),
        ('TERMINATED', _('Risolto')),
        ('SUSPENDED', _('Sospeso')),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    vendor = models.ForeignKey(
        'Vendor',
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="contracts"
    )
    contract_number = models.CharField(
        _("Numero Contratto"),
        max_length=50,
        unique=True,
        help_text=_("Codice identificativo del contratto")
    )
    title = models.CharField(
        _("Titolo"),
        max_length=255,
        help_text=_("Descrizione breve del contratto")
    )
    status = models.CharField(
        _("Stato"),
        max_length=20,
        choices=CONTRACT_STATUS_CHOICES,
        default='DRAFT'
    )
    start_date = models.DateField(
        _("Data Inizio"),
        help_text=_("Data di decorrenza del contratto")
    )
    end_date = models.DateField(
        _("Data Fine"),
        null=True,
        blank=True,
        help_text=_("Data di scadenza del contratto")
    )
    amount = models.DecimalField(
        _("Importo"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Importo totale del contratto")
    )
    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Aggiornato il"), auto_now=True)

    class Meta:
        verbose_name = _("Contratto")
        verbose_name_plural = _("Contratti")
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['contract_number']),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.title}"

    @property
    def is_active(self):
        if self.status != 'ACTIVE':
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
        help_text=_("Nome della frequenza (es. Mensile, Trimestrale)")
    )
    months = models.PositiveIntegerField(
        _("Mesi"),
        unique=True,
        help_text=_("Numero di mesi tra una valutazione e la successiva")
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
        ('COMM', 'Valutazione Commerciale'),
        ('CONS', 'Valutazione del Servizio (Consulting)'),
        ('FCB', 'Valutazione del Servizio (FCB)'),
        ('MED', 'Valutazione del Servizio (MED)'),
        ('PROD_NONTEC', 'Valutazione Prodotto non tecnologico'),
        ('PROD_TEC', 'Valutazione Prodotto tecnologico'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(
        _("Categoria di Valutazione"),
        max_length=20,
        choices=EVALUATION_CATEGORY_CHOICES
    )
    code = models.CharField(
        _("Codice Criterio"),
        max_length=50,
        unique=True,
        help_text=_("Codice univoco del criterio (es. COMM_01, FCB_03, PROD_TEC_02)")
    )
    name = models.CharField(
        _("Nome del Criterio"),
        max_length=255,
        help_text=_("Nome del criterio di valutazione (es. 'Efficienza del servizio')")
    )
    description = models.TextField(
        _("Descrizione"),
        blank=True,
        null=True,
        help_text=_("Descrizione dettagliata del criterio")
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
    VENDOR_TYPE_CHOICES = [
        ('Società', _('Società')),
        ('Professionista', _('Professionista')),
        ('Dipendente', _('Dipendente')),
        ('Dipendente + Libero professionista', _('Dipendente + Libero professionista')),
        ('Disoccupato', _('Disoccupato')),
        ('Libero Professionista', _('Libero Professionista')),
        ('Presso Studio', _('Presso Studio')),
        ('Prestazione Occasionale', _('Prestazione Occasionale')),
        ('Società/professionista', _('Società/professionista')),
        ('Internazionale', _('Internazionale')),
    ]

    SERVICE_TYPE_CHOICES = [
        ('ALTRO', 'Altro'),
        ('ANALISI_LABORATORIO', 'Analisi di laboratorio'),
        ('COMMERCIALE', 'Commerciale'),
        ('CONSULENZA', 'Consulenza'),
        ('FORNITURA', 'Fornitura'),
        ('INDAGINI_STRUMENTALI', 'Indagini strumentali'),
    ]

    CLUSTER_CORSO_CHOICES = [
        ('01', 'GenSpDirPre'),
        ('02', 'GenSpDirPre; Antincendio; Attrezzature'),
        ('03', 'GenSpDirPre; Segnaletica Stradale'),
        ('04', 'Antincendio'),
        ('05', 'Primo Soccorso'),
        ('06', 'Primo Soccorso BLSD'),
        ('08', 'Attrezzature'),
        ('09', 'Elearning'),
        ('11', 'Manageriale'),
        ('12', 'Attestati'),
        ('19', 'Tutti'),
        ('20', 'Ambientale'),
    ]

    CONTRACTUAL_STATUS_CHOICES = [
        ('00', 'Da verificare'),
        ('02', 'Fare RAI'),
        ('03', 'RAI Effettuata'),
        ('04', 'Contrattualizzato'),
        ('05', 'Da contrattualizzare ad esigenza'),
        ('06', 'Contratto Scaduto'),
        ('99', 'Non Usare'),
    ]

    VENDOR_FINAL_EVALUATION_CHOICES = [
        ('DA VALUTARE', _('Da Valutare')),
        ('NEGATIVO', _('Negativo')),
        ('POSITIVO', _('Positivo')),
        ('MOLTO POSITIVO', _('Molto Positivo')),
    ]

    VENDOR_MEDICAL_SERVICE_CHOICES = [
        ('ALTRI_PROF', 'Altri Professionisti'),
        ('ALTRO', 'ALTRO'),
        ('AMBULANZE', 'Ambulanze'),
        ('CENTRO_MEDICO', 'Centro medico/Poliambulatorio'),
        ('DOCENTE', 'Docente'),
        ('FORN_SANITARIE', 'Forniture sanitarie/Elettromedicali'),
        ('INFERMIERE', 'Infermiere'),
        ('LABORATORIO', 'Laboratorio'),
        ('MEDICINA_LAVORO', 'Medicina del Lavoro'),
        ('MEDICO_COMPETENTE', 'Medico Competente'),
        ('MEDICO_GENERICO', 'Medico Generico'),
        ('MEDICO_SPECIALISTA', 'Medico Specialista'),
        ('RIFIUTI', 'Rifiuti'),
        ('SOCIETA_SANITARIA', 'Società Infermieri-Medici-Assistenti sociali'),
    ]

    old_code = models.CharField(
        _("Vecchio Codice Fornitore"),
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        help_text=_("Vecchio codice univoco del fornitore, se applicabile")
    )

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
        max_length=100,
        help_text=_("Telefono di riferimento"),
        blank=True, null=True
    )
    website = models.URLField(
        _("Sito Web"),
        blank=True, null=True,
        help_text=_("Sito web aziendale")
    )
    vendor_type = models.CharField(
        _("Tipo di Fornitore"),
        max_length=50,
        choices=VENDOR_TYPE_CHOICES,
        default='Società',
        help_text=_("Tipo di fornitore"),
        blank=True, null=True
    )
    user_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Utente di aggiornamento"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vendors",
        help_text=_("Utente di aggiornamento associato al fornitore")
    )
    qualification_type = models.ForeignKey(
        QualificationType,
        verbose_name=_("Titolo di Studio / Tipo di Qualifica"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="vendors",
        help_text=_("Titolo di studio o qualifica del fornitore")
    )

    # NUOVO: relazione many-to-many con ServiceType
    services = models.ManyToManyField(
        ServiceType,
        verbose_name=_("Servizi Erogati"),
        through='VendorService',
        blank=True,
        related_name="vendors_providing_service",
        help_text=_("Servizi erogati dal fornitore")
    )

    cluster_corso = models.CharField(
        _("Cluster Corso"),
        max_length=50,
        choices=CLUSTER_CORSO_CHOICES,
        blank=True, null=True,
        help_text=_("Raggruppamento di corso per tipologia di servizio")
    )

    vendor_task_description = models.TextField(
        _("Descrizione Attività Fornitore"),
        blank=True, null=True,
        help_text=_("Descrizione delle attività svolte dal fornitore")
    )
    mobile_device = models.BooleanField(
        _("Dispositivo Mobile"),
        default=False,
        help_text=_("Indica se il fornitore utilizza dispositivi mobili per le operazioni")
    )
    ambulatory_service = models.TextField(
        _("Servizio Ambulatoriale"),
        blank=True, null=True,
        help_text=_("Descrizione dei servizi ambulatoriali offerti dal fornitore")
    )
    laboratory_service = models.BooleanField(
        _("Servizio di Laboratorio"),
        default=False,
        help_text=_("Indica se il fornitore offre servizi di laboratorio")
    )
    laboratory_independent = models.BooleanField(
        _("Laboratorio Indipendente"),
        default=False,
        null=True,
        help_text=_("Indica se il laboratorio è indipendente")
    )
    licensed_physician_year = models.IntegerField(
        _("Medico autorizzato dall'anno"),
        null=True, blank=True,
        help_text=_("Medico autorizzato dall'anno")
    )
    vendor_medical_service = models.CharField(
        _("Servizio Sanitario/Professionale"),
        max_length=50,
        choices=VENDOR_MEDICAL_SERVICE_CHOICES,
        default='ALTRO',
        blank=True,
        null=True,
        help_text=_("Tipologia di servizio medico o sanitario fornito")
    )
    date_of_establishment = models.DateField(
        _("Data di Specializzazione/Fondazione"),
        null=True, blank=True,
        help_text=_("Data di Specializzazione o Fondazione")
    )
    other_medical_service = models.TextField(
        _("Altri Servizi Medici"),
        blank=True, null=True,
        help_text=_("Descrizione di altri servizi medici offerti dal fornitore")
    )
    doctor_registration = models.TextField(
        _("Titolo Iscrizione Albo Medici"),
        blank=True, null=True,
        help_text=_("Descrizione del titolo di iscrizione all'albo dei medici")
    )
    doctor_cv = models.BooleanField(
        _("CV del Medico Disponibile"),
        default=False,
        help_text=_("Indica se il curriculum vitae del medico è disponibile")
    )
    doctor_cv2 = models.BooleanField(
        _("CV2 del Medico Disponibile"),
        default=False,
        help_text=_("Indica se il secondo curriculum vitae del medico è disponibile")
    )

    # Contractual Fields
    contractual_status = models.CharField(
        _("Stato Contrattuale"),
        max_length=2,
        choices=CONTRACTUAL_STATUS_CHOICES,
        default='00',
        help_text=_("Indica lo stato contrattuale del fornitore")
    )
    contractual_start_date = models.DateField(
        _("Data Inizio Contratto"),
        null=True, blank=True,
        help_text=_("Data di inizio del contratto con il fornitore")
    )
    contractual_end_date = models.DateField(
        _("Data Fine Contratto"),
        null=True, blank=True,
        help_text=_("Data di fine del contratto con il fornitore")
    )
    contractual_terms = models.TextField(
        _("Termini Contrattuali"),
        blank=True, null=True,
        help_text=_("Termini e condizioni del contratto con il fornitore")
    )
    reference_person = models.CharField(
        _("Persona di Riferimento"),
        max_length=100,
        help_text=_("Persona di riferimento"),
        blank=True, null=True
    )
    vendor_management_update = models.CharField(
        _("Gestione aggiornamenti"),
        max_length=100,
        help_text=_("Gestione aggiornamenti del fornitore"),
        blank=True, null=True
    )
    embyon_blocked = models.BooleanField(
        _("Bloccato in Embyon"),
        default=False,
        help_text=_("Indica se il fornitore risulta bloccato in Embyon")
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
    vendor_final_evaluation = models.CharField(
        _("Valutazione Finale del Fornitore"),
        max_length=20,
        choices=VENDOR_FINAL_EVALUATION_CHOICES,
        default='DA VALUTARE',
        help_text=_("Valutazione finale complessiva del fornitore"),
        blank=True, null=True
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
    competences_zone = models.CharField(
        _("Zona Competenze"),
        max_length=255,
        blank=True, null=True,
        help_text=_("Zona geografica delle competenze del fornitore (campo legacy)")
    )
    # Nuova relazione strutturata con Zone di Competenza
    competence_zones = models.ManyToManyField(
        CompetenceZone,
        verbose_name=_("Zone di Competenza"),
        blank=True,
        related_name="vendors",
        help_text=_("Zone di competenza geografica del fornitore")
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

    # Document relationship (nuovo)
    vendor_documents = models.ManyToManyField(
        Document,
        verbose_name=_("Documenti"),
        blank=True,
        related_name="vendors",
        help_text=_("Documenti associati al fornitore")
    )

    risk_level = models.CharField(
        _("Livello di Affidabilità/Rischio"),
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='MEDIUM',
        help_text=_("Valutazione dell'affidabilità/rischio del fornitore"),
        blank=True, null=True
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
    is_ico_consultant = models.BooleanField(
        _("È Consulente ICO"),
        default=False,
        help_text=_("Indica se il fornitore è un consulente ICO")
    )
    albo_zucchetti = models.CharField(
        _("Inserito in Albo Zucchetti"),
        max_length=20,
        blank=True, null=True
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
    def primary_service(self):
        """Ritorna il servizio principale del fornitore"""
        primary = self.vendor_services.filter(is_primary=True).first()
        return primary.service_type if primary else None
    
    @property
    def active_services(self):
        """Ritorna i servizi attivi del fornitore"""
        return self.vendor_services.filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now().date())
        )
    
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
            status='APPROVED'
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
                if doc.document_type.reminder_days_before is not None and days_to_expiry <= doc.document_type.reminder_days_before:
                    documents_expiring.append(doc)
        return documents_expiring
    
    @property
    def missing_mandatory_documents(self):
        """Ritorna i documenti obbligatori mancanti per la categoria del fornitore"""
        if not self.category:
            return DocumentType.objects.none()
        
        required = DocumentType.objects.filter(is_required=True)
        
        submitted_ids = self.vendor_documents.filter(
            status__in=['APPROVED', 'UPLOADED']
        ).values_list('document_type_id', flat=True)
        
        return required.exclude(id__in=submitted_ids)
    
    @property
    def is_documentation_complete(self):
        """Verifica se tutta la documentazione obbligatoria è presente e valida"""
        missing = self.missing_mandatory_documents
        expired = self.expired_documents.filter(document_type__is_required=True)
        return not missing.exists() and not expired.exists()

    # Alias di compatibilità: mantiene self.documents.filter(...)
    @property
    def documents(self):
        return self.vendor_documents


class Evaluator(models.Model):
    """
    Valutatore che può essere associato alle valutazioni dei fornitori
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(
        _("Nome"),
        max_length=100
    )
    last_name = models.CharField(
        _("Cognome"),
        max_length=100
    )
    email = models.EmailField(
        _("Email"),
        unique=True,
        blank=True,
        null=True
    )
    role = models.CharField(
        _("Ruolo"),
        max_length=150,
        blank=True,
        null=True,
        help_text=_("Ruolo o qualifica del valutatore")
    )
    department = models.CharField(
        _("Dipartimento"),
        max_length=150,
        blank=True,
        null=True
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
        related_name="evaluations"
    )
    criterion = models.ForeignKey(
        EvaluationCriterion,
        verbose_name=_("Criterio di Valutazione"),
        on_delete=models.CASCADE,
        related_name="vendor_scores"
    )
    score = models.PositiveSmallIntegerField(
        _("Punteggio"),
        choices=EVALUATION_SCALE,
        help_text=_("Valutazione da 1 (Scarso) a 8 (Eccellente)")
    )
    evaluator = models.ForeignKey(
        Evaluator,
        verbose_name=_("Valutatore"),
        on_delete=models.SET_NULL,
        related_name="evaluations",
        blank=True,
        null=True
    )
    evaluation_frequency = models.ForeignKey(
        EvaluationFrequency,
        verbose_name=_("Frequenza di Valutazione"),
        on_delete=models.SET_NULL,
        related_name="evaluations",
        blank=True,
        null=True,
        default=None
    )

    def save(self, *args, **kwargs):
        if self.evaluation_frequency_id is None:
            try:
                self.evaluation_frequency = EvaluationFrequency.objects.get(months=12)
            except EvaluationFrequency.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    notes = models.TextField(
        _("Note"),
        blank=True,
        null=True
    )
    evaluated_at = models.DateField(_("Data Valutazione"), auto_now_add=True)

    class Meta:
        verbose_name = _("Valutazione")
        verbose_name_plural = _("Valutazioni")
        unique_together = ("vendor", "criterion")

    def __str__(self):
        return f"{self.vendor.name} - {self.criterion.name}: {self.get_score_display()}"
