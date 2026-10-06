"""Travasa le vecchie zone di competenza nei nuovi campi territoriali.

Due sorgenti, unite (mai una che sostituisce l'altra):

1. Le `CompetenceZone` assegnate al fornitore, espanse applicando le
   regole INCLUDE meno quelle EXCLUDE. Una zona senza regole utilizzabili
   viene interpretata dal suo nome, come il testo libero.
2. Il vecchio campo testuale libero `Vendor.competences_zone`, popolato a
   suo tempo dall'import Excel, riconosciuto con un match best-effort.

Cio' che non fa match non viene indovinato: finisce nel report prodotto
da `data_migration_scripts/report_competence_zone_migration.py`, da
lanciare in `--dry-run` PRIMA di migrare, finche' il testo originale
esiste ancora.

Le funzioni di matching stanno dentro questo file e non in un modulo
della app: la migrazione deve restare rigiocabile anche dopo che lo stack
legacy sara' stato cancellato, altrimenti un `migrate` da zero
esploderebbe. Script e test le importano con `importlib.import_module`.

La normalizzazione del testo e' fatta in Python e mai con lookup a
database: su MySQL la collation `utf8mb4_*_ci` e' case- e
accent-insensitive, su SQLite no, e i test veloci girano su SQLite.
"""

import re
import unicodedata
import uuid

from django.db import migrations

from vendor_management_system.vendors.geography_seed import (
    FIXTURE_ITALIA,
    FIXTURE_NAZIONI,
    carica_fixture,
)

# Sinonimi che la sola normalizzazione non riconcilia.
ALIAS_REGIONI = {
    "sudtirol": "trentino alto adige",
    "sud tirol": "trentino alto adige",
    "alto adige": "trentino alto adige",
    "val d aosta": "valle d aosta",
    "friuli": "friuli venezia giulia",
    "fvg": "friuli venezia giulia",
    "emilia": "emilia romagna",
}

# Forme brevi dei nomi di provincia e comuni presenti nei dati legacy,
# ricondotti alla sigla della loro provincia.
ALIAS_PROVINCE = {
    "trentino": "TN",
    "bozen": "BZ",
    "monza": "MB",
    "brianza": "MB",
    "monza brianza": "MB",
    "pesaro": "PU",
    "urbino": "PU",
    "pesaro urbino": "PU",
    "massa": "MS",
    "carrara": "MS",
    "forli": "FC",
    "cesena": "FC",
    "barletta": "BT",
    "andria": "BT",
    "trani": "BT",
    "verbania": "VB",
    "aquila": "AQ",
    "spezia": "SP",
    # Comuni
    "albano": "RM",
    "albano laziale": "RM",
    "albenga": "SV",
    "aprilia": "LT",
    "avenza": "MS",
    "avezzano": "AQ",
    "bitonto": "BA",
    "busto arsizio": "VA",
    "carate brianza": "MB",
    "cengio": "SV",
    "cervia": "RA",
    "chianciano": "SI",
    "chianciano terme": "SI",
    "ciampino": "RM",
    "conegliano": "TV",
    "follonica": "GR",
    "gaeta": "LT",
    "gavorrano": "GR",
    "gela": "CL",
    "guidonia": "RM",
    "jesi": "AN",
    "lamezia": "CZ",
    "lamezia terme": "CZ",
    "lavagna": "GE",
    "manfredonia": "FG",
    "marghera": "VE",
    "mesagne": "BR",
    "mestre": "VE",
    "moliterno": "PZ",
    "montalto uffugo": "CS",
    "montevarchi": "AR",
    "novi ligure": "AL",
    "olbia": "SS",
    "osimo": "AN",
    "ostia": "RM",
    "pomezia": "RM",
    "porto marghera": "VE",
    "sant antimo": "NA",
    "valbruna": "UD",
    "viggiano": "PZ",
    "villapiana": "CS",
    "villapiana lido": "CS",
}

# Nomi alternativi di nazioni estere a catalogo.
ALIAS_NAZIONI = {
    "inghilterra": "regno unito",
}

# Aree sub-regionali con confini netti, espresse come elenco di province.
ALIAS_AREE = {
    "romagna": ("RA", "FC", "RN"),
}

