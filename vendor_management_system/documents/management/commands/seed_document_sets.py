"""Popola il catalogo dei Set Documentali (DocumentSet).

Un Set Documentale raggruppa più tipi di documento (DocumentType) e viene usato
nella scheda fornitore, tab "Documenti", per creare in automatico la lista dei
documenti richiesti in base al set prescelto.

Il comando è idempotente: si può rieseguire senza creare duplicati (i set sono
identificati per nome, i tipi di documento per `code`). La maggior parte dei
tipi di documento deve già esistere (vedi `populate_document_types`): vengono
collegati ai set risolvendo i codici in modo tollerante alle differenze di
formattazione (spazi, trattini, underscore, punti). I pochi tipi mancanti
richiesti dai nuovi set (AIDEV-10: CV, Documento di Identità, Informativa
Trattamento Dati, Polizza Assicurativa) vengono creati qui direttamente.

Uso: python manage.py seed_document_sets
"""

import re

from django.core.management.base import BaseCommand

from vendor_management_system.documents.models import (
    DocumentCatalog,
    DocumentSet,
)


def _norm(code):
    """Normalizza un codice documento per il confronto: maiuscolo, senza
    caratteri non alfanumerici (spazi, '-', '_', '.', '/')."""
    return re.sub(r"[^0-9A-Za-z]", "", code or "").upper()


# Documenti mancanti a catalogo, richiesti dai nuovi Set Documentali
# Formatore/Dipendente/Consulente/Laboratorio (AIDEV-10). Informazioni
# minime: codice, nome, categoria, obbligatorietà/rinnovo.
#   code, name, document_category, is_required, requires_renewal,
#   validity_period_days
NEW_DOCUMENT_TYPES = [
    ("CV", "Curriculum Vitae", "OTHER", True, False, 365),
    (
        "DOC_IDENT",
        "Documento di Identità",
        "LEGAL",
        True,
        True,
        3650,
    ),
    (
        "INF_PRIVACY",
        "Informativa Trattamento Dati Personali",
        "LEGAL",
        True,
        False,
        365,
    ),
    ("POLIZZA", "Polizza Assicurativa", "INSURANCE", True, True, 365),
]

# Definizione dei set. Ogni voce dei `codes` usa il codice "come da
# specifica"; la risoluzione verso il DocumentCatalog esistente avviene per
# confronto normalizzato.
DOCUMENT_SETS = [
    {
        "name": "SUBAPPALTATORE",
        "description": "Set documentale per fornitori di tipo Subappaltatore.",
        "codes": [
            "ITP",
            "Patente a crediti",
            "SOA",
            "AMB-Cat.2bis",
            "Lettera G DM37/2008",
            "RC PROF",
            "DURC",
            "VISURA_CAM",
        ],
    },
    {
        "name": "MEDICINA DEL LAVORO",
        "description": (
            "Set documentale per fornitori di servizi di Medicina del Lavoro."
        ),
        "codes": [
            "RC PROF",
            "DURC",
            "VISURA_CAM",
            "ACQ-CONT",
            "ACQ-ALL1",
            "ACQ-ALL2",
            "ACQ-ALL3",
            "ACQ-ALL6",
            "SA8000-CERT",
            "CERT_LAB.",
            "CART-SAN",
            "TAV-GRAF",
            "STR-MDL",
        ],
    },
    {
        "name": "FORMATORE",
        "description": (
            "Set documentale per fornitori di tipo Formatore/Società di "
            "formazione."
        ),
        "codes": [
            "CV",
            "VISURA_CAM",
            "DURC",
            "POLIZZA",
            "INF_PRIVACY",
            "ACQ-ALL2",
        ],
    },
    {
        "name": "DIPENDENTE",
        "description": "Set documentale per fornitori di tipo Dipendente.",
        "codes": ["CV", "DOC_IDENT"],
    },
    {
        "name": "CONSULENTE",
        "description": "Set documentale per fornitori di tipo Consulente.",
        "codes": [
            "CV",
            "VISURA_CAM",
            "DURC",
            "POLIZZA",
            "INF_PRIVACY",
            "ACQ-ALL2",
        ],
    },
    {
        "name": "LABORATORIO",
        "description": "Set documentale per fornitori di tipo Laboratorio.",
        "codes": [
            "VISURA_CAM",
            "DURC",
            "POLIZZA",
            "INF_PRIVACY",
            "ACQ-ALL2",
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Popola il catalogo dei Set Documentali usati nel tab Documenti "
        "del fornitore"
    )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Inizio popolamento Set Documentali...")
        )

        self._sync_new_document_types()

        # Mappa normalizzata code -> DocumentCatalog (una sola query).
        by_norm = {
            _norm(dt.code): dt
            for dt in DocumentCatalog.objects.all()
            if dt.code
        }

        for order, spec in enumerate(DOCUMENT_SETS, start=1):
            doc_set, created = DocumentSet.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "description": spec["description"],
                    "default_status": "PENDING",
                    "is_active": True,
                    "sort_order": order,
                },
            )
            if not created:
                doc_set.description = spec["description"]
                doc_set.is_active = True
                doc_set.sort_order = order
                doc_set.save(
                    update_fields=["description", "is_active", "sort_order"]
                )

            resolved, missing = [], []
            for code in spec["codes"]:
                dt = by_norm.get(_norm(code))
                (resolved if dt else missing).append(code if not dt else dt)

            doc_set.document_types.set(resolved)

            verb = "Creato" if created else "Aggiornato"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{verb} set '{doc_set.name}': {len(resolved)} tipi "
                    "collegati."
                )
            )
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        "  ⚠ Tipi documento non trovati (ignorati): "
                        f"{', '.join(missing)}"
                    )
                )

        self.stdout.write(
            self.style.NOTICE("Popolamento Set Documentali completato.")
        )

    def _sync_new_document_types(self):
        """Crea a catalogo i tipi di documento mancanti richiesti dai nuovi
        Set Documentali (idempotente: identificati per `code`)."""
        for (
            code,
            name,
            category,
            is_required,
            requires_renewal,
            validity_period_days,
        ) in NEW_DOCUMENT_TYPES:
            dt, created = DocumentCatalog.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "document_category": category,
                    "is_required": is_required,
                    "requires_renewal": requires_renewal,
                    "validity_period_days": validity_period_days,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Creato tipo documento '{dt.code}' - {dt.name}."
                    )
                )
