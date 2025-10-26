from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, flash, render_template_string, session 
from flask_cors import CORS
import requests
from ldap3 import Server, Connection, ALL, Tls
from models import db, User, UserDetails, Autorizzatori, ActionToken, Opzioni, Cdc, SubmissionLog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import googlemaps
from redminelib import Redmine
from bs4 import BeautifulSoup
import ssl
import os
import smtplib
import secrets
import socket
import json
import ipaddress
import geocoder
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# === CONFIGURAZIONE ===
SERVER_NAME = socket.gethostname()
#DB_CONNECTION_STRING = 'sqlite:///ldap_users.db'

DB_CONNECTION_STRING = (
    'mysql+pymysql://root:quark@localhost/travel'
    if SERVER_NAME in ("FABIOHPNEO", "ryzen9")
    else 'mysql+pymysql://travel:Fulgard2025!@172.16.1.65/travel'
)


# Configurazione SMTP
SMTP_HOST = 'spoc.fulgard.com'
SMTP_PORT = 25

# Configurazione Redmine
REDMINE_URL = (
    'http://localhost:9090'  # URL del server Redmine in produzione
    if SERVER_NAME in ("FABIOHPNEO", "ryzen9")
    else  'https://spoctest.fulgard.com'  # URL del server Redmine
)
API_KEY = '92f621e2584a5fdc95ef99a4d2f019ea4b682d71'  # Chiave API di Redmine
PROJECT_ID = 11      # ID o identificatore del progetto
TRACKER_ID = 4       # es. 1 = Supporto
COMPANY_ID = 1       # 'FULGARD'
COMPANY_NAME = 'FULGARD'  # Nome della compagnia
EMAIL_TO = 'travel@fulgard.com'  # Email a cui inviare la notifica
EMIAL_MITTENTE = f"Richieste viaggi Fulgard <{EMAIL_TO}>"
STATUS_ID_APPROVATO = 9  # ID dello stato dell'issue in Redmine
STATUS_ID_RIFIUTATO = 10  # ID dello stato dell'issue in Redmine

# Configurazione Google Maps
GMAPS_API_KEY = 'AIzaSyDSTrthXlVxE0DM_hXU6HDYtw8iXeQxrZ0'  # Chiave API di Google Maps

# Configurazione LDAP
LDAP_SERVER = '172.16.1.90'
LDAP_PORT = 636
LDAP_USER = 'spoc@sicura.loc'
LDAP_PASSWORD = 'Gz8#kV!3pT@q9Xw$M1'
USE_SSL = True
TLS_CONFIG = Tls(validate=ssl.CERT_NONE)  # Configurazione TLS per LDAP

# === LOGGING ===
LOG_DIR = Path(os.getenv("TRAVEL_LOG_DIR", "/var/log/travel_app"))
LOG_FILE = LOG_DIR / "travel_app.log"

# Prova a creare /var/log/... ; se non hai permessi, ripiega su ./logs
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    can_use_system_logdir = os.access(LOG_DIR, os.W_OK)
except Exception:
    can_use_system_logdir = False

if not can_use_system_logdir:
    LOG_DIR = Path("./logs")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = LOG_DIR / "travel_app.log"

# Formatter unico
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler a rotazione: 5 MB x 5 file
file_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Pulisci eventuali handler preesistenti (evita doppi log) e attacca al root
root = logging.getLogger()
root.handlers.clear()
root.setLevel(logging.INFO)
root.addHandler(file_handler)

# Allinea i logger di Flask/Werkzeug al root/file
logging.getLogger("werkzeug").handlers.clear()
logging.getLogger("werkzeug").propagate = True
logging.getLogger("werkzeug").setLevel(logging.INFO)
logging.getLogger("geocoder").setLevel(logging.ERROR)
logging.getLogger("geocoder.base").setLevel(logging.ERROR)

# 🔑 Aggiungi questa riga!
logger = logging.getLogger("travel_app")
logger.info(f"Logging su file: {LOG_FILE}")