# Testi che significano "tutto il territorio nazionale".
TUTTA_ITALIA = {
    "italia",
    "italiana",
    "italiano",
    "nazionale",
    "tutta italia",
    "tutta l italia",
    "tutto il territorio nazionale",
    "territorio nazionale",
}

# Macro-aree deliberatamente NON interpretate: "nord" puo' voler dire
# nord-ovest, nord-est o entrambi, e indovinare scriverebbe dati sbagliati
# in silenzio. Vanno risolte a mano leggendo il report.
MACRO_AREE = {
    "nord",
    "nord italia",
    "italia del nord",
    "settentrione",
    "centro",
    "centro italia",
    "sud",
    "sud italia",
    "meridione",
    "isole",
    "nord ovest",
    "nord est",
    "centro nord",
    "centro sud",
}

# Parole di contorno ignorate quando non fanno parte di un nome noto.
PAROLE_VUOTE = {
    "a",
    "al",
    "alta",
    "area",
    "bassa",
    "d",
    "da",
    "dei",
    "del",
    "della",
    "delle",
    "di",
    "e",
    "ed",
    "in",
    "l",
    "la",
    "le",
    "prov",
    "provincia",
    "province",
    "regione",
    "regioni",
    "zona",
    "zone",
}

SEPARATORI = re.compile(r"[,;/|+]| e | - | ed ")


def _senza_accenti(testo):
    decomposto = unicodedata.normalize("NFKD", str(testo))
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizza(testo):
    """Minuscolo, senza accenti, senza punteggiatura, spazi collassati."""
    if not testo:
        return ""
    solo_alfanumerico = re.sub(r"[^0-9a-zA-Z]+", " ", _senza_accenti(testo))
    return " ".join(solo_alfanumerico.split()).casefold()


def costruisci_indice(nazioni, regioni, province):
    """Indice dei nomi canonici, a partire dalle righe di catalogo.

    `nazioni`, `regioni` e `province` sono liste di tuple:
    `(code, name)` per le nazioni, `(code, name, country_code)` per le
    regioni, `(code, name, region_code)` per le province.
    """
    province_per_regione = {}
    province_per_nazione = {}
    regione_di_nazione = {}

    for code, _name, country_code in regioni:
        regione_di_nazione[code] = country_code

    for code, _name, region_code in province:
        province_per_regione.setdefault(region_code, []).append(code)
        nazione = regione_di_nazione.get(region_code)
        if nazione:
            province_per_nazione.setdefault(nazione, []).append(code)

    return {
        "nazione_per_nome": {normalizza(n): c for c, n in nazioni},
        "regione_per_nome": {normalizza(n): c for c, n, _ in regioni},
        "provincia_per_nome": {normalizza(n): c for c, n, _ in province},
        "provincia_per_sigla": {c.upper(): c for c, _n, _r in province},
        "regione_di_provincia": {c: r for c, _n, r in province},
        "province_per_regione": province_per_regione,
        "province_per_nazione": province_per_nazione,
        "nazioni_foglia": {
            c for c, _n in nazioni if c not in set(regione_di_nazione.values())
        },
    }


def _vocabolario(indice):
    """Frasi riconoscibili -> (tipo, valore). A parita' di frase vince il
    tipo piu' specifico inserito per ultimo (provincia su nazione, ecc.)."""
    voci = {}
    for nome, codice in indice["nazione_per_nome"].items():
        voci[nome] = ("nazione", codice)
    for alias, nome in ALIAS_NAZIONI.items():
        codice = indice["nazione_per_nome"].get(nome)
        if codice:
            voci[alias] = ("nazione", codice)
    for nome, codice in indice["regione_per_nome"].items():
        voci[nome] = ("regione", codice)
    for alias, nome in ALIAS_REGIONI.items():
        codice = indice["regione_per_nome"].get(nome)
        if codice:
            voci[alias] = ("regione", codice)
    for nome, codice in indice["provincia_per_nome"].items():
        voci[nome] = ("provincia", codice)
    for alias, sigla in ALIAS_PROVINCE.items():
        codice = indice["provincia_per_sigla"].get(sigla)
        if codice:
            voci[alias] = ("provincia", codice)
    for alias, sigle in ALIAS_AREE.items():
        codici = tuple(
            indice["provincia_per_sigla"][s]
            for s in sigle
            if s in indice["provincia_per_sigla"]
        )
        if codici:
            voci[alias] = ("area", codici)
    for frase in TUTTA_ITALIA:
        voci[frase] = ("italia", None)
    for frase in MACRO_AREE:
        voci[frase] = ("macro", None)
    return voci


