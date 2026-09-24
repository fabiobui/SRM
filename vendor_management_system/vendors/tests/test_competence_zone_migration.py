"""Funzioni di travaso delle vecchie zone di competenza.

I test veloci girano con `--no-migrations`, quindi la data migration non
viene mai eseguita da loro: la sua correttezza si verifica qui, sulle
funzioni pure, piu' con la suite Docker che rigioca tutta la cronologia.

Le funzioni vivono dentro il file della migrazione (deve restare
rigiocabile anche dopo la rimozione dello stack legacy), da cui il
caricamento con `importlib`: `import` non accetta nomi che iniziano per
cifra.
"""

import importlib

import pytest

migrazione = importlib.import_module(
    "vendor_management_system.vendors.migrations.0043_migrate_competence_zones"
)

NAZIONI = [("IT", "Italia"), ("FR", "Francia"), ("DE", "Germania")]
REGIONI = [
    ("LOM", "Lombardia", "IT"),
    ("EMR", "Emilia-Romagna", "IT"),
    ("VDA", "Valle d'Aosta", "IT"),
    ("TAA", "Trentino-Alto Adige", "IT"),
]
PROVINCE = [
    ("MI", "Milano", "LOM"),
    ("BG", "Bergamo", "LOM"),
    ("RA", "Ravenna", "EMR"),
    ("RN", "Rimini", "EMR"),
    ("AO", "Aosta", "VDA"),
    ("TN", "Trento", "TAA"),
]


@pytest.fixture
def indice():
    return migrazione.costruisci_indice(NAZIONI, REGIONI, PROVINCE)


def _match(testo, indice):
    province, nazioni, _ok, ko = migrazione.match_testo(testo, indice)
    return province, nazioni, ko


# --------------------------------------------------------------------------
# Normalizzazione
# --------------------------------------------------------------------------


def test_normalizza_toglie_accenti_e_punteggiatura():
    assert migrazione.normalizza("Emilia-Romagna") == "emilia romagna"
    assert migrazione.normalizza("Valle d'Aosta") == "valle d aosta"
    assert migrazione.normalizza("  FORLI'  ") == "forli"


def test_normalizza_accetta_vuoto():
    assert migrazione.normalizza(None) == ""
    assert migrazione.normalizza("") == ""


# --------------------------------------------------------------------------
# Match del testo libero
# --------------------------------------------------------------------------


def test_nome_regione_espande_le_sue_province(indice):
    province, _n, ko = _match("Lombardia", indice)

    assert province == {"MI", "BG"}
    assert ko == []


def test_regione_con_grafia_diversa(indice):
    """Il trattino e l'apostrofo spariscono nella normalizzazione, quindi
    le due grafie che convivono nel repo fanno match entrambe."""
    assert _match("Emilia Romagna", indice)[0] == {"RA", "RN"}
    assert _match("Emilia-Romagna", indice)[0] == {"RA", "RN"}
    assert _match("Valle d'Aosta", indice)[0] == {"AO"}
    assert _match("Trentino Alto Adige", indice)[0] == {"TN"}


def test_alias_regione(indice):
    assert _match("Sudtirol", indice)[0] == {"TN"}
    assert _match("Friuli", indice)[1] == set()


def test_nome_provincia(indice):
    assert _match("Ravenna", indice)[0] == {"RA"}


def test_prefissi_ignorati(indice):
    assert _match("Provincia di Milano", indice)[0] == {"MI"}
    assert _match("Regione Lombardia", indice)[0] == {"MI", "BG"}


def test_italia_espande_tutte_le_province(indice):
    province, _n, ko = _match("Italia", indice)

    assert province == {"MI", "BG", "RA", "RN", "AO", "TN"}
    assert ko == []


def test_nazione_estera_resta_a_livello_nazione(indice):
    province, nazioni, _ko = _match("Francia", indice)

    assert province == set()
    assert nazioni == {"FR"}


def test_elenco_con_separatori_misti(indice):
    province, nazioni, ko = _match(
        "Lombardia, Ravenna; Francia / Rimini", indice
    )

    assert province == {"MI", "BG", "RA", "RN"}
    assert nazioni == {"FR"}
    assert ko == []


def test_separatore_e_testuale(indice):
    assert _match("Milano e Bergamo", indice)[0] == {"MI", "BG"}


def test_sigla_riconosciuta_solo_se_maiuscola(indice):
    """Senza questo vincolo "pa", "si", "re", "co" farebbero strage di
    falsi positivi su parole comuni."""
    assert _match("MI", indice)[0] == {"MI"}
    assert _match("mi", indice)[0] == set()
    assert _match("Mi", indice)[0] == set()


def test_macro_aree_non_vengono_indovinate(indice):
    """ "Nord" puo' essere nord-ovest, nord-est o entrambi: si segnala nel
    report e si risolve a mano."""
    province, nazioni, ko = _match("Nord Italia", indice)

    assert province == set()
    assert nazioni == set()
    assert ko == ["Nord Italia"]


def test_token_sconosciuto_finisce_fra_i_non_riconosciuti(indice):
    province, _n, ko = _match("Lombardia, Pianeta Marte", indice)

    assert province == {"MI", "BG"}
    assert ko == ["Pianeta Marte"]


def test_testo_vuoto(indice):
    assert _match("", indice) == (set(), set(), [])
    assert _match(None, indice) == (set(), set(), [])


# --------------------------------------------------------------------------
# Espansione delle zone nominate
# --------------------------------------------------------------------------


def test_include_nazione_meno_exclude_regione(indice):
    regole = [
        ("INCLUDE", "IT", None, None),
        ("EXCLUDE", None, "EMR", None),
    ]

    province, nazioni = migrazione.espandi_zone(regole, indice)

    assert province == {"MI", "BG", "AO", "TN"}
    assert nazioni == set()


def test_include_regione_piu_provincia(indice):
    regole = [
        ("INCLUDE", None, "LOM", None),
        ("INCLUDE", None, None, "RA"),
    ]

    province, _n = migrazione.espandi_zone(regole, indice)

    assert province == {"MI", "BG", "RA"}


def test_exclude_provincia_singola(indice):
    regole = [
        ("INCLUDE", None, "LOM", None),
        ("EXCLUDE", None, None, "BG"),
    ]

    assert migrazione.espandi_zone(regole, indice)[0] == {"MI"}


def test_nazione_estera_resta_nazione_anche_nelle_regole(indice):
    regole = [("INCLUDE", "DE", None, None)]

    province, nazioni = migrazione.espandi_zone(regole, indice)

    assert province == set()
    assert nazioni == {"DE"}


def test_nessuna_regola_nessuna_copertura(indice):
    assert migrazione.espandi_zone([], indice) == (set(), set())
