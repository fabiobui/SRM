import requests

API_KEY = "69fc85c1e4017aa3780ad6dc"
BASE_URL = "https://company.openapi.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# --- Ricerca azienda per nome ---
def cerca_azienda(nome, provincia=None, forma=None):
    params = {
        "dryRun": 0,
        "dataEnrichment": "name",
        "autocomplete": nome,
        "activityStatus": "ATTIVA",
        "limit": 30
    }
    if provincia and len(provincia) >= 2:
        params["province"] = provincia[:2].upper()
    if forma and forma[:2].upper() in ("SP", "SR"):
        params["legalFormCode"] = forma[:2].upper()

    r = requests.get(f"{BASE_URL}/IT-search", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json().get("data", [])


# --- Recupero indirizzo per ID azienda ---
def get_address(company_id):
    r = requests.get(f"{BASE_URL}/IT-address/{company_id}", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    if data.get("success") and data.get("data"):
        office = data["data"][0]["address"]["registeredOffice"]
        return {
            "indirizzo":  f"{office.get('toponym', '')} {office.get('street', '')}".strip(),
            "numcivico":  office.get("streetNumber"),
            "città":      office.get("town"),
            "cap":        office.get("zipCode"),
            "provincia":  office.get("province"),
            "regione":    office.get("region", {}).get("description"),
            "nazione":    "IT"
        }
    return None


# Esempio d'uso
aziende = cerca_azienda("AUDIRAI", provincia="MI")
for a in aziende:
    print(a["id"], a["companyName"], a.get("vatCode"))

if aziende:
    indirizzo = get_address(aziende[0]["id"])
    print(indirizzo)