def _scomponi(pezzo, voci, indice, lunghezza_massima):
    """Riconosce le frasi note dentro un pezzo, cercando sempre la frase
    piu' lunga (cosi' "sud sardegna" batte "sud", "nord italia" batte
    "italia"). Ritorna `(voci_trovate, parole_sconosciute)`."""
    originali = [
        p for p in re.split(r"[^0-9A-Za-z]+", _senza_accenti(pezzo)) if p
    ]
    parole = [p.casefold() for p in originali]
    trovate, sconosciute = [], []
    i = 0
    while i < len(parole):
        for n in range(min(lunghezza_massima, len(parole) - i), 0, -1):
            voce = voci.get(" ".join(parole[i : i + n]))
            if voce:
                trovate.append(voce)
                i += n
                break
        else:
            parola = originali[i]
            # Sigla provincia: solo se nel testo ORIGINALE e' esattamente
            # due lettere maiuscole. Senza questo vincolo "pa", "si", "an",
            # "re", "co", "mo" farebbero strage di falsi positivi.
            if (
                len(parola) == 2
                and parola.isalpha()
                and parola.isupper()
                and parola in indice["provincia_per_sigla"]
            ):
                trovate.append(
                    ("provincia", indice["provincia_per_sigla"][parola])
                )
            elif parole[i] not in PAROLE_VUOTE:
                sconosciute.append(parole[i])
            i += 1
    return trovate, sconosciute


def match_testo(testo, indice):
    """Interpreta il vecchio testo libero.

    Ritorna `(province, nazioni, riconosciuti, non_riconosciuti)`, dove i
    primi due sono insiemi di codici e gli altri due liste di pezzi di
    testo, utili al report.

    Una regione citata insieme a una sua provincia (es. "LAZIO ROMA",
    "Puglia - Taranto") fa solo da contesto: vale la provincia. Citata da
    sola vale invece tutte le sue province.
    """
    province = set()
    nazioni = set()
    regioni = set()
    riconosciuti = []
    non_riconosciuti = []

    if not testo or not str(testo).strip():
        return province, nazioni, riconosciuti, non_riconosciuti

    voci = _vocabolario(indice)
    lunghezza_massima = max(len(frase.split()) for frase in voci)

    for grezzo in SEPARATORI.split(str(testo)):
        grezzo = grezzo.strip()
        trovate, sconosciute = _scomponi(
            grezzo, voci, indice, lunghezza_massima
        )
        if not trovate and not sconosciute:
            continue

        utili = [v for v in trovate if v[0] != "macro"]
        if sconosciute or len(utili) < len(trovate) or not utili:
            non_riconosciuti.append(grezzo)
        else:
            riconosciuti.append(grezzo)

        for tipo, valore in utili:
            if tipo == "provincia":
                province.add(valore)
            elif tipo == "area":
                province.update(valore)
            elif tipo == "regione":
                regioni.add(valore)
            elif tipo == "italia":
                nazione = indice["nazione_per_nome"].get("italia")
                province.update(
                    indice["province_per_nazione"].get(nazione, [])
                )
            elif valore in indice["nazioni_foglia"]:
                nazioni.add(valore)
            else:
                province.update(indice["province_per_nazione"].get(valore, []))

    regioni_contesto = {
        indice["regione_di_provincia"].get(codice) for codice in province
    }
    for regione in regioni - regioni_contesto:
        province.update(indice["province_per_regione"].get(regione, []))

    return province, nazioni, riconosciuti, non_riconosciuti


