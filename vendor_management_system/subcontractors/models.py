"""Tecnici e mezzi/dotazioni dei fornitori Subappaltatori.

Ogni documento è una riga con la propria scadenza: il rinnovo di un attestato
crea un nuovo documento e i precedenti restano in archivio. Per promemoria e
visualizzazione conta il documento più recente validato per ciascun tipo.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

PENDING = "PENDING"
VALIDATED = "VALIDATED"
REJECTED = "REJECTED"
VALIDATION_CHOICES = [
    (PENDING, _("In attesa")),
    (VALIDATED, _("Validato")),
    (REJECTED, _("Respinto")),
]

# Tipo documento -> (etichetta, richiede scadenza), dall'Excel del ticket.
TECHNICIAN_DOC_TYPES = {
    "identita": ("Documento di identità", True),
    "patente": ("Patente", True),
    "lul": ("LUL", True),
    "unilav": ("UNILAV", True),
    "idoneita_sanitaria": ("Idoneità sanitaria", True),
    "consegna_dpi": ("Consegna DPI", True),
    "formazione_generale": ("Attestato formazione generale", False),
    "formazione_specifica": ("Attestato formazione specifica", True),
    "formazione_preposti": ("Attestato formazione preposti", True),
    "dpi_3_cat": ("DPI 3ª categoria", True),
    "pes_pav": ("PES/PAV", True),
    "spazi_confinati": ("Spazi confinati", True),
    "ple": ("PLE", True),
    "primo_soccorso": ("Primo soccorso", True),
    "antincendio": ("Antincendio", True),
    "altra_documentazione": ("Altra documentazione", False),
}

EQUIPMENT_DOC_TYPES = {
    "libretto": ("Libretto", False),
    "leasing": ("Contratto di leasing", True),
    "assicurazione": ("Assicurazione", True),
    "certificato_taratura": ("Certificato di taratura", True),
}

# Documenti "obbligatori" della colonna dell'Excel. Il contratto di leasing
# è obbligatorio solo per i mezzi in leasing: resta facoltativo.
TECHNICIAN_REQUIRED_DOCS = (
    "identita",
    "patente",
    "unilav",
    "idoneita_sanitaria",
    "formazione_generale",
    "formazione_specifica",
)
EQUIPMENT_REQUIRED_DOCS = ("libretto", "assicurazione", "certificato_taratura")


EXPIRY_REQUIRED_MSG = _("Questo tipo di documento richiede una scadenza.")


def _doc_type_choices(types):
    return [(key, label) for key, (label, _has_expiry) in types.items()]


def optional_doc_choices(types, required):
    return [
        (key, label)
        for key, (label, _has_expiry) in types.items()
        if key not in required
    ]


def required_doc_choices(types, required):
    return [(key, types[key][0]) for key in required]


def latest_validated_documents(documents):
    """Per ogni tipo, il documento validato caricato più di recente."""
    latest = {}
    for doc in documents.filter(validation_status=VALIDATED).order_by(
        "-uploaded_at", "-pk"
    ):
        latest.setdefault(doc.doc_type, doc)
    return list(latest.values())


class Technician(models.Model):
    vendor = models.ForeignKey(
        "vendors.Vendor",
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="technicians",
    )
    surname = models.CharField(_("Cognome"), max_length=100)
    first_name = models.CharField(_("Nome"), max_length=100)
    role = models.CharField(_("Mansione"), max_length=150, blank=True)
    badge = models.CharField(_("Badge"), max_length=50, blank=True)
    validation_status = models.CharField(
        _("Stato validazione"),
        max_length=20,
        choices=VALIDATION_CHOICES,
        default=PENDING,
    )
    rejection_note = models.TextField(
        _("Motivo del respingimento"), blank=True
    )
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)

    class Meta:
        verbose_name = _("Tecnico")
        verbose_name_plural = _("Tecnici")
        ordering = ["surname", "first_name"]

    def __str__(self):
        return f"{self.surname} {self.first_name}"


class TechnicianDocument(models.Model):
    technician = models.ForeignKey(
        Technician,
        verbose_name=_("Tecnico"),
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(
        _("Tipo documento"),
        max_length=50,
        choices=_doc_type_choices(TECHNICIAN_DOC_TYPES),
    )
    expiry_date = models.DateField(
        _("Data di scadenza"), null=True, blank=True
    )
    file = models.FileField(
        _("File"), upload_to="subcontractors/technicians/%Y/"
    )
    validation_status = models.CharField(
        _("Stato validazione"),
        max_length=20,
        choices=VALIDATION_CHOICES,
        default=PENDING,
    )
    rejection_note = models.TextField(
        _("Motivo del respingimento"), blank=True
    )
    uploaded_at = models.DateTimeField(_("Caricato il"), auto_now_add=True)

    class Meta:
        verbose_name = _("Documento tecnico")
        verbose_name_plural = _("Documenti tecnici")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.technician}"

    def clean(self):
        super().clean()
        has_expiry = TECHNICIAN_DOC_TYPES.get(self.doc_type, ("", False))[1]
        if has_expiry and not self.expiry_date:
            raise ValidationError(
                {
                    "expiry_date": _(
                        "Questo tipo di documento richiede una scadenza."
                    )
                }
            )


class Equipment(models.Model):
    vendor = models.ForeignKey(
        "vendors.Vendor",
        verbose_name=_("Fornitore"),
        on_delete=models.CASCADE,
        related_name="equipment_items",
    )
    equipment_type = models.CharField(_("Tipo mezzo"), max_length=150)
    plate = models.CharField(_("Targa"), max_length=20, blank=True)
    serial_code = models.CharField(
        _("Matricola/codice interno"), max_length=100, blank=True
    )
    instrument = models.CharField(_("Strumento"), max_length=150, blank=True)
    validation_status = models.CharField(
        _("Stato validazione"),
        max_length=20,
        choices=VALIDATION_CHOICES,
        default=PENDING,
    )
    rejection_note = models.TextField(
        _("Motivo del respingimento"), blank=True
    )
    created_at = models.DateTimeField(_("Creato il"), auto_now_add=True)

    class Meta:
        verbose_name = _("Mezzo/dotazione")
        verbose_name_plural = _("Mezzi/dotazioni")
        ordering = ["equipment_type", "plate"]

    def __str__(self):
        return " - ".join(
            part for part in [self.equipment_type, self.plate] if part
        )


class EquipmentDocument(models.Model):
    equipment = models.ForeignKey(
        Equipment,
        verbose_name=_("Mezzo/dotazione"),
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(
        _("Tipo documento"),
        max_length=50,
        choices=_doc_type_choices(EQUIPMENT_DOC_TYPES),
    )
    expiry_date = models.DateField(
        _("Data di scadenza"), null=True, blank=True
    )
    file = models.FileField(
        _("File"), upload_to="subcontractors/equipment/%Y/"
    )
    validation_status = models.CharField(
        _("Stato validazione"),
        max_length=20,
        choices=VALIDATION_CHOICES,
        default=PENDING,
    )
    rejection_note = models.TextField(
        _("Motivo del respingimento"), blank=True
    )
    uploaded_at = models.DateTimeField(_("Caricato il"), auto_now_add=True)

    class Meta:
        verbose_name = _("Documento mezzo")
        verbose_name_plural = _("Documenti mezzi")
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.get_doc_type_display()} - {self.equipment}"

    def clean(self):
        super().clean()
        has_expiry = EQUIPMENT_DOC_TYPES.get(self.doc_type, ("", False))[1]
        if has_expiry and not self.expiry_date:
            raise ValidationError(
                {
                    "expiry_date": _(
                        "Questo tipo di documento richiede una scadenza."
                    )
                }
            )
