# Analisi e Implementazione — Area Fornitore (Portale)

> Documento di analisi per lo sviluppo dell'area riservata ai fornitori (vendor self‑service portal) sul Vendor Management System.

## 1. Sintesi esecutiva

Il VMS oggi gestisce molto bene il back‑office (admin + BO user) ma il **portale fornitore** è solo abbozzato (route `/documents/portal/` con upload non funzionante). L'obiettivo di questa fase è realizzare un'**area riservata al fornitore** in cui:

- il fornitore accede con utenza dedicata (creata da BO **o** auto‑registrata previa approvazione);
- gestisce i propri **documenti** (upload, aggiornamento, esiti revisione);
- visualizza e propone modifiche alla propria **anagrafica** (workflow di approvazione BO);
- consulta il proprio **stato qualifica** (score, scadenze, audit, rischio);
- comunica con il back‑office tramite una **messaggistica** dedicata.

Restano **fuori scope** in questa fase: ordini di acquisto (PO), storico performance lato fornitore, API REST esposte all'esterno, LDAP per fornitori.

---

## 2. Stato attuale (cosa esiste già)

### 2.1 Modello dati
| Modello | File | Stato |
|---|---|---|
| `User` (custom) | [users/models.py](../vendor_management_system/users/models.py) | Ha `role` (admin/bo_user/vendor) e FK `vendor`. Pronto. |
| `Vendor` | [vendors/models.py](../vendor_management_system/vendors/models.py) | Anagrafica completa, qualifica, audit, performance. Pronto. |
| `Document` / `DocumentType` | [documents/models.py](../vendor_management_system/documents/models.py) | Workflow status già implementato. Pronto. |
| `Address`, `Category` | [vendors/models.py](../vendor_management_system/vendors/models.py) | Pronto. |

### 2.2 Autenticazione
- Login custom via email/password ([core/auth_views.py](../vendor_management_system/core/auth_views.py)) con redirect per ruolo.
- `HybridAuthBackend` LDAP + ModelBackend ([core/simple_ldap_backend.py](../vendor_management_system/core/simple_ldap_backend.py)).
- Mixin permessi: `VendorRequiredMixin`, `VendorOwnerRequiredMixin` ([core/permissions.py](../vendor_management_system/core/permissions.py)).

### 2.3 Portale fornitore (parziale)
- Route: `/documents/portal/` → `VendorPortalView` ([documents/views.py:108](../vendor_management_system/documents/views.py:108)).
- Template [vendor_portal.html](../vendor_management_system/documents/templates/documents/vendor_portal.html): elenco documenti caricati / mancanti / in scadenza, ma **modal di upload non implementato** (solo `alert()` placeholder).
- `DocumentUploadView` POST funzionante ma senza form integrato in pagina.

### 2.4 Notifiche
- Esiste il template [emails/document_expiry_alert.html](../vendor_management_system/documents/templates/emails/document_expiry_alert.html) e `documents/tasks.py`. Da verificare il job periodico Celery e completare i casi d'uso.

---

## 3. Scope confermato (in base alle decisioni prese)

| Funzionalità | In scope | Note |
|---|:-:|---|
| Login/logout fornitore | ✅ | Riusare `CustomLoginView` esistente. |
| Auto‑registrazione fornitore + approvazione BO | ✅ | Nuovo flusso pubblico `RegistrationRequest`. |
| Creazione fornitore + invito da BO/admin | ✅ | Email con link "imposta password". |
| Reset password | ✅ | Flow Django nativo `PasswordResetView` con template custom. |
| "I miei documenti" (upload/aggiorna/scarica/dettaglio esito) | ✅ | Estende `VendorPortalView`. |
| Anagrafica fornitore (visualizza + proponi modifiche con approvazione BO) | ✅ | Nuovo modello `VendorChangeRequest`. |
| Stato qualifica (read‑only) | ✅ | Solo lettura dei campi già presenti su `Vendor`. |
| Messaggistica BO ↔ fornitore | ✅ | Nuovo modello `Message` + thread per fornitore. |
| Notifiche email | ✅ | Scadenze, esito revisione, esito anagrafica, nuovi messaggi. |
| Ordini di acquisto (PO) | ❌ | Fuori scope. |
| Storico performance | ❌ | Fuori scope. |
| API REST per fornitore | ❌ | Fuori scope. |
| LDAP per fornitori | ❌ | Solo auth locale. |
| Multi‑utente per fornitore | ❌ (per ora) | Modello già lo supporta; UI 1:1 in questa fase. |