def espandi_zone(regole, indice):
    """Espande le regole INCLUDE/EXCLUDE di una o piu' zone.

    `regole` e' una lista di tuple
    `(rule_type, country_code, region_code, province_code)`.
    """
    include_p, include_n = set(), set()
    exclude_p, exclude_n = set(), set()

    for tipo, nazione, regione, provincia in regole:
        bersaglio_p, bersaglio_n = set(), set()
        if provincia:
            bersaglio_p.add(provincia)
        elif regione:
            bersaglio_p.update(indice["province_per_regione"].get(regione, []))
        elif nazione:
            figlie = indice["province_per_nazione"].get(nazione)
            if figlie:
                bersaglio_p.update(figlie)
            else:
                bersaglio_n.add(nazione)

        if tipo == "EXCLUDE":
            exclude_p |= bersaglio_p
            exclude_n |= bersaglio_n
        else:
            include_p |= bersaglio_p
            include_n |= bersaglio_n

    return include_p - exclude_p, include_n - exclude_n


def _chiave(valore):
    """Id geografico come UUID, sia dall'ORM sia da SQL diretto."""
    if valore is None:
        return None
    return valore if isinstance(valore, uuid.UUID) else uuid.UUID(str(valore))


def codici_per_id(nazioni, regioni, province):
    """Mappe id -> codice per nazioni, regioni e province.

    Gli argomenti sono righe `(id, code)` lette dal database. Le regole
    delle zone legacy possono puntare agli id delle fixture del catalogo
    geografico anche dove la geografia e' stata creata con altri id (dal
    vecchio `import_geography.py`): anche quegli id vengono risolti, per
    codice. A parita' di id vince la riga in tabella.
    """
    mappe = {
        "vendors.country": {},
        "vendors.region": {},
        "vendors.province": {},
    }
    fixture = carica_fixture(FIXTURE_ITALIA) + carica_fixture(FIXTURE_NAZIONI)
    for record in fixture:
        codice = record["fields"]["code"]
        mappe[record["model"]][_chiave(record["pk"])] = codice
    for modello, righe in (
        ("vendors.country", nazioni),
        ("vendors.region", regioni),
        ("vendors.province", province),
    ):
        for id_riga, codice in righe:
            mappe[modello][_chiave(id_riga)] = codice
    return {
        "nazioni": mappe["vendors.country"],
        "regioni": mappe["vendors.region"],
        "province": mappe["vendors.province"],
    }


def risolvi_regola(tipo, nazione_id, regione_id, provincia_id, codici):
    """Regola con id geografici -> regola con codici (None se ignoti)."""
    return (
        tipo,
        codici["nazioni"].get(_chiave(nazione_id)),
        codici["regioni"].get(_chiave(regione_id)),
        codici["province"].get(_chiave(provincia_id)),
    )


def calcola_copertura(zone, testo, indice):
    """Copertura di un fornitore: zone espanse piu' testo libero.

    `zone` e' una lista di `(nome_zona, regole)`, con le regole gia'
    risolte in codici. Una zona le cui regole non producono nulla (zona
    senza regole, o con riferimenti geografici irrisolvibili) viene
    interpretata dal suo nome.
    """
    province_zone, nazioni_zone = set(), set()
    riconosciuti, non_riconosciuti = [], []
    for nome, regole in zone:
        province, nazioni = espandi_zone(regole, indice)
        if not province and not nazioni:
            province, nazioni, ok, ko = match_testo(nome, indice)
            riconosciuti.extend(ok)
            non_riconosciuti.extend(ko)
        province_zone |= province
        nazioni_zone |= nazioni

    da_testo_p, da_testo_n, ok, ko = match_testo(testo, indice)
    return {
        "provinces": province_zone | da_testo_p,
        "countries": nazioni_zone | da_testo_n,
        "provinces_da_zone": province_zone,
        "countries_da_zone": nazioni_zone,
        "provinces_da_testo": da_testo_p,
        "countries_da_testo": da_testo_n,
        "riconosciuti": riconosciuti + ok,
        "non_riconosciuti": non_riconosciuti + ko,
    }


def carica_indice(apps):
    """Costruisce l'indice leggendo il catalogo geografico (3 query)."""
    Country = apps.get_model("vendors", "Country")
    Region = apps.get_model("vendors", "Region")
    Province = apps.get_model("vendors", "Province")

    return costruisci_indice(
        list(Country.objects.values_list("code", "name")),
        list(Region.objects.values_list("code", "name", "country__code")),
        list(Province.objects.values_list("code", "name", "region__code")),
    )


