import uuid
from django.core import validators
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class DocumentType(models.Model):
    """Tipi di documenti da richiedere ai fornitori"""
    
    id = models.CharField(
        _("Document Type ID"),
        max_length=10,
        unique=True,
        primary_key=True,
        editable=False,
        help_text=_("Unique ID for Document Type"),
    )
    name = models.CharField(
        _("Document Type Name"),
        max_length=100,
        help_text=_("Name of document type (e.g. DURC, ISO 9001, etc.)")
    )
    description = models.TextField(
        _("Description"),
        help_text=_("Description of this document type"),
        blank=True
    )
    is_required = models.BooleanField(
        _("Required"),
        default=True,
        help_text=_("Whether this document is required for vendor qualification")
    )
    validity_period_days = models.IntegerField(
        _("Validity Period (Days)"),
        help_text=_("How many days this document is valid for"),
        default=365
    )
    reminder_days_before = models.IntegerField(
        _("Reminder Days Before Expiry"),
        help_text=_("Send reminder X days before expiry"),
        default=30
    )
    
    class Meta:
        verbose_name = _("Document Type")
        verbose_name_plural = _("Document Types")
        ordering = ["name"]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = str(uuid.uuid4()).replace("-", "")[:10].upper()
        super().save(*args, **kwargs)

class Document(models.Model):
    """Documenti caricati dai fornitori"""
    
    STATUS_CHOICES = [
        ('PENDING', _('In attesa di caricamento')),
        ('UPLOADED', _('Caricato - da verificare')),
        ('APPROVED', _('Approvato')),
        ('REJECTED', _('Respinto')),
        ('EXPIRED', _('Scaduto')),
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
        related_name="documents"
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.CASCADE,
        verbose_name=_("Document Type"),
        help_text=_("Type of document")
    )
    file = models.FileField(
        _("Document File"),
        upload_to="vendor_documents/%Y/%m/",
        help_text=_("Upload the document file"),
        null=True,
        blank=True
    )
    issue_date = models.DateField(
        _("Issue Date"),
        help_text=_("Date when document was issued"),
        null=True,
        blank=True
    )
    expiry_date = models.DateField(
        _("Expiry Date"),
        help_text=_("Date when document expires"),
        null=True,
        blank=True
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text=_("Current status of document")
    )
    notes = models.TextField(
        _("Notes"),
        help_text=_("Additional notes about this document"),
        blank=True
    )
    uploaded_at = models.DateTimeField(
        _("Uploaded At"),
        auto_now_add=True,
        help_text=_("When document was uploaded")
    )
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        verbose_name=_("Reviewed By"),
        help_text=_("User who reviewed this document"),
        null=True,
        blank=True,
        related_name="reviewed_documents"
    )
    reviewed_at = models.DateTimeField(
        _("Reviewed At"),
        help_text=_("When document was reviewed"),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _("Document")
        verbose_name_plural = _("Documents")
        ordering = ["-uploaded_at"]
        unique_together = ["vendor", "document_type"]
    
    def __str__(self):
        return f"{self.vendor.name} - {self.document_type.name}"
    
    @property
    def is_expiring_soon(self):
        """Check if document expires within reminder period"""
        if not self.expiry_date:
            return False
        days_to_expiry = (self.expiry_date - timezone.now().date()).days
        return days_to_expiry <= self.document_type.reminder_days_before
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if not self.expiry_date:
            return False
        return self.expiry_date < timezone.now().date()
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.id = str(uuid.uuid4()).replace("-", "")[:10].upper()
        
        # Auto-update status based on expiry
        if self.is_expired and self.status != 'EXPIRED':
            self.status = 'EXPIRED'
        
        super().save(*args, **kwargs)