---

## 4. Architettura proposta

### 4.1 Nuova app Django: `portal`

Per non gonfiare ulteriormente `documents/` e mantenere separazione di responsabilità, propongo una **nuova app** `vendor_management_system/portal/` che contenga views, URL, template, form, modelli specifici del portale fornitore (`VendorChangeRequest`, `VendorRegistrationRequest`, `Message`).

Resta com'è: `Document`/`DocumentType` (in `documents/`), `Vendor` (in `vendors/`), `User` (in `users/`).

### 4.2 Routing — prefisso `/portale`

```
/portale/                          → home portale (redirect a dashboard fornitore)
/portale/login/                    → riusa CustomLoginView
/portale/logout/
/portale/registrazione/            → RegistrationRequestCreateView (pubblica)
/portale/registrazione/conferma/   → pagina "richiesta inviata, attendi approvazione"
/portale/password-reset/...        → flow Django standard

# area autenticata (vendor)
/portale/dashboard/                → PortalDashboardView (stato sintetico)
/portale/documenti/                → MyDocumentsView (lista)
/portale/documenti/upload/         → MyDocumentUploadView (form/modal POST)
/portale/documenti/<id>/           → MyDocumentDetailView (esito, note rifiuto)
/portale/anagrafica/               → MyVendorProfileView (read)
/portale/anagrafica/modifica/      → VendorChangeRequestCreateView (proponi modifiche)
/portale/anagrafica/richieste/     → VendorChangeRequestListView (storico richieste)
/portale/qualifica/                → MyQualificationView (read-only)
/portale/messaggi/                 → MessageThreadView (lista + invio)
/portale/messaggi/<id>/            → MessageDetailView

# area BO (estende back‑office esistente)
/documents/backoffice/registrazioni/        → elenco RegistrationRequest da approvare
/documents/backoffice/anagrafica-richieste/ → elenco VendorChangeRequest da approvare
/documents/backoffice/messaggi/             → vista BO messaggistica
```

`/documents/portal/` viene mantenuto come redirect 301 a `/portale/dashboard/` per retro‑compatibilità.

### 4.3 Layout / template
- Introdurre un **template base** `portal/templates/portal/base_portal.html` con navbar, footer, gestione `{% block content %}` (Bootstrap 5 + FontAwesome via CDN, in linea con i template esistenti).
- Tutti i template dell'area fornitore estendono `base_portal.html`. Layout coerente, niente più `<html>` ripetuto in ogni pagina.

---

## 5. Modifiche al modello dati

### 5.1 Nuovo modello `VendorRegistrationRequest` (app `portal`)

Per l'auto‑registrazione pubblica con approvazione BO. La registrazione **non crea** subito `User` né `Vendor` — solo una richiesta in stato `PENDING`.

```python
class VendorRegistrationRequest(models.Model):
    STATUS = [('PENDING','In attesa'), ('APPROVED','Approvata'), ('REJECTED','Respinta')]

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    # Dati richiedente
    company_name = CharField(max_length=255)
    vat_number = CharField(max_length=20)
    fiscal_code = CharField(max_length=16, blank=True)
    email = EmailField()                      # email fornitore = futuro login
    phone = CharField(max_length=20, blank=True)
    contact_person = CharField(max_length=100)
    category = ForeignKey(Category, null=True, blank=True, on_delete=SET_NULL)
    notes = TextField(blank=True)             # messaggio del fornitore
    # Workflow
    status = CharField(choices=STATUS, default='PENDING')
    created_at = DateTimeField(auto_now_add=True)
    reviewed_at = DateTimeField(null=True, blank=True)
    reviewed_by = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True,
                             related_name='reviewed_registrations')
    review_notes = TextField(blank=True)
    # Quando approvata
    created_vendor = ForeignKey(Vendor, on_delete=SET_NULL, null=True, blank=True)
    created_user   = ForeignKey(User,   on_delete=SET_NULL, null=True, blank=True,
                                related_name='+')
```

