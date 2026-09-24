"""Travasa le vecchie zone di competenza nei nuovi campi territoriali.

Due sorgenti, unite (mai una che sostituisce l'altra):

1. Le `CompetenceZone` assegnate al fornitore, espanse applicando le
   regole INCLUDE meno quelle EXCLUDE.
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

from django.db import migrations

# Sinonimi che la sola normalizzazione non riconcilia.
ALIAS_REGIONI = {
    "sudtirol": "trentino alto adige",
    "sud tirol": "trentino alto adige",
    "alto adige": "trentino alto adige",
    "val d aosta": "valle d aosta",
    "friuli": "friuli venezia giulia",
    "emilia": "emilia romagna",
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

SEPARATORI = re.compile(r"[,;/|+]| e | - | ed ")


def normalizza(testo):
    """Minuscolo, senza accenti, senza punteggiatura, spazi collassati."""
    if not testo:
        return ""
    decomposto = unicodedata.normalize("NFKD", str(testo))
    senza_accenti = "".join(
        c for c in decomposto if not unicodedata.combining(c)
    )
    solo_alfanumerico = re.sub(r"[^0-9a-zA-Z]+", " ", senza_accenti)
    return " ".join(solo_alfanumerico.split()).casefold()


def _spoglia_prefissi(token):
    """Toglie "provincia di", "prov.", "regione", "zona" dal token."""
    for prefisso in (
        "provincia di ",
        "provincia ",
        "prov di ",
        "prov ",
        "regione ",
        "zona ",
        "area ",
    ):
        if token.startswith(prefisso):
            return token[len(prefisso) :].strip()
    return token


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
        "province_per_regione": province_per_regione,
        "province_per_nazione": province_per_nazione,
        "nazioni_foglia": {
            c for c, _n in nazioni if c not in set(regione_di_nazione.values())
        },
    }


def match_testo(testo, indice):
    """Interpreta il vecchio testo libero.

    Ritorna `(province, nazioni, riconosciuti, non_riconosciuti)`, dove i
    primi due sono insiemi di codici e gli altri due liste di token, utili
    al report.
    """
    province = set()
    nazioni = set()
    riconosciuti = []
    non_riconosciuti = []

    if not testo or not str(testo).strip():
        return province, nazioni, riconosciuti, non_riconosciuti

    for grezzo in SEPARATORI.split(str(testo)):
        grezzo = grezzo.strip()
        if not grezzo:
            continue
        token = _spoglia_prefissi(normalizza(grezzo))
        if not token:
            continue
        token = ALIAS_REGIONI.get(token, token)

        if token in MACRO_AREE:
            non_riconosciuti.append(grezzo)
            continue

        if token in TUTTA_ITALIA:
            nazione = indice["nazione_per_nome"].get("italia")
            if nazione:
                province.update(
                    indice["province_per_nazione"].get(nazione, [])
                )
                riconosciuti.append(grezzo)
            else:
                non_riconosciuti.append(grezzo)
            continue

        codice_regione = indice["regione_per_nome"].get(token)
        if codice_regione:
            province.update(
                indice["province_per_regione"].get(codice_regione, [])
            )
            riconosciuti.append(grezzo)
            continue

        codice_provincia = indice["provincia_per_nome"].get(token)
        if codice_provincia:
            province.add(codice_provincia)
            riconosciuti.append(grezzo)
            continue

        # Sigla provincia: solo se nel testo ORIGINALE il token e'
        # esattamente due lettere maiuscole. Senza questo vincolo "pa",
        # "si", "an", "re", "co", "mo" farebbero strage di falsi positivi
        # su parole comuni.
        if (
            len(grezzo) == 2
            and grezzo.isalpha()
            and grezzo.isupper()
            and grezzo in indice["provincia_per_sigla"]
        ):
            province.add(indice["provincia_per_sigla"][grezzo])
            riconosciuti.append(grezzo)
            continue

        codice_nazione = indice["nazione_per_nome"].get(token)
        if codice_nazione:
            if codice_nazione in indice["nazioni_foglia"]:
                nazioni.add(codice_nazione)
            else:
                province.update(
                    indice["province_per_nazione"].get(codice_nazione, [])
                )
            riconosciuti.append(grezzo)
            continue

        non_riconosciuti.append(grezzo)

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


def calcola_copertura(vendor, regole_per_zona, indice):
    """Copertura di un fornitore: zone espanse piu' testo libero."""
    regole = []
    for zona in vendor.competence_zones.all():
        regole.extend(regole_per_zona.get(zona.pk, []))
    province, nazioni = espandi_zone(regole, indice)

    da_testo_p, da_testo_n, riconosciuti, non_riconosciuti = match_testo(
        vendor.competences_zone, indice
    )
    return {
        "provinces": province | da_testo_p,
        "countries": nazioni | da_testo_n,
        "provinces_da_zone": province,
        "countries_da_zone": nazioni,
        "riconosciuti": riconosciuti,
        "non_riconosciuti": non_riconosciuti,
    }


def travasa(apps, schema_editor):
    Vendor = apps.get_model("vendors", "Vendor")
    Province = apps.get_model("vendors", "Province")
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
        "country__code",
        "region__code",
        "province__code",
    ):
        regole_per_zona.setdefault(zona_id, []).append((tipo, naz, reg, prov))

    id_provincia = dict(Province.objects.values_list("code", "id"))
    Country = apps.get_model("vendors", "Country")
    id_nazione = dict(Country.objects.values_list("code", "id"))

    LegameProvincia = Vendor.competence_provinces.through
    LegameNazione = Vendor.competence_countries.through
    legami_p, legami_n = [], []

    esaminati = 0
    senza_match = 0
    parziali = 0

    queryset = Vendor.objects.prefetch_related("competence_zones")
    for vendor in queryset.iterator(chunk_size=500):
        copertura = calcola_copertura(vendor, regole_per_zona, indice)

        aveva_dati = bool((vendor.competences_zone or "").strip()) or bool(
            copertura["provinces_da_zone"] or copertura["countries_da_zone"]
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
