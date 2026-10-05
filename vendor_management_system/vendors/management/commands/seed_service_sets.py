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

from vendor_management_system.vendors.models import (
    Category,
    ServiceSet,
    ServiceType,
)


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
        "description": (
            "Servizi di manutenzione antincendio per subappaltatori."
        ),
        "category_code": "105",
        "parent": ("SERVICE ANTINCENDIO", "SERVICE ANTINCENDIO", 510),
        "services": [
            (
                "EST.-MAN",
                "MANUTENZIONE ESTINTORI (CONTROLLO, REVISIONE, COLLAUDO)",
                511,
            ),
            ("IDRANTI-MAN", "MANUTENZIONE IDRANTI SEMESTRALE E ANNUALE", 512),
            (
                "SERR.-MAN",
                "MANUTENZIONE SERRAMENTI TAGLIAFUOCO E DISPOSITIVI DI "
                "SICUREZZA",
                513,
            ),
            ("CASS. MEDICA-MAN", "CASSETTA MEDICA CONTROLLO SEMESTRALE", 514),
            ("ARMADI DPI-MAN", "ARMADI DPI CONTROLLO SEMESTRALE", 515),
            ("AUTORESP.-MAN", "CONTROLLO AUTORESPIRATORI", 516),
            (
                "DOCCE LAVAOCCHI-MAN",
                "DOCCE LAVAOCCHI CONTROLLO SEMESTRALE",
                517,
            ),
            ("EFC - MAN.", "EFC MANUTENZIONE SEMESTRALE", 521),
            ("EFC- PROVA REALE", "EFC PROVA REALE", 522),
            ("EFC - INST.", "EFC INSTALLAZIONE", 523),
            ("LUCI EMERG.-MAN", "LAMPADE EMERGENZA CONTR. SEM.", 524),
            (
                "G.P. UNI 12845 -MAN",
                "CONTROLLO STAZIONE DI POMPAGGIO UNI12845 (SETTIMANALE, "
                "MENSILE, TRIMESTRALE)",
                525,
            ),
            (
                "G.P. NFPA -MAN",
                "CONTROLLO STAZIONE DI POMPAGGIO NFPA (SETTIMANALE, "
                "MENSILE, TRIMESTRALE)",
                526,
            ),
            (
                "G.P. UNI 12845 -SEMEST.",
                "CONTROLLO SEMESTRALE STAZIONE DI POMPAGGIO "
                "ELETTROPOMPA+MOTOPOMPA UNI12845",
                527,
            ),
            (
                "G.P. NFPA -SEMEST.",
                "CONTROLLO SEMESTRALE STAZIONE DI POMPAGGIO "
                "ELETTROPOMPA+MOTOPOMPA NFPA",
                528,
            ),
            (
                "G.P RIS. IDRICA FT",
                "CONTR. RISERVA IDRICA FUORI TERRA (SEMESTRALE, "
                "TIRENNALE, DECENNALE)",
                529,
            ),
            (
                "G.P. RIS. IDRICA INT.",
                "CONTR. SEM RISERVA IDRICA INTERRATA (SEMESTRALE, "
                "TIRENNALE, DECENNALE)",
                530,
            ),
            (
                "IMP. SPK UNI - MAN",
                "CONTROLLO IMPIANTO SPRINKLER UNI (MENSILE, "
                "TRIMESTRALE, SEMESTRALE)",
                531,
            ),
            (
                "IMP. SPK NFPA- MAN",
                "CONTROLLO IMPIANTO SPRINKLER NFPA (MENSILE, "
                "TRIMESTRALE, SEMESTRALE)",
                532,
            ),
            (
                "IMP. SCHIUMA-PREMES.",
                "IMP. SCHIUMA PREMESCOLATORE MANUTENZIONE SEMESTRALE",
                533,
            ),
            (
                "IMP. SCHIUMA-FIREDOS",
                "IMP. SCHIUMA FIREDOS MANUTENZIONE SEMESTRALE",
                534,
            ),
            (
                "IMP. SCHIUMA-MONITORI",
                "IMP. SCHIUMA MAN. MONITORI FISSI/A BRANDEGGIO",
                535,
            ),
            ("CARRI SCHIUMA-MAN", "CARRI MOBILI SCHIUMA MANUTENZIONE", 536),
            (
                "IMP. RIL. INC.-MAN",
                "IMPIANTO RILEVAZIONE INCENDIO MANUTENZIONE",
                537,
            ),
            (
                "IMP. RIL. GAS-MAN",
                "IMPIANTO RILEVAZIONE GAS CONTROLLO SEMESTRALE",
                538,
            ),
            (
                "IMP. SPEG. GAS-MAN",
                "IMPIANTO SPEGNIMENTO GAS MANUTENZIONE",
                539,
            ),
            ("IMP. SPEG. GAS-DFT", "IMP. SPEG. GAS ESECUZIONE DFT", 540),
            (
                "IMP. SPEG. GAS -COLL.",
                "IMP. SPEG. GAS ESECUZIONE COLLAUDI DECENNALI",
                541,
            ),
            ("IMP. EVAC-MAN.", "IMPIANTO EVAC CONTROLLO SEMESTRALE", 542),
            (
                "IMP. EVAC-PROVA INT.",
                "IMPIANTO EVAC PROVA INTELLEGIBILITA'",
                543,
            ),
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
            (
                "AD. MACC-PNEUMATICA",
                "INTERVENTI DI PNEUMATICA/OLEODINAMICA",
                556,
            ),
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
            (
                "S.T. PROG. INTER.LE",
                "PROGETTAZIONE SU STANDARD INTERNAZIONALI",
                568,
            ),
            (
                "S.T. PPA",
                "PROGETTAZIONE PROTEZIONE PASSIVA/ANALISI SU "
                "STRUTTURE ESISTENTI",
                569,
            ),
        ],
    },
    {
        "name": "SUB. INSTALLAZIONE IMP. ANTINCENDIO",
        "description": (
            "Servizi di installazione impianti antincendio per subappaltatori."
        ),
        "category_code": "105",
        "parent": ("ANTINCENDIO INST. IMP.", "INST. IMP. ANTINCENDIO", 570),
        "services": [
            (
                "INST. ELET. RIL E ALLARME",
                "INST. ELET. RILEVAZIONE E ALLARME INCENDI",
                571,
            ),
            (
                "INST. ELET. EVAC",
                "INST. ELET. EVAC/DIFFUSIONE SONORA EMERGENZA",
                572,
            ),
            (
                "INST. ELET. SUPERVISIONE",
                "INST. ELET. SUPERVISIONE E INTEGRAZIONE",
                573,
            ),
            (
                "INST. ELET. CENTRALI",
                "INST. ELET. PROGRAMMAZIONE CENTRALI",
                574,
            ),
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
        "description": (
            "Servizi di protezione passiva antincendio per subappaltatori."
        ),
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


# Categorie (ServiceType radice) sotto cui vivono i servizi dei set IGEAM:
# codice -> (nome, ordinamento). Come per gli altri blocchi, sono create solo
# se mancano; quelle già a catalogo non vengono toccate.
IGEAM_SERVICE_ROOTS = {
    "624": ("624", 10),
    "AMB": ("Amb", 20),
    "BASI": ("BASI", 30),
    "CGHS": ("consulenza generale HS", 40),
    "FORM": ("Formazione", 50),
    "IGIND": ("IGIENE  INDUSTRIALE", 60),
    "INGEGN": ("Ingegn", 70),
    "RISK": ("RISK", 80),
    "RISKPSICO": ("RISK Psicosociali", 90),
    "SICCANT": ("Sicurezza Cantieri", 100),
    "STRUMENTI": ("STRUMENTI DI MISURA", 610),
}

# Set Servizi IGEAM (AIDEV-118), senza classificazione fornitore. Fonte:
# "FORNITORI_SET SERVIZI con descrizioni.xlsx", foglio "SET SERVIZI". Ogni
# servizio è (codice, nome, codice categoria in IGEAM_SERVICE_ROOTS,
# ordinamento). I raggruppamenti del file sono indipendenti dall'albero
# categoria/servizio del catalogo: il padre indicato serve solo se il
# servizio manca e va creato (SERV-0114..0123 sono i servizi "da codificare").
IGEAM_SERVICE_SETS = [
    {
        "name": "RISCHIO MINERARIO",
        "description": "Servizi per il settore minerario ed estrattivo.",
        "category_code": None,
        "services": [
            ("SERV-0016", "RISCHIO MINERARIO", "624", 16),
            ("SERV-0017", "DSS/PEI", "624", 17),
        ],
    },
    {
        "name": "AMBIENTE",
        "description": "Servizi di consulenza ambientale ed energetica.",
        "category_code": None,
        "services": [
            ("SERV-0014", "ADR & RID", "AMB", 14),
            ("SERV-0054", "TCAA", "AMB", 54),
            ("SERV-0055", "ACUSTICA AMBIENTALE", "AMB", 55),
            ("SERV-0056", "SUOLO", "AMB", 56),
            ("SERV-0057", "VIA - VAS", "AMB", 57),
            ("SERV-0058", "AIA - AUA", "AMB", 58),
            ("SERV-0059", "WASTE MANAGEMENT", "AMB", 59),
            ("SERV-0060", "ACQUA", "AMB", 60),
            ("SERV-0061", "ARIA", "AMB", 61),
            ("SERV-0062", "Mobilty Manager /PIANI MOBILITA'", "AMB", 62),
            ("SERV-0063", "ENERGY MANAGEMENT", "AMB", 63),
            ("SERV-0064", "APE", "AMB", 64),
            ("SERV-0065", "TERMOGRAFIA", "AMB", 65),
            ("SERV-0066", "LCA", "AMB", 66),
        ],
    },
    {
        "name": "CERTIFICAZIONI",
        "description": "Servizi di consulenza su certificazioni e sistemi.",
        "category_code": None,
        "services": [
            ("SERV-0067", "HSE Manager - UNI 11720", "BASI", 67),
            ("SERV-0068", "DLgs 231 - MOGC", "BASI", 68),
            ("SERV-0069", "ISO 37301 - Compliance", "BASI", 69),
            ("SERV-0070", "Serie ISO 9000", "BASI", 70),
            ("SERV-0071", "Serie ISO 14000", "BASI", 71),
            ("SERV-0072", "Serie ISO 45000", "BASI", 72),
            ("SERV-0073", "ISO 50001", "BASI", 73),
            ("SERV-0074", "EMAS", "BASI", 74),
            ("SERV-0075", "Serei ISO 14064", "BASI", 75),
            ("SERV-0076", "Indicatori EFRAG", "BASI", 76),
            ("SERV-0077", "SA 8000 - ISO 26000", "BASI", 77),
            ("SERV-0078", "PdR 125", "BASI", 78),
            ("SERV-0079", "Ecovadis", "BASI", 79),
            ("SERV-0080", "SGI", "BASI", 80),
        ],
    },
    {
        "name": "CONSULENZA GENERALE HS",
        "description": "Servizi di consulenza generale su salute e sicurezza.",
        "category_code": None,
        "services": [
            ("SERV-0001", "RSPP/ASPP", "CGHS", 1),
            ("SERV-0002", "DVR", "CGHS", 2),
            ("SERV-0003", "DUVRI", "CGHS", 3),
            ("SERV-0007", "PIANI EMERGENZA", "CGHS", 7),
            ("SERV-0114", "PLANIMETRIE PIANO DI EMERGENZA", "CGHS", 114),
        ],
    },
    {
        "name": "FORMAZIONE",
        "description": "Servizi di docenza e formazione.",
        "category_code": None,
        "services": [
            ("SERV-0081", "DOC - RIFIUTI", "FORM", 81),
            ("SERV-0082", "E-LEARNING", "FORM", 82),
            ("SERV-0083", "DOC - SGI", "FORM", 83),
            ("SERV-0084", "DOC - REACH/CLP", "FORM", 84),
            ("SERV-0085", "DOC - ADR", "FORM", 85),
            ("SERV-0086", "DOC - 624", "FORM", 86),
            ("SERV-0087", "DOC - HAZOP/HAZID", "FORM", 87),
            ("SERV-0088", "Doc - In Inglese", "FORM", 88),
            ("SERV-0089", "Realtà Virtuale", "FORM", 89),
            ("SERV-0090", "00 - DM 16/01/1997 - RLS", "FORM", 90),
            (
                "SERV-0091",
                "02 - DGR n.5702 del 06/12/1999 - Amianto",
                "FORM",
                91,
            ),
            (
                "SERV-0092",
                "03 - DM 388 del 15/07/2003 - Primo Soccorso",
                "FORM",
                92,
            ),
            (
                "SERV-0093",
                "04 - ASR 26/01/2006 - Addetti Fune Portante",
                "FORM",
                93,
            ),
            (
                "SERV-0094",
                "05 - ASR 26/01/2006 - Addetti Ponteggi",
                "FORM",
                94,
            ),
            (
                "SERV-0095",
                "06 - Artt. 37 e 77 D.Lgs 81/08 - DPI 3 cat.",
                "FORM",
                95,
            ),
            (
                "SERV-0096",
                "07 - Artt. 66, 73 D.Lgs. 81/08 - Spazi Confinati",
                "FORM",
                96,
            ),
            (
                "SERV-0097",
                "08 - ASR 21/12/2011 - Datore di Lavoro",
                "FORM",
                97,
            ),
            (
                "SERV-0098",
                "09 - ASR 21/12/2011 linee applicative 27/07/2012 - "
                "Lavoratori",
                "FORM",
                98,
            ),
            ("SERV-0099", "10 - ASR 22/02/2012 - Attrezzature", "FORM", 99),
            (
                "SERV-0100",
                "11 - DM 06/03/2013 - Formatori Sicurezza",
                "FORM",
                100,
            ),
            (
                "SERV-0101",
                "12 - CEI 11-27 del 2021 - PES/PAV/PEI",
                "FORM",
                101,
            ),
            ("SERV-0102", "13 - ASR 07/07/2016 - RSPP ASPP", "FORM", 102),
            ("SERV-0103", "14 - ASR 07/07/2016 - CSP CSE", "FORM", 103),
            (
                "SERV-0104",
                "15 - DM 22/01/2019 - Segnaletica Stradale",
                "FORM",
                104,
            ),
            ("SERV-0105", "16 - BLSD/ISTRUTTORI/INFERMIERI", "FORM", 105),
            (
                "SERV-0106",
                "17 - Reg.to CE 178/2002 e 852/2004 - HACCP",
                "FORM",
                106,
            ),
            (
                "SERV-0107",
                "18 - Dlgs. 152/2006 – Codice Ambientale",
                "FORM",
                107,
            ),
            ("SERV-0108", "19 - DM 02/09/2021 - Antincendio", "FORM", 108),
            (
                "SERV-0109",
                "19.1 - SOLO TEORIA - DM 02/09/2021 - Antincendio",
                "FORM",
                109,
            ),
            (
                "SERV-0110",
                "19.2 - SOLO ATTREZZATURE - DM 02/09/2021 - Antincendio",
                "FORM",
                110,
            ),
            (
                "SERV-0111",
                "20 - D.Lgs. 152 del 03/04/2006 TU Ambiente",
                "FORM",
                111,
            ),
            ("SERV-0112", "21 - Competenze Trasversali", "FORM", 112),
            ("SERV-0113", "22 - HACCP - 1993/43/CEE", "FORM", 113),
        ],
    },
    {
        "name": "IGIENE INDUSTRIALE",
        "description": "Servizi di igiene industriale.",
        "category_code": None,
        "services": [
            ("SERV-0038", "AMIANTO", "IGIND", 38),
            ("SERV-0039", "BIOL", "IGIND", 39),
            ("SERV-0040", "cangerogeni, mutageni, reprotossici", "IGIND", 40),
            ("SERV-0041", "rischio chimico", "IGIND", 41),
            ("SERV-0042", "HACCP", "IGIND", 42),
            ("SERV-0043", "IAQ (chimica e microbiologica)", "IGIND", 43),
            ("SERV-0044", "Stress Termico", "IGIND", 44),
            ("SERV-0045", "MMC e movimenti ripetuti", "IGIND", 45),
            ("SERV-0046", "Microclima amb. moderati", "IGIND", 46),
            ("SERV-0047", "Illuminamento", "IGIND", 47),
            ("SERV-0048", "LASER", "IGIND", 48),
            ("SERV-0049", "VIBRAZIONI", "IGIND", 49),
            ("SERV-0050", "RUMORE", "IGIND", 50),
            ("SERV-0051", "ROA", "IGIND", 51),
            ("SERV-0053", "RI (Radon)", "IGIND", 53),
            ("SERV-0115", "CEM", "IGIND", 115),
        ],
    },
    {
        "name": "INGEGNERIA",
        "description": "Servizi di ingegneria e analisi di rischio.",
        "category_code": None,
        "services": [
            ("SERV-0008", "PROG. ANTINCENDIO", "INGEGN", 8),
            ("SERV-0012", "VULNERAB. SISMICA", "INGEGN", 12),
            ("SERV-0018", "BONIF-ACUS", "INGEGN", 18),
            ("SERV-0019", "HAZOP SIL Chairman", "INGEGN", 19),
            ("SERV-0020", "HAZOP SIL Scribe", "INGEGN", 20),
            ("SERV-0021", "RAM Analysis", "INGEGN", 21),
            ("SERV-0022", "3D F&G MAPPING", "INGEGN", 22),
            ("SERV-0023", "HAZID, FMEA, SIMOPS", "INGEGN", 23),
            ("SERV-0024", "SIL ALLOCATION", "INGEGN", 24),
            ("SERV-0025", "FERA, QRA, EERA, ESSA", "INGEGN", 25),
            (
                "SERV-0026",
                "AIR DISPERSION AND FLARE HEAT RADIATION",
                "INGEGN",
                26,
            ),
            ("SERV-0027", "SIL VERIFICATION/SRS/FSA", "INGEGN", 27),
            ("SERV-0028", "BOW TIE/SECE PERFORM. STANDARD", "INGEGN", 28),
            ("SERV-0029", "SAFOP & ALARM MNG.", "INGEGN", 29),
            ("SERV-0030", "RIR (RDS, NAR, SGS)", "INGEGN", 30),
        ],
    },
    {
        "name": "VALUTAZIONE RISCHI",
        "description": "Servizi di valutazione dei rischi.",
        "category_code": None,
        "services": [
            ("SERV-0004", "ATEX", "RISK", 4),
            ("SERV-0005", "RISCHIO ELETTRICO", "RISK", 5),
            ("SERV-0006", "FULMINAZIONE", "RISK", 6),
            ("SERV-0009", "VALUTAZIONE RISCHIO INCENDIO", "RISK", 9),
            ("SERV-0010", "RISCHIO MACCHINE", "RISK", 10),
            ("SERV-0011", "VERIFICA PED", "RISK", 11),
            ("SERV-0013", "SPAZI CONFINATI", "RISK", 13),
            ("SERV-0015", "REACH/CLP", "RISK", 15),
            ("SERV-0052", "Lavori in quota", "RISK", 52),
            (
                "SERV-0035",
                "RISCHIO VIOLENZA INTERNA E AGGRESSIONI",
                "RISKPSICO",
                35,
            ),
            ("SERV-0036", "Età e differenze di genere", "RISKPSICO", 36),
            ("SERV-0037", "SLC", "RISKPSICO", 37),
        ],
    },
    {
        "name": "SICUREZZA CANTIERI",
        "description": "Servizi di sicurezza nei cantieri.",
        "category_code": None,
        "services": [
            ("SERV-0031", "Direzione Lavori", "SICCANT", 31),
            ("SERV-0032", "Incarico CSE", "SICCANT", 32),
            ("SERV-0033", "POS", "SICCANT", 33),
            ("SERV-0034", "Incarico CSP -elaborazione PSC", "SICCANT", 34),
        ],
    },
    {
        "name": "STRUMENTI DI MISURA",
        "description": "Strumentazione di misura del fornitore.",
        "category_code": None,
        "services": [
            ("SERV-0116", "FONOMETRO", "STRUMENTI", 116),
            ("SERV-0117", "DINAMOMETRO", "STRUMENTI", 117),
            ("SERV-0118", "CENTRALINA MICROCLIMATICA", "STRUMENTI", 118),
            ("SERV-0119", "ACCELEROMETRO", "STRUMENTI", 119),
            ("SERV-0120", "SONDA CAMPI ELETTROMAGNETICI", "STRUMENTI", 120),
            (
                "SERV-0121",
                "POMPE PER CAMPIONAMENTO AGENTI CHIMICI",
                "STRUMENTI",
                121,
            ),
            ("SERV-0122", "LUXMETRO", "STRUMENTI", 122),
            ("SERV-0123", "TERMOCAMERA", "STRUMENTI", 123),
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Popola il catalogo Servizi e i Set Servizi usati nel tab "
        "Servizi del fornitore"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-catalog",
            action="store_true",
            help=(
                "Riallinea al file anche nome e ordinamento dei servizi già a "
                "catalogo. Di default i servizi esistenti non vengono toccati."
            ),
        )
        parser.add_argument(
            "--create-only",
            action="store_true",
            help=(
                "Crea solo i Set Servizi mancanti, senza toccare quelli già "
                "esistenti (descrizione, classificazione e lista servizi "
                "possono essere stati personalizzati da admin). Pensato per "
                "l'esecuzione automatica ad ogni deploy."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE("Inizio popolamento Set Servizi...")
        )

        update = options["update_catalog"]
        create_only = options["create_only"]
        by_norm = {
            _norm(s.code): s for s in ServiceType.objects.all() if s.code
        }
        categories = {c.code: c for c in Category.objects.all()}

        for order, spec in enumerate(SERVICE_SETS, start=1):
            parent = self._resolve_parent(spec["parent"], by_norm, update)
            resolved = [
                self._resolve_service(svc, parent, by_norm, update)
                for svc in spec["services"]
            ]
            self._sync_set(
                spec, order, resolved, categories, create_only=create_only
            )

        self._seed_igeam_sets(
            len(SERVICE_SETS), by_norm, categories, create_only
        )

        self.stdout.write(
            self.style.NOTICE("Popolamento Set Servizi completato.")
        )

    def _seed_igeam_sets(self, offset, by_norm, categories, create_only):
        """Set IGEAM: ogni servizio ha il proprio padre, creato se manca."""
        for order, spec in enumerate(IGEAM_SERVICE_SETS, start=offset + 1):
            resolved = []
            for code, name, parent_code, sort_order in spec["services"]:
                root_name, root_order = IGEAM_SERVICE_ROOTS[parent_code]
                parent = self._resolve_parent(
                    (parent_code, root_name, root_order), by_norm, False
                )
                resolved.append(
                    self._resolve_service(
                        (code, name, sort_order), parent, by_norm, False
                    )
                )
            self._sync_set(
                spec, order, resolved, categories, create_only=create_only
            )

    def _resolve_parent(self, spec, by_norm, update):
        """ServiceType categoria (senza padre) del blocco, creato se
        assente."""
        code, name, sort_order = spec
        parent = by_norm.get(_norm(code))
        if parent is None:
            parent = ServiceType.objects.create(
                code=code,
                name=name,
                sort_order=sort_order,
                is_active=True,
                parent=None,
            )
            by_norm[_norm(code)] = parent
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Creata categoria servizi '{code}' - {name}."
                )
            )
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
                code=code,
                name=name,
                sort_order=sort_order,
                is_active=True,
                parent=parent,
            )
            by_norm[_norm(code)] = service
            self.stdout.write(
                self.style.SUCCESS(f"  Creato servizio '{code}' - {name}.")
            )
        elif update:
            # Il padre non viene mai riassegnato: un servizio già classificato
            # altrove (es. gli EFC sotto la categoria EFC) resta dov'è.
            service.name = name
            service.sort_order = sort_order
            service.is_active = True
            service.save(update_fields=["name", "sort_order", "is_active"])
        return service

    def _sync_set(self, spec, order, services, categories, create_only=False):
        category = None
        if spec["category_code"]:
            category = categories.get(spec["category_code"])
            if category is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Classificazione "
                        f"'{spec['category_code']}' non trovata: "
                        f"il set '{spec['name']}' resta senza "
                        f"classificazione."
                    )
                )

        service_set, created = ServiceSet.objects.get_or_create(
            name=spec["name"],
            defaults={
                "description": spec["description"],
                "category": category,
                "is_active": True,
                "sort_order": order,
            },
        )
        if not created and create_only:
            self.stdout.write(
                f"  Set '{service_set.name}' già esistente: non toccato "
                "(--create-only)."
            )
            return

        if not created:
            service_set.description = spec["description"]
            service_set.category = category
            service_set.is_active = True
            service_set.sort_order = order
            service_set.save(
                update_fields=[
                    "description",
                    "category",
                    "is_active",
                    "sort_order",
                ]
            )

        service_set.service_types.set(services)

        verb = "Creato" if created else "Aggiornato"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} set '{service_set.name}': {len(services)} "
                f"servizi collegati."
            )
        )