**Approvazione** (azione BO): crea `Vendor`, crea `User(role='vendor', vendor=...)`, invia email con link "imposta password" (token Django nativo `PasswordResetTokenGenerator`).

### 5.2 Nuovo modello `VendorChangeRequest` (app `portal`)

Le modifiche all'anagrafica proposte dal fornitore vanno in approvazione BO.

```python
class VendorChangeRequest(models.Model):
    STATUS = [('PENDING','In attesa'), ('APPROVED','Approvata'), ('REJECTED','Respinta')]

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = ForeignKey(Vendor, on_delete=CASCADE, related_name='change_requests')
    requested_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    # Snapshot dei campi modificati (JSON: {field: {"old":..., "new":...}})
    changes = JSONField()
    status = CharField(choices=STATUS, default='PENDING')
    created_at = DateTimeField(auto_now_add=True)
    reviewed_at = DateTimeField(null=True, blank=True)
    reviewed_by = ForeignKey(User, on_delete=SET_NULL, null=True, blank=True,
                             related_name='reviewed_change_requests')
    review_notes = TextField(blank=True)
```

Approvazione: applica i `changes` a `Vendor`, salva. Rifiuto: scrive `review_notes`, notifica.

**Campi modificabili dal fornitore** (whitelist server‑side): `name`, `email`, `phone`, `website`, `reference_contact`, `contact_details`, `address` (creazione/aggiornamento), `iso_certifications`, `category` *(?)* — da confermare.

**Campi NON modificabili**: `vendor_code`, `vat_number`, `fiscal_code`, `qualification_*`, `risk_level`, `last_audit_date`, `next_audit_due`, `is_active`, performance.

### 5.3 Nuovo modello `Message` (app `portal`)

Messaggistica thread‑based per fornitore (1 thread per fornitore in questa fase, niente "gruppi").

```python
class Message(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = ForeignKey(Vendor, on_delete=CASCADE, related_name='messages')
    sender = ForeignKey(User, on_delete=SET_NULL, null=True)  # vendor user o BO user
    subject = CharField(max_length=200, blank=True)           # solo primo messaggio
    body = TextField()
    parent = ForeignKey('self', on_delete=CASCADE, null=True, blank=True,
                        related_name='replies')               # threading
    attachment = FileField(upload_to='vendor_messages/%Y/%m/', null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    read_at_by_vendor = DateTimeField(null=True, blank=True)
    read_at_by_bo     = DateTimeField(null=True, blank=True)
    is_from_vendor = BooleanField()  # cache: sender appartiene al vendor?
```

### 5.4 Modifiche a modelli esistenti

- **Nessuna modifica strutturale** a `User`, `Vendor`, `Document` (i campi necessari ci sono già).
- Aggiunta minore consigliata su `Document`: campo `rejection_reason` opzionale per separare le note di rifiuto dalle note generiche (oggi entrambe in `notes`). **Decisione da confermare**.

---

## 6. Componenti da sviluppare

### 6.1 Form (`portal/forms.py`)
- `VendorRegistrationForm` — form pubblico anti‑spam (honeypot o reCAPTCHA da decidere).
- `VendorProfileChangeForm` — basato su `Vendor`, **whitelist** dei campi editabili, calcola il diff e crea `VendorChangeRequest`.
- `DocumentUploadForm` — `ModelForm` su `Document` (file, document_type, issue_date, expiry_date, notes).
- `MessageReplyForm` — body + allegato opzionale.
- `SetPasswordOnInviteForm` — riusa `SetPasswordForm` Django.

