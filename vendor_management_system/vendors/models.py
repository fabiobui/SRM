# Imports
import uuid

from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# Model for Vendor
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

    # Core Fields
    vendor_code = models.CharField(
        _("Vendor Code"),
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
        _("Name of Vendor"), max_length=255, help_text=_("Nome del fornitore"), blank=True
    )
    contact_details = models.TextField(
        _("Contact Details of Vendor"), help_text=_("Dettagli di contatto del fornitore"), blank=True
    )
    address = models.TextField(_("Address of Vendor"), help_text=_("Indirizzo del fornitore"), blank=True)
    
    # New General Information Fields
    vat_number = models.CharField(
        _("VAT Number"),
        max_length=20,
        help_text=_("Partita IVA"),
        blank=True, null=True
    )
    fiscal_code = models.CharField(
        _("Fiscal Code"),
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
        _("Reference Contact"),
        max_length=100,
        help_text=_("Riferimento principale"),
        blank=True, null=True
    )
    phone = models.CharField(
        _("Phone"),
        max_length=20,
        help_text=_("Telefono di riferimento"),
        blank=True, null=True
    )
    website = models.URLField(
        _("Website"),
        blank=True, null=True,
        help_text=_("Sito web aziendale")
    )
    
    # Performance Fields (existing)
    on_time_delivery_rate = models.FloatField(
        _("On-time Delivery Rate"),
        help_text=_("Rating di Consegna Puntuale del Fornitore"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        null=True, blank=True,
    )
    quality_rating_avg = models.FloatField(
        _("Quality Rating Average"),
        help_text=_("Rating Medio di Qualità del Fornitore"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(5)],
        null=True, blank=True,
    )
    average_response_time = models.FloatField(
        _("Average Response Time"),
        help_text=_("Tempo di Risposta Medio del Fornitore in Ore"),
        validators=[validators.MinValueValidator(0)],
        null=True,  blank=True,
    )
    fulfillment_rate = models.FloatField(
        _("Fulfillment Rate"),
        help_text=_("Rating di Adempimento del Fornitore"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        null=True, blank=True,
    )
    
    # Qualification/Compliance Fields
    qualification_status = models.CharField(
        _("Qualification Status"),
        max_length=20,
        choices=QUALIFICATION_STATUS_CHOICES,
        default='PENDING',
        help_text=_("Stato della qualifica del fornitore"),
        blank=True, null=True
    )
    qualification_score = models.FloatField(
        _("Qualification Score"),
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(100)],
        null=True, blank=True,
        help_text=_("Punteggio medio di qualifica (0-100)")
    )
    qualification_date = models.DateField(
        _("Qualification Date"),
        null=True, blank=True,
        help_text=_("Data di qualifica o revisione")
    )
    qualification_expiry = models.DateField(
        _("Qualification Expiry"),
        null=True, blank=True,
        help_text=_("Scadenza della qualifica (es. ogni 12 mesi)")
    )
    
    # Evaluation and Operational Capacity Fields
    category = models.CharField(
        _("Category"),
        max_length=100,
        help_text=_("Categoria merceologica (es. 'Servizi', 'Forniture', 'Manutenzione')"),
        blank=True, null=True
    )
    risk_level = models.CharField(
        _("Risk Level"),
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='MEDIUM',
        help_text=_("Valutazione del rischio fornitore"),
        blank=True, null=True
    )
    country = models.CharField(
        _("Country"),
        max_length=100,
        help_text=_("Paese sede legale"),
        blank=True, null=True,
        default="Italia"
    )
    iso_certifications = models.TextField(
        _("ISO Certifications"),
        blank=True, null=True,
        help_text=_("Elenco delle certificazioni ISO possedute")
    )
    
    # Audit and Management Fields
    last_audit_date = models.DateField(
        _("Last Audit Date"),
        null=True, blank=True,
        help_text=_("Ultimo audit condotto")
    )
    next_audit_due = models.DateField(
        _("Next Audit Due"),
        null=True, blank=True,
        help_text=_("Prossima data audit prevista")
    )
    review_notes = models.TextField(
        _("Review Notes"),
        blank=True, null=True,
        help_text=_("Note di revisione e valutazione")
    )

    # Metadata
    class Meta:
        verbose_name = _("Vendor")
        verbose_name_plural = _("Vendors")
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