# === INIZIALIZZAZIONE VARIABLI ===
app = Flask(__name__)
app.secret_key = 'supersegreto123'  # Sostituisci con qualcosa di più sicuro in produzione
#CORS(app)  # se necessario per sviluppo
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONNECTION_STRING
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
gmaps = googlemaps.Client(key=GMAPS_API_KEY)
redmine = Redmine(REDMINE_URL, key=API_KEY)

# Reti interne
INTERNAL_NETWORKS = [
    # Reti private standard
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12")
    #ipaddress.ip_network("171.16.0.0/12")
]


# === FUNZIONI ===

def is_internal_ip(ip):
    try:
        logger.info(f"Verifica IP: {ip}")
        return any(ipaddress.ip_address(ip) in net for net in INTERNAL_NETWORKS)
    except ValueError:
        logger.warning(f"Valore IP non valido: {ip}")
        return False


def render_html_to_string(template_filename, context=None):
    """
    Renderizza un file HTML con Jinja2 e ritorna una stringa HTML.
    Il file deve trovarsi nella cartella 'templates'.
    
    :param template_filename: Nome del file HTML (es. 'tabella_dati.html')
    :param context: Dizionario con variabili da passare al template
    :return: HTML renderizzato come stringa
    """
    if context is None:
        context = {}

    template_path = os.path.join("templates", template_filename)
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template non trovato: {template_path}")
    
    with open(template_path, encoding="utf-8") as f:
        template_str = f.read()
    
    html = render_template_string(template_str, **context)
    # Ora modifichiamo la stringa HTML per aggiungere stili
    soup = BeautifulSoup(html, "html.parser")

    # Applica stile a tutti i tag <table>, <th>, <td>
    for table in soup.find_all("table"):
        table["style"] = "border: 2px solid #0073aa; border-collapse: collapse; width: 100%;"
    for th in soup.find_all("th"):
        th["style"] = "border: 2px solid #0073aa; padding: 8px;"
    for td in soup.find_all("td"):
        td["style"] = "border: 2px solid #0073aa; padding: 8px; background-color: #fff;"

    # Aggiunge due <br> alla fine
    soup.append(soup.new_tag("br"))
    soup.append(soup.new_tag("br"))

    return str(soup)

def crea_issue_redmine(custom_fields, priority=2, subject=None, note=None):
    """
    Crea un'issue in Redmine con i dati forniti.
    
    :param testo_lungo: Stringa HTML con i dati da inserire nell'issue
    :return: ID dell'issue creata
    """
    try:
        new_issue = redmine.issue.create(
            project_id=PROJECT_ID,   # oppure ID numerico
            subject=subject,  # Oggetto dell'issue
            description=note,
            tracker_id=TRACKER_ID,                 # ad esempio 1 = Bug, 2 = Feature, ecc.
            status_id=1,                  # 1 = Nuovo, ecc.
            priority_id=priority,                 # 2 = Normale, 3 = Alta, ecc.
            custom_fields=custom_fields
        )
        return new_issue.id, None
    except Exception as e:
        logger.error(f"Errore nella creazione dell'issue: {e}")
        return None, e

def create_helpdesk_ticket(issue_id, email, cognome, nome, telefono):
    response = requests.post(
        f"{REDMINE_URL}/api/helpdesk/tickets",
        headers={
            'X-Redmine-API-Key': API_KEY,
            'Content-Type': 'application/json'
        },
        json={
            "cognome": cognome,
            "nome": nome,
            "from_address": email,
            "to_address": EMAIL_TO,
            "telefono": telefono,
            "issue_id": issue_id,
            "project_id": PROJECT_ID
            }
    )
    #response.raise_for_status()
    if response.ok:
        data = response.json()
        ticket_id = data.get('helpdesk_ticket_id')
        logger.info(f"✅ Ticket creato: ID {ticket_id}")
        return ticket_id
    else:
        logger.error(f"❌ Errore: {response.status_code} - {response.text}")
        return None