### 6.2 Views (`portal/views.py`)
| View | Tipo | Descrizione |
|---|---|---|
| `PortalDashboardView` | `TemplateView + VendorRequiredMixin` | KPI sintetici: documenti mancanti, in scadenza, richieste anagrafica pendenti, messaggi non letti. |
| `MyDocumentsView` | `ListView` | Lista documenti del proprio vendor con filtro stato. |
| `MyDocumentUploadView` | `FormView` | Upload/aggiornamento documento (sostituisce alert placeholder). |
| `MyDocumentDetailView` | `DetailView + VendorOwnerRequiredMixin` | Esito revisione, motivo rifiuto, scadenze. |
| `MyVendorProfileView` | `DetailView` | Anagrafica corrente, link a "modifica", elenco richieste pendenti. |
| `VendorChangeRequestCreateView` | `FormView` | Form modifica anagrafica → genera `VendorChangeRequest`. |
| `VendorChangeRequestListView` | `ListView` | Storico richieste e relativi esiti. |
| `MyQualificationView` | `TemplateView` | Score, stato, scadenza qualifica, prossimo audit, livello rischio. Sola lettura. |
| `MessageThreadView` | `ListView + FormView` | Lista messaggi del proprio thread + form risposta. |
| `RegistrationRequestCreateView` | `CreateView` (pubblica, no auth) | Form di auto‑registrazione. |
| `RegistrationConfirmationView` | `TemplateView` | Pagina "richiesta inviata". |

**Per il back‑office** (estensioni di area esistente):
| View | Descrizione |
|---|---|
| `RegistrationRequestListView` / `ApproveView` / `RejectView` | Gestione richieste registrazione. L'`Approve` crea `Vendor` + `User` e invia email invito. |
| `VendorChangeRequestListView` / `ApproveView` / `RejectView` | Gestione richieste modifica anagrafica. |
| `BoMessageListView` | Lista thread con badge non‑letti, risposta. |

