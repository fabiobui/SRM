"""
Management command per testare la connessione LDAP (bind di servizio e ricerca base).
"""
import ssl
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

try:
    import ldap3
    from ldap3 import Tls
except ImportError:
    ldap3 = None


class Command(BaseCommand):
    help = "Testa la connessione LDAP: verifica raggiungibilità del server, bind di servizio e ricerca base."

    def add_arguments(self, parser):
        parser.add_argument(
            "--server-uri",
            dest="server_uri",
            default=None,
            help="URI del server LDAP (default: AUTH_LDAP_SERVER_URI dal settings)",
        )
        parser.add_argument(
            "--bind-dn",
            dest="bind_dn",
            default=None,
            help="DN dell'account di servizio (default: AUTH_LDAP_BIND_DN dal settings)",
        )
        parser.add_argument(
            "--bind-password",
            dest="bind_password",
            default=None,
            help="Password dell'account di servizio (default: AUTH_LDAP_BIND_PASSWORD dal settings)",
        )
        parser.add_argument(
            "--search-base",
            dest="search_base",
            default=None,
            help="Base DN per la ricerca di test (default: LDAP_USER_BASE_DN dal settings)",
        )
        parser.add_argument(
            "--no-search",
            action="store_true",
            default=False,
            help="Salta la ricerca di test, esegui solo il bind",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=10,
            help="Timeout connessione in secondi (default: 10)",
        )

    def handle(self, *args, **options):
        if ldap3 is None:
            raise CommandError("Il pacchetto 'ldap3' non è installato. Esegui: pip install ldap3")

        server_uri = options["server_uri"] or getattr(settings, "AUTH_LDAP_SERVER_URI", "")
        bind_dn = options["bind_dn"] or getattr(settings, "AUTH_LDAP_BIND_DN", "")
        bind_password = options["bind_password"] or getattr(settings, "AUTH_LDAP_BIND_PASSWORD", "")
        search_base = options["search_base"] or getattr(settings, "LDAP_USER_BASE_DN", "")
        timeout = options["timeout"]
        no_search = options["no_search"]

        if not server_uri:
            raise CommandError("Nessun server URI configurato. Usa --server-uri o imposta AUTH_LDAP_SERVER_URI.")
        if not bind_dn or not bind_password:
            raise CommandError("Bind DN e password obbligatori. Usa --bind-dn/--bind-password o configura il settings.")

        self.stdout.write(self.style.MIGRATE_HEADING("=== Test connessione LDAP ==="))
        self.stdout.write(f"  Server URI   : {server_uri}")
        self.stdout.write(f"  Bind DN      : {bind_dn}")
        self.stdout.write(f"  Search Base  : {search_base or '(non impostata)'}")
        self.stdout.write(f"  Timeout      : {timeout}s")
        self.stdout.write("")

        # --- 1. Connessione al server ---
        self.stdout.write("1) Connessione al server LDAP...")
        use_ssl = server_uri.startswith("ldaps://")
        tls_config = None
        if use_ssl:
            validate_cert = getattr(settings, "LDAP_TLS_VALIDATE", True)
            tls_config = Tls(validate=ssl.CERT_REQUIRED if validate_cert else ssl.CERT_NONE)

        try:
            server = ldap3.Server(
                server_uri,
                use_ssl=use_ssl,
                tls=tls_config,
                get_info=ldap3.ALL,
                connect_timeout=timeout,
            )
            self.stdout.write(self.style.SUCCESS("   OK - Server raggiungibile"))
        except Exception as exc:
            raise CommandError(f"Impossibile connettersi al server: {exc}")

        # --- 2. Bind di servizio ---
        self.stdout.write("2) Bind con account di servizio...")
        t0 = time.monotonic()
        try:
            conn = ldap3.Connection(
                server,
                user=bind_dn,
                password=bind_password,
                auto_bind=True,
                receive_timeout=timeout,
            )
            elapsed = time.monotonic() - t0
            if not conn.bound:
                raise CommandError("Bind fallito: il server non ha accettato le credenziali di servizio.")
            self.stdout.write(self.style.SUCCESS(f"   OK - Bind riuscito ({elapsed:.2f}s)"))
        except ldap3.core.exceptions.LDAPBindError as exc:
            raise CommandError(f"Bind di servizio fallito (credenziali errate?): {exc}")
        except Exception as exc:
            raise CommandError(f"Errore durante il bind di servizio: {exc}")

        # --- 3. Info server ---
        if server.info:
            self.stdout.write("3) Informazioni server:")
            if server.info.naming_contexts:
                for nc in server.info.naming_contexts:
                    self.stdout.write(f"   Naming Context: {nc}")
        else:
            self.stdout.write("3) Informazioni server: non disponibili")

        # --- 4. Ricerca di test ---
        if not no_search:
            if not search_base:
                self.stdout.write(self.style.WARNING("4) Ricerca di test saltata: search base non configurata."))
            else:
                self.stdout.write(f"4) Ricerca di test su '{search_base}'...")
                try:
                    success = conn.search(
                        search_base=search_base,
                        search_filter="(objectClass=*)",
                        search_scope=ldap3.LEVEL,
                        size_limit=5,
                        attributes=["cn", "distinguishedName"],
                    )
                    if success:
                        count = len(conn.entries)
                        self.stdout.write(self.style.SUCCESS(f"   OK - {count} entry trovate (limit 5)"))
                        for entry in conn.entries[:5]:
                            self.stdout.write(f"   - {entry.entry_dn}")
                    else:
                        self.stdout.write(self.style.WARNING(f"   Nessun risultato. Verifica il search base."))
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(f"   Errore nella ricerca: {exc}"))
        else:
            self.stdout.write("4) Ricerca di test: saltata (--no-search)")

        # Chiudi connessione
        conn.unbind()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=== Connessione LDAP OK ==="))