def aggiorna_ticket(ticket_id, status_id):
    url = f"{REDMINE_URL}/issues/{ticket_id}.json"
    headers = {
        "X-Redmine-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {"issue": {"status_id": status_id}}
    response = requests.put(url, headers=headers, json=data)
    return response.ok

def get_issue(issue_id):
    headers = {"X-Redmine-API-Key": API_KEY}
    url = f"{REDMINE_URL}/issues/{issue_id}.json"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return None

def format_note_date(iso_string):
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%d/%m/%y %H:%M")    

def get_issue_notes(issue_id):
    url = f"{REDMINE_URL}/issues/{issue_id}.json?include=journals"
    headers = {"X-Redmine-API-Key": API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []

    data = response.json()
    journals = data.get("issue", {}).get("journals", [])

    note_list = [
        {
            "autore": j["user"]["name"],
            "data": format_note_date(j["created_on"]),
            "nota": j["notes"]
        }
        for j in journals
        if j.get("notes")  # solo note non vuote
    ]
    return note_list


def genera_token(ticket_id, action, emailRichiedente=None, emailResp=None):
    token = secrets.token_urlsafe(16)
    nuovo_token = ActionToken(ticket_id=ticket_id, email_richiedente=emailRichiedente, email_approvatore=emailResp, used=False,
                               action=action, token=token)
    db.session.add(nuovo_token)
    db.session.commit()
    return token

def crea_email_html(base_url, ticket_id, dati):
    emailResp = dati.get('emailResp')
    emailResp2 = dati.get('emailResp2')
    if emailResp2:
        emailResp = emailResp2
    token_approva = genera_token(ticket_id, "approve", dati.get('emailRichiedente'), emailResp)
    token_rifiuta = genera_token(ticket_id, "reject", dati.get('emailRichiedente'), emailResp)
    url_approva = f"{base_url}/azione?token={token_approva}"
    url_rifiuta = f"{base_url}/azione?token={token_rifiuta}"

    dati["url_approva"] = url_approva
    dati["url_rifiuta"] = url_rifiuta
    # Renderizza il template HTML con i dati
    html = render_html_to_string('email_conferma.html', {"dati": dati})

    return html

def invia_email_html(destinatario, oggetto, corpo_html, cc=None):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = oggetto
    msg["From"] = EMIAL_MITTENTE
    msg["To"] = destinatario
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(corpo_html, "html"))

    # Lista di tutti i destinatari per sendmail
    tutti_destinatari = [destinatario]
    if cc:
        # Se cc è una stringa con più email separate da virgola
        if isinstance(cc, str):
            tutti_destinatari.extend([email.strip() for email in cc.split(',')])
        # Se cc è già una lista
        elif isinstance(cc, list):
            tutti_destinatari.extend(cc)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.sendmail(EMIAL_MITTENTE, tutti_destinatari, msg.as_string())

    logger.info(f"Email inviata a {tutti_destinatari}.")

def get_path(path):
    """
    Restituisce il percorso base dell'applicazione.
    """
    prefix = request.headers.get("X-Forwarded-Prefix", "")
    path = path if (prefix is None or prefix == "") else prefix + path
    return path


def is_private_or_loopback(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip.split(",")[0].strip())
        return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local
    except ValueError:
        return True  # IP malformato: trattalo come non geolocalizzabile

def geo_lookup(ip: str, timeout: float = 2.0) -> str | None:
    """Ritorna 'City, Country' oppure None senza lanciare eccezioni."""
    if not ip or is_private_or_loopback(ip):
        return None
    try:
        # Usa HTTPS e timeout breve
        g = geocoder.ipinfo(ip, timeout=timeout, scheme="https")
        if g.ok:
            city = (g.city or "").strip()
            country = (g.country or "").strip()
            label = ", ".join([p for p in (city, country) if p])
            return label or None
        return None
    except Exception as e:
        logger.warning(f"Geo lookup fallita per {ip}: {e}")
        return None

# ===============================


### MAIN ENDPOINT ###

#@app.after_request
#def add_csp_headers(response):
#    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'"
#    return response

@app.before_request
def check_auth():
    # Evita il redirect per file statici e per il login stesso
    if request.endpoint in ['static', 'login', 'azione']:
        return

    if 'user' not in session:
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if not is_internal_ip(user_ip):
            return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('home'))