### 6.3 Permessi
- Tutte le view `/portale/*` (escluse pubbliche) usano `VendorRequiredMixin`.
- Le view di dettaglio documento/messaggio usano `VendorOwnerRequiredMixin` per impedire IDOR (un vendor non deve poter accedere a documento/messaggio di un altro vendor manipolando l'URL).
- Filtri queryset sempre su `vendor=request.user.vendor`.

### 6.4 Template (estendono `base_portal.html`)
```
portal/templates/portal/
├── base_portal.html             # layout + navbar fornitore
├── dashboard.html
├── documents/
│   ├── list.html
│   ├── upload_form.html
│   └── detail.html
├── profile/
│   ├── detail.html
│   ├── change_form.html
│   └── change_requests_list.html
├── qualification/
│   └── detail.html
├── messages/
│   ├── thread.html
│   └── _message_item.html
├── registration/
│   ├── form.html
│   └── confirmation.html
└── invite/
    └── set_password.html
```

---

## 7. Workflow chiave

### 7.1 Auto‑registrazione pubblica
```
[utente esterno] → /portale/registrazione/
        ↓ submit form
[VendorRegistrationRequest status=PENDING]
        ↓ email a BO ("nuova richiesta")
[BO apre lista richieste] → Approva
        ↓
[crea Vendor + User(role=vendor, vendor=...)]
        ↓ email al fornitore con token "imposta password"
[fornitore imposta password] → login → /portale/dashboard/
```

Rifiuto: `status=REJECTED`, email al richiedente con `review_notes`.

### 7.2 Creazione da admin (oggi già funziona)
L'admin crea `Vendor` + `User` da Django admin. Aggiungiamo, in fase di salvataggio del nuovo `User(role='vendor')`, l'invio automatico dell'email "imposta password" (toggle nel form admin: "invia invito").

### 7.3 Upload documento
```
[fornitore] → /portale/documenti/upload/  (modal sulla lista o pagina dedicata)
        ↓ POST file + document_type + scadenza
[Document(status=UPLOADED)] → email a BO ("nuovo documento da revisionare")
        ↓ BO apre /documents/review/<id>/
APPROVED → email al fornitore "approvato"
REJECTED → email al fornitore con motivo (rejection_reason / notes)
EXPIRED  → job Celery automatico al passaggio della expiry_date
```

### 7.4 Modifica anagrafica
```
[fornitore] → /portale/anagrafica/modifica/
        ↓ form (whitelist campi) → calcola diff
[VendorChangeRequest status=PENDING, changes={…}]
        ↓ email a BO
[BO] → Approva → applica diff a Vendor → email al fornitore
       Rifiuta → review_notes → email al fornitore
```

Importante: il fornitore vede sempre il **valore corrente** dell'anagrafica + un banner "hai 1 richiesta in attesa" se esiste un `VendorChangeRequest` pendente. Una sola richiesta pendente alla volta (vincolo applicativo).

### 7.5 Messaggistica
- Il fornitore può sempre aprire un nuovo messaggio (nuovo thread o continuare quello esistente — in questa fase, **un thread per fornitore**).
- Il BO risponde dalla vista `BoMessageListView`.
- Notifica email a controparte sui nuovi messaggi (rate‑limit consigliato per evitare spam: max 1 email/15min per thread).

---

## 8. Notifiche email

Estendere [documents/tasks.py](../vendor_management_system/documents/tasks.py) (Celery) e creare i template in `portal/templates/emails/`:

| Trigger | Destinatario | Template |
|---|---|---|
| Nuova `VendorRegistrationRequest` | BO (lista email da settings) | `email_registration_new.html` |
| Registrazione approvata + invito password | fornitore richiedente | `email_registration_approved.html` |
| Registrazione rifiutata | fornitore richiedente | `email_registration_rejected.html` |
| Nuovo `Document` UPLOADED | BO | `email_document_uploaded.html` |
| Documento APPROVED / REJECTED | fornitore | `email_document_reviewed.html` |
| Documento in scadenza (esistente) | fornitore | `document_expiry_alert.html` |
| Documento EXPIRED | fornitore | `email_document_expired.html` |
| Nuova `VendorChangeRequest` | BO | `email_change_request_new.html` |
| `VendorChangeRequest` APPROVED/REJECTED | fornitore | `email_change_request_reviewed.html` |
| Nuovo `Message` | controparte | `email_new_message.html` |

Job periodici (Celery beat):
- `check_expiring_documents` (giornaliero) → invia reminder e marca EXPIRED.
- `check_qualification_expiry` (giornaliero) → reminder qualifica in scadenza al fornitore + BO.

---

## 9. Sicurezza

- **Filtri queryset**: tutte le view fornitore filtrano su `vendor=self.request.user.vendor`. Mai fidarsi del PK in URL.
- **`VendorOwnerRequiredMixin`**: applicato a tutte le `DetailView` per oggetti collegati a un vendor (Document, Message, VendorChangeRequest).
- **Whitelist campi modificabili** sull'anagrafica (lato form **e** lato applicazione del diff).
- **CSRF**: Django nativo (form server‑side, no API).
- **Upload file**: limite dimensione (`FILE_UPLOAD_MAX_MEMORY_SIZE`) e validazione MIME/estensione (PDF, immagini, ZIP). Path con UUID per evitare collision/enumeration.
- **Token invito password**: `PasswordResetTokenGenerator` Django, scadenza configurabile (default 3 giorni).
- **Rate limiting** (consigliato) sulla pagina di registrazione pubblica e login (`django-ratelimit`).
- **Anti‑spam** sulla registrazione: honeypot field + opzionalmente reCAPTCHA (decisione da prendere).
- **Audit log** consigliato per le approvazioni BO (chi approva cosa, quando) — campi `reviewed_by`/`reviewed_at` già previsti nei modelli.

---

## 10. Migrazione e dati esistenti

- Nessun cambio breaking sui modelli esistenti.
- Solo nuove migrations per i 3 nuovi modelli (`VendorRegistrationRequest`, `VendorChangeRequest`, `Message`) e il campo opzionale `rejection_reason` su `Document` (se confermato).
- Gli utenti `vendor` già esistenti continueranno a funzionare con `/documents/portal/` (redirect a `/portale/dashboard/`).

---

## 11. Piano di rilascio (proposta in 4 fasi)

> Stime in giornate/uomo (gg) molto orientative — vanno tarate sul tuo contesto.

### Fase 1 — Fondamenta del portale (2-3 gg)
- Nuova app `portal/` con URL e `base_portal.html`.
- Spostamento `/documents/portal/` → `/portale/dashboard/` con redirect.
- `PortalDashboardView` (KPI sintetici).
- `MyDocumentsView` + **upload modal funzionante** (sostituisce alert placeholder).
- `MyDocumentDetailView` con esito revisione.

### Fase 2 — Anagrafica e qualifica (2-3 gg)
- `MyVendorProfileView` (read).
- Modello `VendorChangeRequest` + form con whitelist + workflow di approvazione BO.
- `MyQualificationView` (read‑only).
- View BO per gestire `VendorChangeRequest`.

### Fase 3 — Onboarding fornitore (2-3 gg)
- Modello `VendorRegistrationRequest`.
- Form pubblico `/portale/registrazione/` con anti‑spam.
- View BO di approvazione → crea Vendor + User + invio invito email.
- Flow "imposta password" via token.
- Reset password fornitore.

### Fase 4 — Messaggistica e notifiche (2-3 gg)
- Modello `Message` + `MessageThreadView` + `BoMessageListView`.
- Template email mancanti.
- Estensione `documents/tasks.py` con i nuovi job Celery.
- Test end‑to‑end dei flussi notifica.

**Totale stimato: 8–12 gg/uomo** + test e rifinitura UI.

---

## 12. Decisioni ancora aperte

Punti su cui mi serve una conferma prima/durante l'implementazione:

1. **Categoria modificabile dal fornitore?** O solo BO può cambiarla? -> NO
2. **Indirizzo modificabile**: il fornitore può modificare il suo `Address`, oppure solo proporne uno nuovo? -> lo può modificare ma dobbiamo fare una chiamata alle API di Google per normalizzare l'indirizzo
3. **Email destinatari BO**: lista statica in `settings.py` (env var `BO_NOTIFICATION_EMAILS`) oppure dinamica (tutti gli `User` con `role` admin/bo_user)? -> per ruolo
4. **Anti‑spam registrazione**: solo honeypot, o anche reCAPTCHA (richiede chiave Google)? -> solo honeypot
5. **Campo `rejection_reason`** su `Document`: aggiungerlo separato da `notes` o riusare `notes`? -> lasciamo `notes`
6. **Vincolo "una sola richiesta anagrafica pendente alla volta"**: ok come regola, o accettare anche richieste multiple in coda? -> anche richieste multiple
7. **Allegati nei messaggi**: dimensione max e tipi consentiti (default proporrei: 10 MB, PDF/immagini/ZIP)? -> aumentiamo a 50MB
8. **Privacy**: serve un'informativa privacy/consenso al primo accesso e/o sulla pagina di registrazione pubblica? -> ok prepara un template placeholder e poi io ci mette il testo completo
9. **Localizzazione**: tutti i testi in italiano (coerenti col resto), o serve anche EN/FR (locale già configurato)? -> solo Italiano per ora
10. **Branding**: logo/colori specifici da usare nel portale (oggi navbar verde Bootstrap), o lasciamo lo stile base? -> ti ho messo nella cartella `template_fulgard`il template che ho utilizzato per altro progetto e va usato

---

## 13. Appendice — Mappa file (proposta)

```
vendor_management_system/
├── portal/                              ← NUOVA APP
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py
│   ├── forms.py
│   ├── views.py
│   ├── models.py                        # VendorRegistrationRequest, VendorChangeRequest, Message
│   ├── admin.py
│   ├── tasks.py                         # job Celery specifici portale
│   ├── migrations/
│   ├── templates/
│   │   ├── portal/                      # vedi §6.4
│   │   └── emails/                      # template email portale
│   └── tests/
├── documents/
│   ├── views.py                         # estendere DocumentReviewView per inviare email esito
│   └── tasks.py                         # aggiungere check_qualification_expiry
└── config/
    └── urls.py                          # include('vendor_management_system.portal.urls', namespace='portal')
```

---

*Documento redatto come proposta tecnica iniziale. Le decisioni elencate al §12 vanno chiuse prima dell'implementazione di ciascuna fase.*
