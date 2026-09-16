"""
Script manuale per testare a mano una connessione LDAPS contro l'Active
Directory ('sicura.loc'). Non è un test automatico (non lo esegue pytest) e
non va lanciato in CI: serve solo per il debug interattivo di un
amministratore, dentro la venv del progetto.

Nessuna credenziale va MAI hardcoded qui: host, utente e password si leggono
da variabili d'ambiente. Esempio d'uso (PowerShell):
    $env:LDAP_TEST_HOST = "<host o IP del DC>"
    $env:LDAP_TEST_USER = "<upn o DN>"
    $env:LDAP_TEST_PASSWORD = "<password>"
    python manual_scripts/testldap.py

Nota di sicurezza: una versione precedente di questo script aveva una
password reale hardcoded, già committata in git. Se non è già stata
ruotata, va considerata compromessa e cambiata sull'Active Directory.
"""

import os
import ssl

from ldap3 import Connection, Server, Tls

LDAP_HOST = os.environ["LDAP_TEST_HOST"]
LDAP_USER = os.environ["LDAP_TEST_USER"]
LDAP_PASSWORD = os.environ["LDAP_TEST_PASSWORD"]
SEARCH_BASE = os.environ.get("LDAP_TEST_SEARCH_BASE", "DC=sicura,DC=loc")
SEARCH_FILTER = os.environ.get("LDAP_TEST_SEARCH_FILTER", "(sn=Ro*)")

# ⚠️ In produzione, sostituisci CERT_NONE con CERT_REQUIRED e importa la CA.
tls_config = Tls(validate=ssl.CERT_NONE)

# Server LDAP via SSL (porta 636)
server = Server(LDAP_HOST, port=636, use_ssl=True, tls=tls_config)

# Connessione e bind
try:
    conn = Connection(
        server, user=LDAP_USER, password=LDAP_PASSWORD, auto_bind=True
    )
    print("✔️ Connessione LDAPS riuscita")

    # Esegui una ricerca base (modifica il filtro come ti serve)
    conn.search(
        search_base=SEARCH_BASE,
        search_filter=SEARCH_FILTER,
        attributes=["givenName", "sn", "mail"],
    )

    for entry in conn.entries:
        print(entry)

except Exception as e:
    print("❌ Errore LDAPS:", e)
