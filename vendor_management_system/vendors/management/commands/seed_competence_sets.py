"""Popola il catalogo dei Requisiti Professionali e i relativi Set.

Fonte: "2026-08-04_Set Requisiti professionali e set servizi.xlsx",
foglio "Set Requisiti Professionali".

Nel file la colonna "Categoria" elenca, per ogni requisito, le classificazioni
fornitore che lo richiedono (MEDICO COMPETENTE, INFERMIERE, ...). Da qui viene
creato **un set per classificazione**, così che nel tab "Requisiti Professionali"
del fornitore il dropdown proponga direttamente i requisiti della sua
classificazione.

Il comando è idempotente: i requisiti sono identificati per codice e i set per
nome, quindi si può rieseguire senza creare duplicati. I requisiti mancanti a
catalogo vengono creati, quelli esistenti aggiornati sui campi previsti dal file.

Uso: python manage.py seed_competence_sets
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from vendor_management_system.vendors.models import Category, Competence, CompetenceSet


def _norm(code):
    """Normalizza un codice per il confronto: maiuscolo, senza caratteri non
    alfanumerici (spazi, '-', '_', '.', '/')."""
    return re.sub(r"[^0-9A-Za-z]", "", code or "").upper()


# Requisiti professionali come da file.
#   code, name, competence_category, is_mandatory, requires_certification,
#   renewal_period_months (None = nessun rinnovo)
COMPETENCES = [
    # --- Set Requisiti Professionali MDL ---
    ("MDL-R01", "Albo Medici Competenti", "DOCTOR", True, True, 12),
    ("MDL-R02", "Albo Infermieri", "DOCTOR", True, True, 12),
    ("MDL-R03", "Albo Medici Autorizzati", "DOCTOR", True, True, 12),
    ("MDL-R04", "Autodichiarazione crediti ECM", "DOCTOR", True, True, 36),
    # Obbligatorio solo per gli infermieri di presidio: a catalogo resta non
    # obbligatorio, l'obbligo è espresso dall'appartenenza al set.
    ("MDL-R05", "BLSD", "DOCTOR", False, True, 24),
    ("MDL-R06", "Albo medico professionista", "DOCTOR", True, True, 12),
    # --- Set Requisiti Subappaltatori ---
    ("Patente a crediti", "Patente a crediti", "SAFETY", False, True, None),
    ("SOA", "Attestazione SOA", "SAFETY", False, True, None),
    ("AMB-Cat.2bis", "Autorizzazione Trasporto rifiuti cat. 2Bis", "ENVIRONMENT", False, True, None),
    ("Lettera G DM37/2008", "Abilitazione Installazione Impianti Protezione Antincendio",
     "TECHNICAL", False, True, None),
    ("FGAS", "Certificato F-Gas", "TECHNICAL", False, True, None),
    ("Saldatura", "Tecnici con patentini saldatura PED", "TECHNICAL", False, True, None),
]

# Rinnovo richiesto ma senza periodicità indicata nel file.
RENEWAL_WITHOUT_PERIOD = {"SOA", "AMB-Cat.2bis", "FGAS", "Saldatura"}

# Un set per classificazione fornitore (codice Category -> requisiti).
COMPETENCE_SETS = [
    {
        "name": "MDL - MEDICO COMPETENTE",
        "description": "Requisiti professionali per i medici competenti (Medicina del Lavoro).",
        "category_code": "104103",
        "codes": ["MDL-R01", "MDL-R03", "MDL-R04", "MDL-R05"],
    },
    {
        "name": "MDL - INFERMIERE",
        "description": "Requisiti professionali per gli infermieri (Medicina del Lavoro).",
        "category_code": "104101",
        "codes": ["MDL-R02", "MDL-R04", "MDL-R05"],
    },
    {
        "name": "MDL - INFERMIERE DI PRESIDIO",
        "description": "Requisiti professionali per gli infermieri di presidio. Il BLSD "
                       "(MDL-R05) è obbligatorio per questa classificazione.",
        "category_code": "104106",
        "codes": ["MDL-R02", "MDL-R04", "MDL-R05"],
    },
    {
        "name": "MDL - PROFESSIONISTA GENERICO",
        "description": "Requisiti professionali per i professionisti generici (Medicina del Lavoro).",
        "category_code": "104104",
        "codes": ["MDL-R03", "MDL-R04", "MDL-R05", "MDL-R06"],
    },
    {
        "name": "SUBAPPALTATORI",
        "description": "Requisiti professionali per i fornitori di tipo Subappaltatore.",
        "category_code": "105",
        "codes": ["Patente a crediti", "SOA", "AMB-Cat.2bis",
                  "Lettera G DM37/2008", "FGAS", "Saldatura"],
    },
]


class Command(BaseCommand):
    help = ("Popola il catalogo Requisiti Professionali e i Set Requisiti usati "
            "nel tab Requisiti Professionali del fornitore")

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-catalog",
            action="store_true",
            help=("Riallinea al file anche i requisiti già presenti a catalogo. "
                  "Di default i requisiti esistenti non vengono toccati: il DB "
                  "contiene valori più ricchi di quelli del file (es. la "
                  "periodicità di rinnovo di SOA, F-GAS, SALDATURA)."),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Inizio popolamento Requisiti Professionali..."))

        by_norm = self._sync_catalog(update_existing=options["update_catalog"])
        self._sync_sets(by_norm)

        self.stdout.write(self.style.NOTICE("Popolamento Set Requisiti Professionali completato."))

    def _sync_catalog(self, update_existing=False):
        """Crea i requisiti mancanti a catalogo. Ritorna la mappa codice
        normalizzato -> Competence, comprensiva di quelli già presenti.

        I requisiti già a catalogo vengono lasciati intatti salvo
        ``--update-catalog``: i codici del file sono spesso formattati in modo
        diverso da quelli a DB (``FGAS``/``F-GAS``, ``AMB-Cat.2bis``/
        ``AMB-Cat. 2bis``) e la risoluzione avviene per confronto normalizzato.
        """
        by_norm = {_norm(c.code): c for c in Competence.objects.all() if c.code}

        for order, (code, name, cat, mandatory, cert, months) in enumerate(COMPETENCES, start=1):
            renewal = months is not None or code in RENEWAL_WITHOUT_PERIOD
            existing = by_norm.get(_norm(code))
            values = {
                "name": name,
                "competence_category": cat,
                "is_mandatory": mandatory,
                "requires_certification": cert,
                "requires_renewal": renewal,
                "renewal_period_months": months,
                "is_active": True,
                "sort_order": order,
            }

            if existing and not update_existing:
                continue
            if existing:
                for field, value in values.items():
                    setattr(existing, field, value)
                existing.save(update_fields=list(values))
                self.stdout.write(f"  Aggiornato requisito '{existing.code}'.")
            else:
                created = Competence.objects.create(code=code, **values)
                by_norm[_norm(code)] = created
                self.stdout.write(self.style.SUCCESS(f"  Creato requisito '{code}' - {name}."))

        return by_norm

    def _sync_sets(self, by_norm):
        categories = {c.code: c for c in Category.objects.all()}

        for order, spec in enumerate(COMPETENCE_SETS, start=1):
            category = categories.get(spec["category_code"])
            if category is None:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ Classificazione '{spec['category_code']}' non trovata: "
                    f"il set '{spec['name']}' resta senza classificazione."
                ))

            comp_set, created = CompetenceSet.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "description": spec["description"],
                    "category": category,
                    "is_active": True,
                    "sort_order": order,
                },
            )
            if not created:
                comp_set.description = spec["description"]
                comp_set.category = category
                comp_set.is_active = True
                comp_set.sort_order = order
                comp_set.save(update_fields=["description", "category", "is_active", "sort_order"])

            resolved, missing = [], []
            for code in spec["codes"]:
                competence = by_norm.get(_norm(code))
                (resolved if competence else missing).append(competence or code)

            comp_set.competences.set(resolved)

            verb = "Creato" if created else "Aggiornato"
            self.stdout.write(self.style.SUCCESS(
                f"{verb} set '{comp_set.name}': {len(resolved)} requisiti collegati."
            ))
            if missing:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ Requisiti non trovati (ignorati): {', '.join(missing)}"
                ))
