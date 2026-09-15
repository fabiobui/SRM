"""Popola il catalogo dei Set Documentali (DocumentSet).

Un Set Documentale raggruppa più tipi di documento (DocumentType) e viene usato
nella scheda fornitore, tab "Documenti", per creare in automatico la lista dei
documenti richiesti in base al set prescelto.

Il comando è idempotente: si può rieseguire senza creare duplicati (i set sono
identificati per nome). I tipi di documento devono già esistere (vedi
`populate_document_types`): qui vengono solo collegati ai set, risolvendo i
codici in modo tollerante alle differenze di formattazione (spazi, trattini,
underscore, punti).

Uso: python manage.py seed_document_sets
"""
import re

from django.core.management.base import BaseCommand

from vendor_management_system.documents.models import DocumentSet, DocumentType


def _norm(code):
    """Normalizza un codice documento per il confronto: maiuscolo, senza
    caratteri non alfanumerici (spazi, '-', '_', '.', '/')."""
    return re.sub(r"[^0-9A-Za-z]", "", code or "").upper()


# Definizione dei set. Ogni voce dei `codes` usa il codice "come da specifica";
# la risoluzione verso il DocumentType esistente avviene per confronto normalizzato.
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
        "description": "Set documentale per fornitori di servizi di Medicina del Lavoro.",
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
]


class Command(BaseCommand):
    help = "Popola il catalogo dei Set Documentali usati nel tab Documenti del fornitore"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Inizio popolamento Set Documentali..."))

        # Mappa normalizzata code -> DocumentType (una sola query).
        by_norm = {_norm(dt.code): dt for dt in DocumentType.objects.all() if dt.code}

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
                doc_set.save(update_fields=["description", "is_active", "sort_order"])

            resolved, missing = [], []
            for code in spec["codes"]:
                dt = by_norm.get(_norm(code))
                (resolved if dt else missing).append(code if not dt else dt)

            doc_set.document_types.set(resolved)

            verb = "Creato" if created else "Aggiornato"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{verb} set '{doc_set.name}': {len(resolved)} tipi collegati."
                )
            )
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Tipi documento non trovati (ignorati): {', '.join(missing)}"
                    )
                )

        self.stdout.write(self.style.NOTICE("Popolamento Set Documentali completato."))