@app.route('/home', methods=['GET', 'POST'])
def home():
    opzioni = ['motivo_trasferta', 'societa', 'tipo_documento', 'mezzo_trasporto', 'tipo_bagaglio', 'preferenza_posto']
    dati = {}
    dati["path_conferma"] = get_path("/conferma")
    for opzione in opzioni:
        dati[opzione] = Opzioni.query.filter_by(opzione=opzione).order_by(Opzioni.posizione).all()        
    return render_template('modulo-1.html', dati=dati)

@app.route('/login', methods=['GET', 'POST'])
def login():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)

    # Accesso diretto da rete interna → salta login
    if is_internal_ip(user_ip):
        session['user'] = 'utente-interno'
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Username e password sono obbligatori.", "danger")
            return redirect(url_for('login'))

        # Formato login per dominio AD
        user_dn = f"sicura\\{username}"  # oppure f"{username}@sicura.loc"

        try:
            server = Server(LDAP_SERVER, port=LDAP_PORT, use_ssl=USE_SSL, tls=TLS_CONFIG)
            conn = Connection(server, user=user_dn, password=password, auto_bind=True)

            if conn.bound:
                session['user'] = username
                flash("Login effettuato con successo.", "success")
                return redirect(url_for('home'))

            else:
                flash("Credenziali non valide. Riprova.", "danger")
                return redirect(url_for('login'))

        except Exception as e:
            flash("Errore di connessione al server LDAP.", "danger")
            logger.error(f"❌ LDAP error: {e}")
            return redirect(url_for('login'))

    # GET: mostra form login
    dati = {}
    dati["path_login"] = get_path("/login")
    return render_template("login.html", dati=dati)


@app.route("/azione")
def azione():
    token = request.args.get("token")
    record = ActionToken.query.filter_by(token=token, used=False).first()
    if not record:
        return "Token non valido o già usato.", 403

    logger.info(f"Token: {record.token}")
    logger.info(f"Action: {record.action}")

    ticket_response = get_issue(record.ticket_id)
    if ticket_response:
        issue = ticket_response.get("issue")
        notes = get_issue_notes(record.ticket_id)
        dati = {
            "issue_id": record.ticket_id,
            "descrizione": issue.get("description"),
            "email_richiedente": record.email_richiedente,
            "email_resp": record.email_approvatore,
            "approvazione": 'approvata' if record.action == "approve" else 'rifiutata',
            "assegnato_a": issue.get("assigned_to", {}).get("name"),
            "status": issue.get("status", {}).get("name"),
            "notes": notes
        }
        # Estrai i campi personalizzati
        for field in issue.get("custom_fields", []):
            if field["id"] in [25, 26, 27, 28]:
                name = field["name"].lower().replace(" ", "_")
                logger.info(f"{name}: {field['value']}")
                dati[name] = field["value"]
        # Invia email di approvazione/rifiuto
        corpo_html = render_html_to_string('email_conferma2.html', {"dati": dati})        
        oggetto = f"Richiesta di viaggio - [Trasferta #{record.ticket_id}]"
        oggetto += " - APPROVATA" if record.action == "approve" else " - RIFIUTATA"
        invia_email_html(record.email_richiedente, oggetto, corpo_html)
    else:
        logger.error(f"Errore nella richiesta: {ticket_response.status_code}")

    status_id = STATUS_ID_APPROVATO if record.action == "approve" else STATUS_ID_RIFIUTATO  # Adatta agli ID di Redmine
    if aggiorna_ticket(record.ticket_id, status_id):
        record.used = True
        db.session.commit()
        return f"<h2>Richiesta n.{record.ticket_id} <b>{'approvata' if record.action == 'approve' else 'rifiutata'}</b> dal responsabile.</h2>", 200
    else:
        return "Errore durante aggiornamento Redmine.", 500

