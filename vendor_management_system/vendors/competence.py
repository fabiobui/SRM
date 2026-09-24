"""Copertura territoriale dei fornitori - logica condivisa.

Unico punto di verita' per admin, portale fornitori, dashboard, export e
filtri. Tenere qui la logica evita la duplicazione che affligge gia'
`static/vendors/js/dashboard.js`, dove il predicato di filtro e' ripetuto
una decina di volte.

Modello dei dati: la copertura di un fornitore e' l'insieme delle sue
`competence_provinces` (province italiane) piu' le sue
`competence_countries` (nazioni estere, che a catalogo non hanno
regioni/province). **La copertura di una regione non e' memorizzata: e'
derivata**, e una regione risulta coperta per intero quando lo sono tutte
le sue province. Cosi' non esistono due fonti in contraddizione.

Identificatori: ovunque si usano i **codici** (`MI`, `LOM`, `FR`), non gli
UUID - sono leggibili nel diff JSON delle proposte di modifica del portale
e nella querystring dei filtri, e sono molto piu' compatti nel payload
della dashboard. Attenzione: `FR` e' sia la Francia (ISO) sia Frosinone
(sigla), quindi province e nazioni viaggiano sempre in chiavi o parametri
distinti, mai in un unico elenco.
"""

from django.db.models import Count, Prefetch, Q

from vendor_management_system.vendors.models import Country, Province, Region

# Sentinella "copre tutto il territorio": evita di serializzare 107 sigle
# per ogni fornitore nel payload della dashboard.
TUTTE = "*"


# --------------------------------------------------------------------------
# Catalogo geografico
# --------------------------------------------------------------------------


def leaf_countries_qs():
    """Nazioni selezionabili solo a livello nazione (senza regioni).

    La regola e' generica - "nazione senza regioni a catalogo" - e non
    hardcodata sull'Italia: se un domani si seminassero le regioni di
    un'altra nazione, quella diventerebbe navigabile da sola.
    """
    return Country.objects.filter(is_active=True, regions__isnull=True)


def geo_maps():
    """Indici in memoria del catalogo geografico attivo (2 query).

    Nessuna cache: il costo e' trascurabile e una cache si sporcherebbe
    appena un admin modifica una provincia dall'admin di Django.
    """
    province = list(
        Province.objects.filter(is_active=True)
        .select_related("region__country")
        .order_by("sort_order", "name")
    )
    nazioni = list(
        Country.objects.filter(is_active=True)
        .prefetch_related("regions")
        .order_by("sort_order", "name")
    )

    province_per_regione = {}
    regione_di = {}
    nome_provincia = {}
    for prov in province:
        reg = prov.region.code
        province_per_regione.setdefault(reg, []).append(prov.code)
        regione_di[prov.code] = reg
        nome_provincia[prov.code] = prov.name

    nome_regione = {}
    nazione_di_regione = {}
    regioni_per_nazione = {}
    for naz in nazioni:
        regioni_attive = [r for r in naz.regions.all() if r.is_active]
        for reg in sorted(
            regioni_attive, key=lambda r: (r.sort_order, r.name)
        ):
            nome_regione[reg.code] = reg.name
            nazione_di_regione[reg.code] = naz.code
            regioni_per_nazione.setdefault(naz.code, []).append(reg.code)

    return {
        "province_per_regione": province_per_regione,
        "regione_di": regione_di,
        "nome_provincia": nome_provincia,
        "nome_regione": nome_regione,
        "nazione_di_regione": nazione_di_regione,
        "regioni_per_nazione": regioni_per_nazione,
        "nome_nazione": {n.code: n.name for n in nazioni},
        "nazioni_ordinate": [n.code for n in nazioni],
        "tutte_le_province": {p.code for p in province},
    }


def geo_tree_data():
    """Albero Nazione -> Regione -> Provincia per il selettore.

    Renderizzato server-side dal widget: sono ~157 nodi in 2 query, un
    round-trip AJAX costerebbe piu' di quanto farebbe risparmiare.
    """
    nazioni = (
        Country.objects.filter(is_active=True)
        .order_by("sort_order", "name")
        .prefetch_related(
            Prefetch(
                "regions",
                queryset=Region.objects.filter(is_active=True)
                .order_by("sort_order", "name")
                .prefetch_related(
                    Prefetch(
                        "provinces",
                        queryset=Province.objects.filter(
                            is_active=True
                        ).order_by("sort_order", "name"),
                    )
                ),
            )
        )
    )

    albero = []
    for naz in nazioni:
        regioni = [
            {
                "code": reg.code,
                "name": reg.name,
                "provinces": [
                    {"code": prov.code, "name": prov.name}
                    for prov in reg.provinces.all()
                ],
            }
            for reg in naz.regions.all()
        ]
        albero.append(
            {
                "code": naz.code,
                "name": naz.name,
                "leaf": not regioni,
                "regions": regioni,
            }
        )
    return albero


