from ldap3 import Server, Connection, Tls
import ssl

# ⚠️ In produzione, sostituisci CERT_NONE con CERT_REQUIRED e importa la CA.
tls_config = Tls(validate=ssl.CERT_NONE)

# Server LDAP via SSL (porta 636)
server = Server('172.16.1.90', port=636, use_ssl=True, tls=tls_config)

# Usa il formato utente corretto: prova con UPN o DOMAIN\username
user = 	'spoc@sicura.loc'  # O prova con il DN completo
password = 'Gz8#kV!3pT@q9Xw$M1'


# Connessione e bind
try:
    conn = Connection(server, user=user, password=password, auto_bind=True)
    print("✔️ Connessione LDAPS riuscita")

    # Esegui una ricerca base (modifica il filtro come ti serve)
    conn.search(
        search_base='DC=sicura,DC=loc',
        search_filter='(sn=Ro*)',
        attributes=['givenName', 'sn', 'mail']
    )

    for entry in conn.entries:
        print(entry)

except Exception as e:
    print("❌ Errore LDAPS:", e)