@app.route('/conferma', methods=['GET', 'POST'])
def conferma():
    base_url = request.url_root.rstrip('/')
    if request.method == 'POST':
        dati = request.form.to_dict()

        cod_azienda = dati.get('societa')
        logger.info(f"Codice azienda: {cod_azienda}")
        if cod_azienda:
            # Verifica se l'azienda esiste nel DB
            opzione = Opzioni.query.filter_by(opzione='societa', id=cod_azienda).first()
            if opzione:
                dati['societa'] = f"{opzione.id} - {opzione.descrizione}"

        uid = dati.get('user_id')  # deve esserci nel form
        if not uid:
            flash('UID mancante', 'error')

        # Logging dati di accesso
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        windows_user = request.environ.get('REMOTE_USER') or (
            request.authorization.username if request.authorization else None)
        
        try:
            g = geo_lookup(user_ip) 
            location = f"{g.city}, {g.country}" if g.ok else None
        except:
            location = None


        # Cerca se esiste già un dettaglio, così da aggiornare invece di duplicare
        details = UserDetails.query.filter_by(uid=uid).first()
        if not details:
            details = UserDetails(uid=uid)

        # Assegna i valori
        details.telefono = dati.get('telefono')
        details.tipodoc = dati.get('tipoDoc')
        details.numdoc = dati.get('numDoc')
        details.socaddebito = dati.get('societa')
        details.cdc = dati.get('cdc')

        # Parsing della data
        scadenza_str = dati.get('dataScadDoc')
        if scadenza_str:
            try:
                details.scadenzadoc = datetime.strptime(scadenza_str, '%d/%m/%Y').date()
            except ValueError:
                flash('Formato data non valido. Usa GG/MM/AAAA.', 'error')
                return redirect(url_for('form_page'))

        # Salva nel DB
        db.session.add(details)
        db.session.commit()

        # Crea una nuova issue in Redmine
        priority_list = {
            2: 'normale',
            3: 'alta',
            4: 'urgente',
            5: 'urgentissima'
        }
        priority = next((k for k, v in priority_list.items() if v == dati.get('priorita')), None)
        campi_custom_html = {25: 'dati_richiedente.html', 
                             26: 'dati_rifazienda.html', 
                             27: 'dati_trasferta.html', 
                             28: 'dati_pernotto.html'}
        custom_fields = []
        for id_campo, nome_file in campi_custom_html.items():
            if (id_campo == 28) and (dati.get('toggleHotel') != 'si'):
                html = "<p><b>Nessuna prenotazione hotel</b></p>"
            else:
                html = render_html_to_string(nome_file, {"dati": dati})
            custom_fields.append({
                'id': id_campo,
                'value': html
            })
        campi_custom_addizionali = {
            6: cod_azienda,  # Società di addebito
            33: dati.get('cdc'),
            34: dati.get('commessa'),
            35: "0.00",  # Importo totale
            47: uid  # ID utente
        }
        for id_campo, valore in campi_custom_addizionali.items():
            if valore:
                custom_fields.append({
                    'id': id_campo,
                    'value': valore
                })
        subject = f"Richiesta di viaggio per {dati.get('cognome')} {dati.get('nome')}"    
        issue_id, error = crea_issue_redmine(custom_fields, priority, subject, dati.get('note'))
        if error:
            flash(f"Errore nella creazione su Redmine del ticket: {error}", 'error')
        if issue_id:
            logger.info(f"ID issue creata: {issue_id}")
            # Log della richiesta
            log = SubmissionLog(
                uid=uid,
                user_agent=user_agent,
                ip=user_ip,
                windows_user=windows_user,
                location=location,
                issue_id=issue_id
            )
            db.session.add(log)
            db.session.commit()
            email_richiedente = dati.get('emailRichiedente')
            email_approvatore = dati.get('emailResp')
            email_approvatore2 = dati.get('emailResp2')
            dati["issue_id"] = issue_id
            helpdesk_ticket_id = create_helpdesk_ticket(issue_id, email_richiedente, dati.get('cognome'), dati.get('nome'), dati.get('telefono'))
            dati["helpdesk_ticket_id"] = helpdesk_ticket_id            
            flash(f'Ticket creato con ID: {issue_id}', 'success')
            # Invia email di approvazione/rifiuto
            dati["mittente"] = "no"
            corpo_html = crea_email_html(base_url, issue_id, dati)
            oggetto = f"Richiesta di viaggio per {dati.get('cognome')} {dati.get('nome')} - [Trasferta #{issue_id}]"
            if email_approvatore2:
                cc = email_approvatore
                email_approvatore = email_approvatore2
            else:
                cc = None
            invia_email_html(email_approvatore, oggetto, corpo_html, cc=cc)
            # Invia email al mittente
            dati["mittente"] = "si"
            corpo_html = crea_email_html(base_url, issue_id, dati)
            oggetto = f"Richiesta di viaggio - [Trasferta #{issue_id}]"
            invia_email_html(email_richiedente, oggetto, corpo_html)            
        else:
            flash('Errore generico nella creazione del ticket', 'error')

        return render_template("conferma.html", dati=dati)