# --------------------------------------------------------------------------
# Lettura della copertura di un fornitore
# --------------------------------------------------------------------------


def prefetch_competence(queryset):
    """Aggiunge il prefetch della copertura territoriale.

    Da usare ovunque si iteri su piu' fornitori leggendone le zone. Nel
    loop poi va usato `list(vendor.competence_provinces.all())` e **mai**
    `.filter()` sul related manager, che bypasserebbe questa cache e
    reintrodurrebbe un N+1.
    """
    return queryset.prefetch_related(
        Prefetch(
            "competence_provinces",
            queryset=Province.objects.select_related("region__country"),
        ),
        "competence_countries",
    )


def current_selection(vendor):
    """Copertura salvata, come codici: `{"provinces": [...], ...}`.

    Niente sentinella: e' la forma usata dal widget e dalle proposte di
    modifica, dove serve l'elenco esatto.
    """
    return {
        "provinces": sorted(p.code for p in vendor.competence_provinces.all()),
        "countries": sorted(c.code for c in vendor.competence_countries.all()),
    }


def vendor_competence_codes(vendor, geo=None):
    """Copertura compattata per il payload JSON della dashboard.

    Applica la sentinella `TUTTE`: un fornitore che copre tutta l'Italia
    pesa una trentina di byte invece di ~0,7 KB. Le regioni sono derivate
    con la regola "almeno una provincia coperta", **la stessa** usata
    dall'aggregazione `by_region`: se le due divergessero, cliccando una
    barra da 12 l'utente vedrebbe 9 righe.
    """
    geo = geo or geo_maps()
    province = sorted(p.code for p in vendor.competence_provinces.all())
    nazioni = sorted(c.code for c in vendor.competence_countries.all())

    tutte = geo["tutte_le_province"]
    if tutte and set(province) >= tutte:
        return {
            "provinces": [TUTTE],
            "regions": [TUTTE],
            "countries": nazioni,
        }

    regioni = sorted(
        {geo["regione_di"][c] for c in province if c in geo["regione_di"]}
    )
    return {"provinces": province, "regions": regioni, "countries": nazioni}


def region_coverage(province_codes, geo=None):
    """Stato tri-stato di ogni regione: `full`, `partial` o `none`.

    E' la regola che il widget replica lato client per le checkbox
    `indeterminate`; tenerla anche qui la rende testabile in Python.
    """
    geo = geo or geo_maps()
    selezionate = set(province_codes)
    stato = {}
    for reg, province in geo["province_per_regione"].items():
        coperte = selezionate.intersection(province)
        if not coperte:
            stato[reg] = "none"
        elif len(coperte) == len(province):
            stato[reg] = "full"
        else:
            stato[reg] = "partial"
    return stato


# --------------------------------------------------------------------------
# Riepilogo leggibile
# --------------------------------------------------------------------------


def summarize_selection(province_codes, country_codes, geo=None):
    """Riepilogo leggibile, una riga per nazione.

    Esempi:
        "Italia: tutte le regioni (107 province)"
        "Italia - Lombardia (tutte), Emilia-Romagna: Ravenna, Rimini"
        "Estero: Francia, Germania"

    Prende codici e non istanze perche' deve funzionare anche sugli
    elenchi congelati dentro `VendorChangeRequest.changes`, dove il
    fornitore vivo puo' nel frattempo essere cambiato.
    """
    geo = geo or geo_maps()
    selezionate = {c for c in province_codes if c in geo["regione_di"]}
    stato = region_coverage(selezionate, geo)
    righe = []

    for naz in geo["nazioni_ordinate"]:
        regioni = geo["regioni_per_nazione"].get(naz)
        if not regioni:
            continue
        toccate = [r for r in regioni if stato.get(r, "none") != "none"]
        if not toccate:
            continue

        nome_naz = geo["nome_nazione"][naz]
        coperte_qui = [
            p
            for r in regioni
            for p in geo["province_per_regione"].get(r, [])
            if p in selezionate
        ]
        if all(stato.get(r) == "full" for r in regioni):
            righe.append(
                f"{nome_naz}: tutte le regioni ({len(coperte_qui)} province)"
            )
            continue

        pezzi = []
        for reg in toccate:
            nome_reg = geo["nome_regione"][reg]
            if stato[reg] == "full":
                pezzi.append(f"{nome_reg} (tutte)")
            else:
                nomi = [
                    geo["nome_provincia"][p]
                    for p in geo["province_per_regione"][reg]
                    if p in selezionate
                ]
                pezzi.append(f"{nome_reg}: {', '.join(nomi)}")
        righe.append(f"{nome_naz} - {', '.join(pezzi)}")

    estere_scelte = set(country_codes)
    estere = [
        geo["nome_nazione"][c]
        for c in geo["nazioni_ordinate"]
        if c in estere_scelte and c in geo["nome_nazione"]
    ]
    if estere:
        righe.append(f"Estero: {', '.join(estere)}")

    return righe


