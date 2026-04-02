"""
Management command per testare l'autenticazione LDAP di un utente specifico.
"""
import getpass
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
    help = "Testa l'autenticazione LDAP di un utente: ricerca + bind con le sue credenziali."

    def add_arguments(self, parser):
        parser.add_argument("username", help="Username (email/UPN) dell'utente da autenticare")
        parser.add_argument(
            "--password",
            dest="password",
            default=None,
            help="Password dell'utente (se non fornita, verrà chiesta interattivamente)",
        )
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
            help="Base DN per la ricerca utente (default: LDAP_USER_BASE_DN dal settings)",
        )
        parser.add_argument(
            "--search-filter",
            dest="search_filter",
            default=None,
            help="Filtro di ricerca LDAP. Usa {username} come placeholder (default: (userPrincipalName={username}))",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=10,
            help="Timeout connessione in secondi (default: 10)",
        )
        parser.add_argument(
            "--show-attrs",
            action="store_true",
            default=False,
            help="Mostra tutti gli attributi dell'utente trovato",
        )

    def handle(self, *args, **options):
        if ldap3 is None:
            raise CommandError("Il pacchetto 'ldap3' non è installato. Esegui: pip install ldap3")

        username = options["username"]
        password = options["password"]
        server_uri = options["server_uri"] or getattr(settings, "AUTH_LDAP_SERVER_URI", "")
        bind_dn = options["bind_dn"] or getattr(settings, "AUTH_LDAP_BIND_DN", "")
        bind_password = options["bind_password"] or getattr(settings, "AUTH_LDAP_BIND_PASSWORD", "")
        search_base = options["search_base"] or getattr(settings, "LDAP_USER_BASE_DN", "")
        search_filter_tpl = options["search_filter"] or "(userPrincipalName={username})"
        timeout = options["timeout"]
        show_attrs = options["show_attrs"]

        if not server_uri:
            raise CommandError("Nessun server URI configurato. Usa --server-uri o imposta AUTH_LDAP_SERVER_URI.")
        if not bind_dn or not bind_password:
            raise CommandError("Bind DN e password di servizio obbligatori per la ricerca utente.")
        if not search_base:
            raise CommandError("Search base non configurata. Usa --search-base o imposta LDAP_USER_BASE_DN.")

        # Chiedi la password in modo interattivo se non fornita
        if not password:
            password = getpass.getpass(f"Password per {username}: ")
            if not password:
                raise CommandError("Password non fornita.")

        self.stdout.write(self.style.MIGRATE_HEADING("=== Test autenticazione LDAP ==="))
        self.stdout.write(f"  Server URI   : {server_uri}")
        self.stdout.write(f"  Bind DN      : {bind_dn}")
        self.stdout.write(f"  Search Base  : {search_base}")
        self.stdout.write(f"  Username     : {username}")
        self.stdout.write("")

        # --- Setup server ---
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
                get_info=ldap3.NONE,
                connect_timeout=timeout,
            )
        except Exception as exc:
            raise CommandError(f"Impossibile connettersi al server: {exc}")

        # --- 1. Bind di servizio ---
        self.stdout.write("1) Bind con account di servizio...")
        try:
            service_conn = ldap3.Connection(
                server,
                user=bind_dn,
                password=bind_password,
                auto_bind=True,
                receive_timeout=timeout,
            )
            self.stdout.write(self.style.SUCCESS("   OK"))
        except Exception as exc:
            raise CommandError(f"Bind di servizio fallito: {exc}")

        # --- 2. Ricerca utente ---
        search_filter = search_filter_tpl.replace("{username}", username)
        self.stdout.write(f"2) Ricerca utente con filtro: {search_filter}")

        search_attrs = [
            "userPrincipalName", "displayName", "mail", "cn",
            "sAMAccountName", "memberOf", "distinguishedName",
        ]
        if show_attrs:
            search_attrs = ldap3.ALL_ATTRIBUTES

        try:
            success = service_conn.search(
                search_base=search_base,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE,
                attributes=search_attrs,
            )
        except Exception as exc:
            service_conn.unbind()
            raise CommandError(f"Errore nella ricerca: {exc}")

        if not success or not service_conn.entries:
            service_conn.unbind()
            raise CommandError(f"Utente '{username}' non trovato nella directory LDAP.")

        user_entry = service_conn.entries[0]
        user_dn = str(user_entry.entry_dn)
        self.stdout.write(self.style.SUCCESS(f"   OK - Utente trovato: {user_dn}"))

        # Mostra attributi
        self.stdout.write("   Attributi:")
        for attr in user_entry.entry_attributes:
            val = user_entry[attr]
            self.stdout.write(f"     {attr}: {val}")

        service_conn.unbind()

        # --- 3. Bind con credenziali utente ---
        self.stdout.write("")
        self.stdout.write("3) Autenticazione con credenziali utente...")

        # Prova diversi formati di bind (come nel SimpleLDAPBackend)
        bind_formats = [
            ("DN completo", user_dn),
            ("UserPrincipalName", username),
        ]
        # Aggiungi formato NetBIOS se l'username contiene @
        if "@" in username:
            local_part = username.split("@")[0]
            domain_part = username.split("@")[1].split(".")[0]
            bind_formats.append(("NetBIOS", f"{domain_part}\\{local_part}"))

        authenticated = False
        for fmt_name, bind_user in bind_formats:
            self.stdout.write(f"   Tentativo {fmt_name}: {bind_user}")
            t0 = time.monotonic()
            try:
                user_conn = ldap3.Connection(
                    server,
                    user=bind_user,
                    password=password,
                    auto_bind=True,
                    receive_timeout=timeout,
                )
                elapsed = time.monotonic() - t0
                if user_conn.bound:
                    self.stdout.write(self.style.SUCCESS(f"   OK - Autenticazione riuscita con {fmt_name} ({elapsed:.2f}s)"))
                    user_conn.unbind()
                    authenticated = True
                    break
                user_conn.unbind()
            except ldap3.core.exceptions.LDAPBindError:
                self.stdout.write(self.style.WARNING(f"   FAIL - Credenziali rifiutate con {fmt_name}"))
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"   FAIL - Errore con {fmt_name}: {exc}"))

        self.stdout.write("")
        if authenticated:
            self.stdout.write(self.style.SUCCESS("=== Autenticazione LDAP riuscita ==="))
        else:
            raise CommandError("Autenticazione fallita con tutti i formati di bind. Verifica la password.")
