"""Popola il catalogo Servizi e i relativi Set.

Fonte: "2026-08-04_Set Requisiti professionali e set servizi.xlsx",
foglio "Set Servizi".

Ogni blocco del file diventa un ServiceSet, usato dal dropdown "Set Servizi"
nel tab Servizi del fornitore. La riga marcata "è categoria" nella colonna
CATEGORIA non entra nel set: individua il ServiceType padre sotto cui creare i
servizi mancanti (nell'inline Servizi si assegnano solo i servizi specifici,
mai le categorie).

Il comando è idempotente: i servizi sono identificati per codice normalizzato e
i set per nome. I servizi già a catalogo non vengono modificati (a DB i nomi
sono spesso più estesi di quelli del file, es. "Installazione Elettrica
Rilevazione e Allarme Incendi" contro "INST. ELET. RILEVAZIONE E ALLARME
INCENDI"); vengono creati solo quelli mancanti, sotto il padre del proprio
blocco. Un servizio già esistente sotto un altro padre resta dov'è e viene
semplicemente collegato al set.

Uso: python manage.py seed_service_sets
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from vendor_management_system.vendors.models import Category, ServiceSet, ServiceType


def _norm(code):
    """Normalizza un codice per il confronto: maiuscolo, senza caratteri non
    alfanumerici (spazi, '-', '_', '.', '/')."""
    return re.sub(r"[^0-9A-Za-z]", "", code or "").upper()


# Definizione dei set, come da file. Per ogni blocco: la classificazione
# fornitore a cui si applica, il ServiceType padre e i servizi specifici.
SERVICE_SETS = [
    {
        "name": "MEDICINA DEL LAVORO",
        "description": "Servizi di Medicina del Lavoro.",
        "category_code": "104",
        "parent": ("MDL", "Medicina del lavoro", 600),
        "services": [
            ("MDL-001", "Prelievi ematochimici", 601),
            ("MDL-002", "Drug test", 602),
            ("MDL-003", "Esecuzione ECG", 603),
            ("MDL-004", "Affitto ambulatorio", 604),
            ("MDL-005", "Servizio poliambulatoriale", 605),
            ("MDL-006", "Dotazione strumenti propri", 606),
            ("MDL-007", "Trasfertista", 607),
            ("MDL-008", "Medico Autorizzato", 608),
            ("MDL-009", "Uscita Infermiere", 609),
            ("MDL-010", "Refertazione", 610),
            ("MDL-011", "Portale on-line per scarico referti", 611),
            ("MDL-012", "Proprio ambulatorio d’appoggio", 612),
            ("MDL-013", "Unità Mobile", 613),
            ("MDL-020", "Oculista", 620),
            ("MDL-021", "Cardiologo", 621),
            ("MDL-022", "Dermatologo", 622),
            ("MDL-023", "Podologo", 623),
            ("MDL-024", "Fisioterapista", 624),
            ("MDL-025", "Ortopedico", 625),
            ("MDL-026", "Psicologo", 626),
            ("MDL-027", "Psichiatra", 627),
        ],
    },
    {
        "name": "SUB. SECURITY",
        "description": "Servizi di security per subappaltatori.",
        "category_code": "105",
        "parent": ("SECURITY", "SECURITY", 500),
        "services": [
            ("SECURITY-SERV", "SERVICE", 502),
            ("SECURITY-INST", "INSTALLAZIONE", 503),
            ("SECURITY-FORN", "FORNITURA MATERIALE SPECIFICO (GUNNEBO)", 501),
        ],
    },
    {
        "name": "SUB. SERVICE ANTINCENDIO",
        "description": "Servizi di manutenzione antincendio per subappaltatori.",
        "category_code": "105",
        "parent": ("SERVICE ANTINCENDIO", "SERVICE ANTINCENDIO", 510),
        "services": [
            ("EST.-MAN", "MANUTENZIONE ESTINTORI (CONTROLLO, REVISIONE, COLLAUDO)", 511),
            ("IDRANTI-MAN", "MANUTENZIONE IDRANTI SEMESTRALE E ANNUALE", 512),
            ("SERR.-MAN", "MANUTENZIONE SERRAMENTI TAGLIAFUOCO E DISPOSITIVI DI SICUREZZA", 513),
            ("CASS. MEDICA-MAN", "CASSETTA MEDICA CONTROLLO SEMESTRALE", 514),
            ("ARMADI DPI-MAN", "ARMADI DPI CONTROLLO SEMESTRALE", 515),
            ("AUTORESP.-MAN", "CONTROLLO AUTORESPIRATORI", 516),
            ("DOCCE LAVAOCCHI-MAN", "DOCCE LAVAOCCHI CONTROLLO SEMESTRALE", 517),
            ("EFC - MAN.", "EFC MANUTENZIONE SEMESTRALE", 521),
            ("EFC- PROVA REALE", "EFC PROVA REALE", 522),
            ("EFC - INST.", "EFC INSTALLAZIONE", 523),
            ("LUCI EMERG.-MAN", "LAMPADE EMERGENZA CONTR. SEM.", 524),
            ("G.P. UNI 12845 -MAN", "CONTROLLO STAZIONE DI POMPAGGIO UNI12845 (SETTIMANALE, MENSILE, TRIMESTRALE)", 525),
            ("G.P. NFPA -MAN", "CONTROLLO STAZIONE DI POMPAGGIO NFPA (SETTIMANALE, MENSILE, TRIMESTRALE)", 526),
            ("G.P. UNI 12845 -SEMEST.", "CONTROLLO SEMESTRALE STAZIONE DI POMPAGGIO ELETTROPOMPA+MOTOPOMPA UNI12845", 527),
            ("G.P. NFPA -SEMEST.", "CONTROLLO SEMESTRALE STAZIONE DI POMPAGGIO ELETTROPOMPA+MOTOPOMPA NFPA", 528),
            ("G.P RIS. IDRICA FT", "CONTR. RISERVA IDRICA FUORI TERRA (SEMESTRALE, TIRENNALE, DECENNALE)", 529),
            ("G.P. RIS. IDRICA INT.", "CONTR. SEM RISERVA IDRICA INTERRATA (SEMESTRALE, TIRENNALE, DECENNALE)", 530),
            ("IMP. SPK UNI - MAN", "CONTROLLO IMPIANTO SPRINKLER UNI (MENSILE, TRIMESTRALE, SEMESTRALE)", 531),
            ("IMP. SPK NFPA- MAN", "CONTROLLO IMPIANTO SPRINKLER NFPA (MENSILE, TRIMESTRALE, SEMESTRALE)", 532),
            ("IMP. SCHIUMA-PREMES.", "IMP. SCHIUMA PREMESCOLATORE MANUTENZIONE SEMESTRALE", 533),
            ("IMP. SCHIUMA-FIREDOS", "IMP. SCHIUMA FIREDOS MANUTENZIONE SEMESTRALE", 534),
            ("IMP. SCHIUMA-MONITORI", "IMP. SCHIUMA MAN. MONITORI FISSI/A BRANDEGGIO", 535),
            ("CARRI SCHIUMA-MAN", "CARRI MOBILI SCHIUMA MANUTENZIONE", 536),
            ("IMP. RIL. INC.-MAN", "IMPIANTO RILEVAZIONE INCENDIO MANUTENZIONE", 537),
            ("IMP. RIL. GAS-MAN", "IMPIANTO RILEVAZIONE GAS CONTROLLO SEMESTRALE", 538),
            ("IMP. SPEG. GAS-MAN", "IMPIANTO SPEGNIMENTO GAS MANUTENZIONE", 539),
            ("IMP. SPEG. GAS-DFT", "IMP. SPEG. GAS ESECUZIONE DFT", 540),
            ("IMP. SPEG. GAS -COLL.", "IMP. SPEG. GAS ESECUZIONE COLLAUDI DECENNALI", 541),
            ("IMP. EVAC-MAN.", "IMPIANTO EVAC CONTROLLO SEMESTRALE", 542),
            ("IMP. EVAC-PROVA INT.", "IMPIANTO EVAC PROVA INTELLEGIBILITA'", 543),
        ],
    },
    {
        "name": "SUB. ADEGUAMENTO MACCHINE",
        "description": "Servizi di adeguamento macchine per subappaltatori.",
        "category_code": "105",
        "parent": ("ADEGUAMENTO MACCHINE", "ADEGUAMENTO MACCHINE", 550),
        "services": [
            ("AD. MACC-SERV", "SERVICE", 551),
            ("AD. MACC-ELET.", "CABLAGGI ELETTRICI", 552),
            ("AD.MACC-INST.", "INST. PROTEZIONI", 553),
            ("AD. MACC-QUADRI", "QUADRI ELETTRICI", 554),
            ("AD. MACC-CONS.", "DOCUMENTI-CONSULENZA", 555),
            ("AD. MACC-PNEUMATICA", "INTERVENTI DI PNEUMATICA/OLEODINAMICA", 556),
        ],
    },
    {
        "name": "STUDIO TECNICO",
        "description": "Servizi di studio tecnico e progettazione.",
        "category_code": None,
        "parent": ("STUDIO TECNICO", "STUDIO TECNICO", 560),
        "services": [
            ("S.T. PROG. IMP. ELET.", "PROGETTAZIONE IMPIANTI ELETTRICI", 561),
            ("S.T. PROG. IMP. MEC.", "PROGETTAZIONE IMPIANTI MECCANICI", 562),
            ("S.T. SOPRALL.", "SOPRALLUOGHI", 563),
            ("S.T. FATTIBILITA’", "STUDI DI FATTIBILITA’", 564),
            ("S.T. VAL. PROG.", "VALIDAZIONE SU PROGETTI TERZI", 565),
            ("S.T. CERT. IMP.", "CERTIFICAZIONI IMPIANTI", 566),
            ("S.T. CONSULENZA", "CONSULENZA PRATICHE EDILIZIE", 567),
            ("S.T. PROG. INTER.LE", "PROGETTAZIONE SU STANDARD INTERNAZIONALI", 568),
            ("S.T. PPA", "PROGETTAZIONE PROTEZIONE PASSIVA/ANALISI SU STRUTTURE ESISTENTI", 569),
        ],
    },
    {
        "name": "SUB. INSTALLAZIONE IMP. ANTINCENDIO",
        "description": "Servizi di installazione impianti antincendio per subappaltatori.",
        "category_code": "105",
        "parent": ("ANTINCENDIO INST. IMP.", "INST. IMP. ANTINCENDIO", 570),
        "services": [
            ("INST. ELET. RIL E ALLARME", "INST. ELET. RILEVAZIONE E ALLARME INCENDI", 571),
            ("INST. ELET. EVAC", "INST. ELET. EVAC/DIFFUSIONE SONORA EMERGENZA", 572),
            ("INST. ELET. SUPERVISIONE", "INST. ELET. SUPERVISIONE E INTEGRAZIONE", 573),
            ("INST. ELET. CENTRALI", "INST. ELET. PROGRAMMAZIONE CENTRALI", 574),
            ("INST. MEC. SPRINKLER", "INST. MECC. IMPIANTI SPRINKLER", 581),
            ("INST. MEC. IDRANTI", "INST. MECC. IMPIANTI IDRANTI", 582),
            ("INST. MEC. SCHIUMA", "INST. MECC. IMPIANTI SCHIUMA", 583),
            ("INST. MEC. GAS", "INST. MECC. IMPIANTI GAS", 584),
            ("INST. MEC. DFT", "INST. MECC. DFT (Door Fan Test)", 585),
            ("INST. MEC. EDILI", "INST. MECC. SCAVI E OPERE CIVILI", 586),
        ],
    },
    {
        "name": "SUB. PROTEZIONE PASSIVA ANTINCENDIO",
        "description": "Servizi di protezione passiva antincendio per subappaltatori.",
        "category_code": "105",
        "parent": ("PPA", "PPA", 590),
        "services": [
            ("PPA-INST", "INSTALLAZIONE SERRAMENTI TAGLIAFUOCO", 591),
            ("PPA-TRATT.", "TRATTAMENTO ANT. ATTRAVERSAMENTI IMPIANTI", 592),
            ("PPA-CARP.", "REALIZZAZIONE/INST. CARPENTERIA METALLICA", 593),
            ("PPA-EDILE", "OPERE EDILI ANT. MURATURA", 594),
            ("PPA-CARTONGESSO", "OPERE EDILI ANT. CARTONGESSO", 595),
            ("PPA-SERR.", "INST. SERRAMENTI SICUREZZA", 596),
            ("PPA-TENDA", "INST. TENDA TAGLIAFUOCO", 597),
        ],
    },
]


class Command(BaseCommand):
    help = "Popola il catalogo Servizi e i Set Servizi usati nel tab Servizi del fornitore"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-catalog",
            action="store_true",
            help=("Riallinea al file anche nome e ordinamento dei servizi già a "
                  "catalogo. Di default i servizi esistenti non vengono toccati."),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Inizio popolamento Set Servizi..."))

        update = options["update_catalog"]
        by_norm = {_norm(s.code): s for s in ServiceType.objects.all() if s.code}
        categories = {c.code: c for c in Category.objects.all()}

        for order, spec in enumerate(SERVICE_SETS, start=1):
            parent = self._resolve_parent(spec["parent"], by_norm, update)
            resolved = [
                self._resolve_service(svc, parent, by_norm, update)
                for svc in spec["services"]
            ]
            self._sync_set(spec, order, resolved, categories)

        self.stdout.write(self.style.NOTICE("Popolamento Set Servizi completato."))

    def _resolve_parent(self, spec, by_norm, update):
        """ServiceType categoria (senza padre) del blocco, creato se assente."""
        code, name, sort_order = spec
        parent = by_norm.get(_norm(code))
        if parent is None:
            parent = ServiceType.objects.create(
                code=code, name=name, sort_order=sort_order, is_active=True, parent=None
            )
            by_norm[_norm(code)] = parent
            self.stdout.write(self.style.SUCCESS(f"  Creata categoria servizi '{code}' - {name}."))
        elif update:
            parent.name = name
            parent.sort_order = sort_order
            parent.is_active = True
            parent.save(update_fields=["name", "sort_order", "is_active"])
        return parent

    def _resolve_service(self, spec, parent, by_norm, update):
        """Servizio specifico del blocco, creato sotto `parent` se assente."""
        code, name, sort_order = spec
        service = by_norm.get(_norm(code))
        if service is None:
            service = ServiceType.objects.create(
                code=code, name=name, sort_order=sort_order, is_active=True, parent=parent
            )
            by_norm[_norm(code)] = service
            self.stdout.write(self.style.SUCCESS(f"  Creato servizio '{code}' - {name}."))
        elif update:
            # Il padre non viene mai riassegnato: un servizio già classificato
            # altrove (es. gli EFC sotto la categoria EFC) resta dov'è.
            service.name = name
            service.sort_order = sort_order
            service.is_active = True
            service.save(update_fields=["name", "sort_order", "is_active"])
        return service

    def _sync_set(self, spec, order, services, categories):
        category = None
        if spec["category_code"]:
            category = categories.get(spec["category_code"])
            if category is None:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ Classificazione '{spec['category_code']}' non trovata: "
                    f"il set '{spec['name']}' resta senza classificazione."
                ))

        service_set, created = ServiceSet.objects.get_or_create(
            name=spec["name"],
            defaults={
                "description": spec["description"],
                "category": category,
                "is_active": True,
                "sort_order": order,
            },
        )
        if not created:
            service_set.description = spec["description"]
            service_set.category = category
            service_set.is_active = True
            service_set.sort_order = order
            service_set.save(update_fields=["description", "category", "is_active", "sort_order"])

        service_set.service_types.set(services)

        verb = "Creato" if created else "Aggiornato"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} set '{service_set.name}': {len(services)} servizi collegati."
        ))