def travasa(apps, schema_editor):
    Vendor = apps.get_model("vendors", "Vendor")
    Country = apps.get_model("vendors", "Country")
    Region = apps.get_model("vendors", "Region")
    Province = apps.get_model("vendors", "Province")
    CompetenceZone = apps.get_model("vendors", "CompetenceZone")
    CompetenceZoneRule = apps.get_model("vendors", "CompetenceZoneRule")

    da_migrare = Vendor.objects.exclude(
        competences_zone__isnull=True, competence_zones__isnull=True
    ).exists()
    if not da_migrare:
        return

    if not Province.objects.exists():
        raise RuntimeError(
            "Catalogo geografico vuoto: la migrazione 0041_seed_geography "
            "deve essere stata applicata prima di questa."
        )

    indice = carica_indice(apps)
    codici = codici_per_id(
        Country.objects.values_list("id", "code"),
        Region.objects.values_list("id", "code"),
        Province.objects.values_list("id", "code"),
    )

    regole_per_zona = {}
    for (
        zona_id,
        tipo,
        naz,
        reg,
        prov,
    ) in CompetenceZoneRule.objects.values_list(
        "zone_id",
        "rule_type",
        "country_id",
        "region_id",
        "province_id",
    ):
        regole_per_zona.setdefault(zona_id, []).append(
            risolvi_regola(tipo, naz, reg, prov, codici)
        )
    nome_zona = dict(CompetenceZone.objects.values_list("id", "name"))

    id_provincia = dict(Province.objects.values_list("code", "id"))
    id_nazione = dict(Country.objects.values_list("code", "id"))

    LegameProvincia = Vendor.competence_provinces.through
    LegameNazione = Vendor.competence_countries.through
    legami_p, legami_n = [], []

    esaminati = 0
    senza_match = 0
    parziali = 0

    queryset = Vendor.objects.prefetch_related("competence_zones")
    for vendor in queryset.iterator(chunk_size=500):
        zone = [
            (nome_zona.get(z.pk, ""), regole_per_zona.get(z.pk, []))
            for z in vendor.competence_zones.all()
        ]
        copertura = calcola_copertura(zone, vendor.competences_zone, indice)

        aveva_dati = bool((vendor.competences_zone or "").strip()) or bool(
            zone
        )
        if aveva_dati:
            esaminati += 1
            if not copertura["provinces"] and not copertura["countries"]:
                senza_match += 1
            elif copertura["non_riconosciuti"]:
                parziali += 1

        for codice in copertura["provinces"]:
            if codice in id_provincia:
                legami_p.append(
                    LegameProvincia(
                        vendor_id=vendor.pk, province_id=id_provincia[codice]
                    )
                )
        for codice in copertura["countries"]:
            if codice in id_nazione:
                legami_n.append(
                    LegameNazione(
                        vendor_id=vendor.pk, country_id=id_nazione[codice]
                    )
                )

    # `ignore_conflicts` mappa su INSERT IGNORE (MySQL) e INSERT OR IGNORE
    # (SQLite): rende la migrazione ri-eseguibile a vuoto.
    LegameProvincia.objects.bulk_create(
        legami_p, batch_size=5000, ignore_conflicts=True
    )
    LegameNazione.objects.bulk_create(
        legami_n, batch_size=5000, ignore_conflicts=True
    )

    # Riepilogo nei log di deploy: resta una traccia dell'esito anche se
    # il report CSV non e' stato lanciato prima (vedi
    # data_migration_scripts/report_competence_zone_migration.py).
    print(
        f"Travaso zone di competenza: {esaminati} fornitori con "
        f"dati legacy, {senza_match} senza alcun match, {parziali} "
        f"parzialmente interpretati. Create {len(legami_p)} associazioni a "
        f"province e {len(legami_n)} a nazioni estere."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("vendors", "0042_vendor_competence_territories"),
    ]

    operations = [
        # Reverse noop: i campi legacy restano popolati fino alla
        # migrazione di rimozione, quindi tornare indietro non perde nulla.
        migrations.RunPython(travasa, migrations.RunPython.noop),
    ]
