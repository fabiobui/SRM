"""Semina il catalogo geografico (Nazioni, Regioni, Province).

Sorgenti: le fixture ``geography_italy.json`` (l'Italia con le sue 20
regioni e 107 province) e ``geography_countries.json`` (le altre nazioni,
che a catalogo non hanno articolazione interna). Entrambe portano PK
deterministici, così gli id restano stabili fra gli ambienti.

Perché non ``loaddata``: quello fa un UPSERT completo e sovrascriverebbe
``is_active``/``sort_order`` eventualmente personalizzati da un admin. Qui
si crea solo ciò che manca, riconoscendo le righe esistenti dal ``code``
(che è ``unique`` su tutti e tre i modelli).

Le funzioni ricevono le classi modello come argomento invece di importarle:
serve alla data migration che semina la geografia, la quale deve usare i
propri modelli storici (``apps.get_model``). Il management command
``seed_geography`` passa invece i modelli veri.

La geografia è un prerequisito delle zone di competenza dei
fornitori: senza queste righe il selettore territoriale è vuoto.
"""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

FIXTURE_ITALIA = "geography_italy.json"
FIXTURE_NAZIONI = "geography_countries.json"


def carica_fixture(nome):
    """Ritorna la lista di record di una fixture del catalogo geografico."""
    percorso = FIXTURES_DIR / nome
    with percorso.open(encoding="utf-8") as fh:
        return json.load(fh)


def _righe(dati, modello):
    """Filtra i record della fixture per nome di modello."""
    return [r for r in dati if r["model"] == modello]


def _crea(model, code, defaults, create_only, conteggi, chiave):
    """Crea la riga se manca; altrimenti la lascia (quasi) stare.

    Con ``create_only=True`` non tocca nulla di esistente: è la modalità
    usata ad ogni deploy.

    Senza il flag riallinea alla fixture due cose soltanto:

    * il ``name``;
    * il ``sort_order``, **ma solo se è ancora quello di default del
      modello**, cioè non è mai stato impostato da nessuno. Serve ai
      database in cui la geografia era stata creata dal vecchio script
      ``import_geography.py``, che per regioni e province non lo
      valorizzava: lì tutte le righe hanno il default e l'ordinamento
      ripiegherebbe su alfabetico, diverso da quello di un database
      nuovo. Un valore diverso dal default è una scelta di un admin e
      non viene mai sovrascritto.

    ``is_active`` non si tocca in nessun caso.
    """
    obj, creato = model.objects.get_or_create(code=code, defaults=defaults)
    if creato:
        conteggi[chiave]["creati"] += 1
        return obj

    conteggi[chiave]["esistenti"] += 1
    if create_only:
        return obj

    da_aggiornare = []
    if obj.name != defaults["name"]:
        obj.name = defaults["name"]
        da_aggiornare.append("name")

    default_modello = model._meta.get_field("sort_order").default
    if obj.sort_order == default_modello != defaults["sort_order"]:
        obj.sort_order = defaults["sort_order"]
        da_aggiornare.append("sort_order")

    if da_aggiornare:
        obj.save(update_fields=da_aggiornare)
        conteggi[chiave]["aggiornati"] += 1
    return obj


def seed_geography(
    country_model,
    region_model,
    province_model,
    *,
    create_only=False,
):
    """Semina nazioni, regioni e province. Idempotente.

    Ritorna un dizionario di conteggi per livello, nella forma
    ``{"nazioni": {"creati": n, "esistenti": n, "aggiornati": n}, ...}``.
    """
    conteggi = {
        chiave: {"creati": 0, "esistenti": 0, "aggiornati": 0}
        for chiave in ("nazioni", "regioni", "province")
    }

    dati = carica_fixture(FIXTURE_ITALIA) + carica_fixture(FIXTURE_NAZIONI)

    # Le fixture referenziano il padre tramite il PK della fixture stessa.
    # Su un database dove le righe esistono già con un altro id (creato a
    # suo tempo da import_geography.py) quel PK non corrisponde, quindi si
    # risolve il padre passando per l'oggetto effettivamente in tabella.
    nazione_per_pk = {}
    regione_per_pk = {}

    for record in _righe(dati, "vendors.country"):
        campi = record["fields"]
        nazione_per_pk[record["pk"]] = _crea(
            country_model,
            campi["code"],
            {
                "id": record["pk"],
                "name": campi["name"],
                "is_active": campi["is_active"],
                "sort_order": campi["sort_order"],
            },
            create_only,
            conteggi,
            "nazioni",
        )

    for record in _righe(dati, "vendors.region"):
        campi = record["fields"]
        regione_per_pk[record["pk"]] = _crea(
            region_model,
            campi["code"],
            {
                "id": record["pk"],
                "name": campi["name"],
                "country": nazione_per_pk[campi["country"]],
                "is_active": campi["is_active"],
                "sort_order": campi["sort_order"],
            },
            create_only,
            conteggi,
            "regioni",
        )

    for record in _righe(dati, "vendors.province"):
        campi = record["fields"]
        _crea(
            province_model,
            campi["code"],
            {
                "id": record["pk"],
                "name": campi["name"],
                "region": regione_per_pk[campi["region"]],
                "is_active": campi["is_active"],
                "sort_order": campi["sort_order"],
            },
            create_only,
            conteggi,
            "province",
        )

    return conteggi