@app.route('/get_user', methods=['GET'])
def get_user():
    uid = request.args.get('uid')
    user = User.query.filter_by(uid=uid).first()
    
    if user:
        user_dict = {
            'uid': user.uid,
            'label': f"{user.surname} {user.name}".strip(),
            'username': user.username,
            'surname': user.surname,
            'name': user.name,
            'email': user.email,
            'department': user.department,
            'company': user.company,
        }

        # Aggiungi i dettagli se esistono
        if user.details:
            user_dict.update({
                'telefono': user.details.telefono,
                'tipodoc': user.details.tipodoc,
                'numdoc': user.details.numdoc,
                'scadenzadoc': user.details.scadenzadoc.strftime('%d/%m/%Y') if user.details.scadenzadoc else None,
                'socaddebito': user.details.socaddebito,
                'cdc': user.details.cdc
            })
        else:
            # Puoi anche aggiungere i campi con valore None se vuoi che siano sempre presenti
            user_dict.update({
                'telefono': None,
                'tipodoc': None,
                'numdoc': None,
                'scadenzadoc': None,
                'socaddebito': None,
                'cdc': None
            })
        # Aggiungi i campi dell'autorizzatore se esistono
    
        if user.autorizzato_da:
            user_dict.update({
                'nominativo': user.autorizzato_da.nominativo,
                'auto1_nominativo': user.autorizzato_da.auto1_nominativo if user.autorizzato_da.auto1 else None,
                'cod_dip': user.autorizzato_da.cod_dip,
                'cod_azienda': user.autorizzato_da.cod_azienda,
                'auto1_uid': user.autorizzato_da.auto1_uid,
                'auto2_uid': user.autorizzato_da.auto2_uid,
                'auto3_uid': user.autorizzato_da.auto3_uid,
                'cdc': user.autorizzato_da.cdc
            })
        else:
            # Valori nulli se non esiste relazione
            user_dict.update({
                'nominativo': None,
                'auto1_nominativo': None,
                'cod_dip': None,
                'cod_azienda': None,
                'auto1_uid': None,
                'auto2_uid': None,
                'auto3_uid': None,
                'cdc': 'n/a'
            })

        #print(user_dict)  # Debug: stampa il dizionario dell'utente
        return jsonify([user_dict])
    else:
        return jsonify([])