def format_selection(province_codes, country_codes, geo=None):
    """Versione monoriga di `summarize_selection`, per diff e colonne."""
    righe = summarize_selection(province_codes, country_codes, geo)
    return "; ".join(righe) if righe else "—"


def competence_summary(vendor, geo=None):
    """Riepilogo monoriga della copertura salvata di un fornitore."""
    selezione = current_selection(vendor)
    return format_selection(
        selezione["provinces"], selezione["countries"], geo
    )


# --------------------------------------------------------------------------
# Scrittura
# --------------------------------------------------------------------------


def set_vendor_competence(vendor, *, province_codes, country_codes):
    """Sostituisce la copertura del fornitore. Unico punto di scrittura.

    E' **tollerante**: i codici sconosciuti o non piu' attivi vengono
    scartati in silenzio. Serve all'approvazione delle proposte di
    modifica del portale, dove i codici sono stati congelati al momento
    della proposta e nel frattempo una provincia puo' essere stata
    disattivata - non e' un motivo per far fallire l'approvazione. La
    validazione stretta dell'input utente sta invece nel form
    (`CompetenceAreaField.clean`).

    Scarta anche le nazioni non foglia: l'Italia non deve mai finire in
    `competence_countries`, altrimenti ci sarebbero due verita' in
    contraddizione sulla copertura italiana.
    """
    province = Province.objects.filter(
        is_active=True, code__in=list(province_codes or [])
    )
    nazioni = leaf_countries_qs().filter(code__in=list(country_codes or []))
    vendor.competence_provinces.set(province)
    vendor.competence_countries.set(nazioni)


# --------------------------------------------------------------------------
# Interrogazione: filtri e aggregazioni
# --------------------------------------------------------------------------


def filter_by_competence(
    queryset, *, countries=None, regions=None, provinces=None
):
    """Filtra i fornitori per copertura territoriale, per codice.

    Il filtro per nazione copre **entrambi i lati**: sia i fornitori che
    hanno quella nazione fra le estere, sia quelli che ne coprono delle
    province (e' il caso dell'Italia, che non sta mai fra le estere).
    """
    if not (countries or regions or provinces):
        return queryset

    if countries:
        queryset = queryset.filter(
            Q(competence_countries__code__in=countries)
            | Q(competence_provinces__region__country__code__in=countries)
        )
    if regions:
        queryset = queryset.filter(
            competence_provinces__region__code__in=regions
        )
    if provinces:
        queryset = queryset.filter(competence_provinces__code__in=provinces)

    # Obbligatorio: senza, un fornitore su 12 province lombarde comparirebbe
    # 12 volte filtrando per la Lombardia.
    return queryset.distinct()


def competence_aggregations():
    """Conteggi per regione, provincia e nazione estera di competenza.

    `distinct=True` non e' opzionale su `by_region`: la catena
    Region -> Province -> M2M -> Vendor moltiplicherebbe altrimenti un
    fornitore per ogni sua provincia nella regione.
    """
    regioni = (
        Region.objects.filter(is_active=True)
        .annotate(count=Count("provinces__competent_vendors", distinct=True))
        .filter(count__gt=0)
        .order_by("-count", "name")
    )
    province = (
        Province.objects.filter(is_active=True)
        .select_related("region")
        .annotate(count=Count("competent_vendors", distinct=True))
        .filter(count__gt=0)
        .order_by("-count", "name")
    )
    nazioni = (
        leaf_countries_qs()
        .annotate(count=Count("competent_vendors", distinct=True))
        .filter(count__gt=0)
        .order_by("-count", "name")
    )

    return {
        "by_region": [
            {"region": r.name, "code": r.code, "count": r.count}
            for r in regioni
        ],
        # `region`/`region_name` servono al filtro a cascata della
        # dashboard: deselezionando una regione vanno tolte anche le sue
        # province dai filtri attivi.
        "by_province": [
            {
                "province": p.name,
                "code": p.code,
                "region": p.region.code,
                "region_name": p.region.name,
                "count": p.count,
            }
            for p in province
        ],
        "by_competence_country": [
            {"country": n.name, "code": n.code, "count": n.count}
            for n in nazioni
        ],
    }
