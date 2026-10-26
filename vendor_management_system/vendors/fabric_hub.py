"""Anagrafica fornitori da FABRIC_HUB, letta via API DAB (sola lettura).

La ricerca "lente" del form fornitore interroga l'entità ``Fornitori_CF``
(vista ``CommonData_ClientiFornitori``) esposta da ``fulgardas``. Auth Entra ID
client-credentials, stesso schema di FAPP; config in ``FABRICHUB_*``.

DAB non supporta ``contains``: la ricerca per ragione sociale filtra in
memoria l'elenco dei fornitori attivi (~10k righe, in cache); codice, P.IVA e
codice fiscale usano invece ``$filter`` lato server.
"""

import time
import urllib.parse

import requests
from django.conf import settings

# La vista scrive la Società in maiuscolo; Vendor.EMBYON_COMPANY_CHOICES in
# CamelCase, e il form accetta solo quei valori.
COMPANY_LABELS = {
    "CMASRL": "CmaSrl",
    "EVIMED": "Evimed",
    "GSPROTEC": "GsProtec",
    "IGEAM": "Igeam",
    "SICURA": "Sicura",
}

ACTIVE_FILTER = "StatoFornitore eq 'ATTIVO'"
TIMEOUT = 30

# Cache per processo (nessuna dipendenza da Redis, assente su alcune VM).
_token_cache = {"value": None, "exp": 0.0}
_suppliers_cache = {"rows": None, "exp": 0.0}


def _get_token():
    now = time.time()
    if _token_cache["value"] and _token_cache["exp"] - 60 > now:
        return _token_cache["value"]
    client_id = settings.FABRICHUB_CLIENT_ID
    resp = requests.post(
        f"https://login.microsoftonline.com/{settings.FABRICHUB_TENANT_ID}"
        "/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": settings.FABRICHUB_CLIENT_SECRET,
            "scope": settings.FABRICHUB_SCOPE or f"api://{client_id}/.default",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    body = resp.json()
    _token_cache["value"] = body["access_token"]
    _token_cache["exp"] = now + int(body.get("expires_in", 3600))
    return _token_cache["value"]


def _headers():
    return {
        "Authorization": f"Bearer {_get_token()}",
        "X-MS-API-ROLE": settings.FABRICHUB_API_ROLE,
    }


def _quote(value):
    """Letterale OData: apici raddoppiati, per non uscire dalla stringa."""
    return "'" + value.replace("'", "''") + "'"


def _iter_entity(filter_expr, page_size=1000):
    """Righe dell'entità DAB, paginando via nextLink."""
    base = settings.FABRICHUB_BASE_URL.rstrip("/")
    url = f"{base}/api/{settings.FABRICHUB_SUPPLIERS_ENTITY}"
    # Il nome parametro deve restare "$filter" letterale: DAB risponde 400 se
    # è percent-encoded. Il valore invece va codificato (spazi, apici).
    value = urllib.parse.quote(filter_expr, safe="")
    query = f"$first={page_size}&$filter={value}"
    while url:
        resp = requests.get(
            f"{url}?{query}" if query else url,
            headers=_headers(),
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        yield from data.get("value", [])
        next_link = data.get("nextLink")
        # Il nextLink esce con http:// (hop interno) e include già i parametri.
        url = (
            next_link.replace("http://", "https://", 1) if next_link else None
        )
        query = ""


def _active_suppliers():
    now = time.time()
    if _suppliers_cache["rows"] is None or _suppliers_cache["exp"] <= now:
        _suppliers_cache["rows"] = list(_iter_entity(ACTIVE_FILTER))
        _suppliers_cache["exp"] = now + settings.FABRICHUB_CACHE_SECONDS
    return _suppliers_cache["rows"]


def _padded_code(digits):
    # CODCONTO è la lettera F più il numero allineato a destra su 6 caratteri
    # ("F   463", "F 17777").
    return "F" + str(int(digits)).rjust(6)


def _normalize(row):
    company = (row.get("Ditta") or "").strip()
    return {
        "old_code": " ".join((row.get("CODCONTO") or "").split()),
        "company": COMPANY_LABELS.get(company.upper(), company),
        "name": (row.get("DSCCONTO1") or "").strip(),
        "vat_number": (row.get("PARTITAIVA") or "").strip(),
        "fiscal_code": (row.get("CODFISCALE") or "").strip(),
        "province": (row.get("PROVINCIA") or "").strip(),
        "status": (row.get("StatoFornitore") or "").strip(),
        "address": (row.get("INDIRIZZO") or "").strip(),
        "postal_code": (row.get("CAP") or "").strip(),
        "city": (row.get("LOCALITA") or "").strip(),
        "email": (row.get("Mail") or "").strip(),
    }


def search_suppliers(
    *, name="", old_code="", vat="", fiscal_code="", limit=200
):
    """Cerca fornitori attivi; usa un solo criterio, in ordine di priorità.

    Ritorna dict con chiavi: company, old_code, name, vat_number, fiscal_code,
    province, status, address, postal_code, city, email. Il chiamante valida
    che ci sia almeno un criterio.
    """
    if name:
        needle = name.casefold()
        rows = [
            r
            for r in _active_suppliers()
            if needle in (r.get("DSCCONTO1") or "").casefold()
        ]
    elif old_code:
        digits = "".join(ch for ch in old_code if ch.isdigit())
        if digits:
            criterion = f"CODCONTO eq {_quote(_padded_code(digits))}"
            rows = list(_iter_entity(f"{ACTIVE_FILTER} and {criterion}"))
        else:
            wanted = old_code.replace(" ", "").upper()
            rows = [
                r
                for r in _active_suppliers()
                if (r.get("CODCONTO") or "").replace(" ", "").upper() == wanted
            ]
    elif vat:
        rows = list(
            _iter_entity(f"{ACTIVE_FILTER} and PARTITAIVA eq {_quote(vat)}")
        )
    elif fiscal_code:
        rows = list(
            _iter_entity(
                f"{ACTIVE_FILTER} and CODFISCALE eq {_quote(fiscal_code)}"
            )
        )
    else:
        rows = []

    results = [_normalize(r) for r in rows]
    results.sort(key=lambda r: r["name"].casefold())
    return results[:limit]