@app.route('/autocomplete_cdc', methods=['POST'])
def autocomplete_cdc():
    data = request.get_json()
    term = data.get('term', '').strip()
    if term:
        # 🟢 1. Ricerca locale nel DB
        results = []
        cdc_list = Cdc.query.filter(Cdc.cdc.ilike(f"{term}%")).limit(10).all()
        if cdc_list:
            for cdc in cdc_list:
                results.append({
                    'label': f"{cdc.cdc}",
                    'uid': cdc.uid,
                    'cdc': cdc.cdc,
                })
        else:
            results = []

        return jsonify(results)


@app.route('/autocomplete_surnames', methods=['POST'])
def autocomplete_surnames():
    data = request.get_json()
    term = data.get('term', '').strip()

    # 🟢 1. Ricerca locale nel DB
    results = []
    if term:
        users = User.query.filter(User.surname.ilike(f"{term}%")).limit(10).all()
        if users:
            for user in users:
                 results.append({
                    'label': f"{user.surname} {user.name}".strip(),
                    'email': user.email,
                    'surname': user.surname,
                    'name': user.name,
                    'uid': user.uid,
                    'cod_azienda': user.autorizzato_da.cod_azienda if user.autorizzato_da else None,
                    'cod_dip': user.autorizzato_da.cod_dip if user.autorizzato_da else None,
                    'auto1_uid': user.autorizzato_da.auto1_uid if user.autorizzato_da else None,
                    'auto1_email': user.autorizzato_da.auto1_email if user.autorizzato_da else None,
                    'auto1_nominativo': user.autorizzato_da.auto1_nominativo if user.autorizzato_da else None,
                    'cdc': user.autorizzato_da.cdc if user.autorizzato_da else 'n/a'
                })

    # 🔁 2. Se non trovati risultati locali, fai la ricerca LDAP
    if not results:
        server = Server(LDAP_SERVER, port=LDAP_PORT, use_ssl=USE_SSL, tls=TLS_CONFIG)
        user = LDAP_USER
        password = LDAP_PASSWORD

        try:
            conn = Connection(server, user=user, password=password, auto_bind=True)
            conn.search(
                search_base='DC=sicura,DC=loc',
                search_filter=f'(sn={term}*)',
                attributes=['sn', 'givenName', 'mail'],
                size_limit=10
            )
            for entry in conn.entries:
                sn = entry.sn.value or ''
                given = entry.givenName.value or ''
                email = entry.mail.value or ''
                name = f"{sn} {given}".strip()
                results.append({
                    'label': name,
                    'email': email
                })

        except Exception as e:
            logger.error(f"❌ Errore LDAPS: {e}")

    return jsonify(results)


@app.route('/autocomplete_luoghi', methods=['POST'])
def autocomplete_luoghi():
    data = request.get_json()
    input_text = data.get('term', '').strip()

    if not input_text:
        return jsonify({'error': 'Parametro "input" mancante'}), 400

    # Chiamata all'API di Google Places Autocomplete
    try:
        predictions = gmaps.places_autocomplete(
            input_text,
            language='it',
            components={'country': 'it'}
        )
        # Estrai solo le descrizioni dei luoghi
        suggestions = []
        for prediction in predictions:
            parts = prediction['description'].split(',')
            if len(parts) >= 3:
                luogo = parts[0].strip()
                provincia = parts[-2].strip()
                label = f"{luogo} ({provincia})"
            else:
                label = prediction['description']
            suggestions.append({"label": label})

        # Limita a 10 risultati
        #suggestions = suggestions[:10]
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Server name: {SERVER_NAME}")
    debug = True if (SERVER_NAME == "FABIOHPNEO" or SERVER_NAME == "ryzen9")  else False
    logger.info(f"Avvio applicazione Flask in {'debug' if debug else 'produzione'}")
    app.run(debug=debug) 
