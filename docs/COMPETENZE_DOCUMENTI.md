# Sistema di Gestione Competenze e Documenti Fornitori

## Panoramica

Il sistema è stato esteso per gestire in modo completo:
- **Competenze/Qualifiche** dei fornitori (es. RSPP, ASPP, Auditor, etc.)
- **Documenti richiesti** ai fornitori (es. DURC, Visura Camerale, Certificazioni ISO, etc.)

## Nuovi Modelli

### 1. Competence (Competenze)
Gestisce le competenze/qualifiche che i fornitori possono possedere.

**Campi principali:**
- `code`: Codice univoco (es. "RSPP", "ASPP")
- `name`: Nome completo della competenza
- `competence_category`: Categoria (Sicurezza, Qualità, Tecnico, Energia, Ambiente, Audit, Altro)
- `requires_certification`: Se richiede una certificazione formale
- `requires_renewal`: Se ha scadenza
- `renewal_period_months`: Periodo di rinnovo in mesi
- `is_mandatory`: Se è obbligatoria per alcune categorie
- `applicable_categories`: Categorie di fornitori per cui è rilevante

**Competenze pre-caricate (28 totali):**
- **Sicurezza**: RSPP, ASPP, Coord. Sicurezza Cantieri, ATEX, Prev. Incendi, Functional Safety, HAZOP, QRA/FERA, etc.
- **Tecnico**: Direzione Lavori, Consulente Merci Pericolose, Tecnico Laser, Igienista, Resp. Amianto, RAM, Acustica, Verifica ITP
- **Energia**: Energy Manager, EGE, Mobility Manager
- **Qualità**: Ergonomo Europeo
- **Audit**: Auditor ISO 9001, 14001, 45001, 50001, SGS PIR

### 2. VendorCompetence (Competenze Fornitore)
Tabella di associazione tra Vendor e Competence con dettagli certificazione.

**Campi principali:**
- `vendor`: Riferimento al fornitore
- `competence`: Riferimento alla competenza
- `has_competence`: Se possiede la competenza
- `certification_number`: Numero certificato/attestato
- `certification_body`: Ente certificatore
- `issue_date`: Data rilascio
- `expiry_date`: Data scadenza
- `verified`: Se verificata dall'azienda
- `verified_by`: Chi ha verificato
- `document_file`: File del certificato

**Property utili:**
- `is_expired`: Verifica se scaduta
- `days_to_expiry`: Giorni rimanenti
- `expiry_status`: Stato (VALID, EXPIRING, EXPIRING_SOON, EXPIRED, NO_EXPIRY)

### 3. DocumentType (Tipi Documento)
Gestisce i tipi di documenti richiesti ai fornitori.

**Campi principali:**
- `code`: Codice univoco (es. "DURC", "VISURA_CAM")
- `name`: Nome del documento
- `document_category`: Categoria (Legale, Finanziario, Sicurezza, Qualità, Tecnico, Assicurativo, Certificazioni, Altro)
- `is_mandatory`: Se obbligatorio
- `requires_renewal`: Se ha scadenza
- `default_validity_days`: Validità standard in giorni
- `alert_days_before_expiry`: Giorni preavviso scadenza
- `applicable_categories`: Categorie fornitori per cui è richiesto
- `template_file`: Template del documento
- `instructions`: Istruzioni per il fornitore

**Documenti pre-caricati (22 totali):**
- **Legali**: DURC, Visura Camerale, Cert. Antimafia, Casellario, Statuto, Atto Costitutivo
- **Finanziari**: Bilancio, Cert. Bancaria
- **Assicurativi**: RC Professionale, RC Operativa, Copertura INAIL
- **Sicurezza**: DVR, DUVRI, POS, Formazione Lavoratori
- **Certificazioni**: ISO 9001, 14001, 45001, 50001
- **Tecnici**: Referenze, Organigramma, Elenco Attrezzature

### 4. VendorDocument (Documenti Fornitore)
Associa documenti specifici ai fornitori con tracking.

**Campi principali:**
- `vendor`: Riferimento al fornitore
- `document_type`: Tipo di documento
- `document_number`: Numero/riferimento documento
- `issue_date`: Data emissione
- `expiry_date`: Data scadenza
- `status`: Stato (PENDING, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED, EXPIRED)
- `verified`: Se verificato
- `document_file`: File documento
- `rejection_reason`: Motivo rifiuto

**Property utili:**
- `is_expired`: Verifica se scaduto
- `days_to_expiry`: Giorni rimanenti
- `expiry_status`: Stato scadenza
- `is_valid`: Se approvato, non scaduto e verificato

## Estensioni al Modello Vendor

### Nuovi Campi
- `competences`: Relazione many-to-many con Competence (tramite VendorCompetence)

### Nuove Property

**Competenze:**
- `active_competences`: Competenze attive del fornitore
- `expired_competences`: Competenze scadute
- `expiring_competences`: Competenze in scadenza nei prossimi 90 giorni
- `missing_mandatory_competences`: Competenze obbligatorie mancanti per la categoria

**Documenti:**
- `valid_documents`: Documenti validi (approvati, verificati, non scaduti)
- `expired_documents`: Documenti scaduti
- `expiring_documents`: Documenti in scadenza (entro giorni preavviso)
- `missing_mandatory_documents`: Documenti obbligatori mancanti per la categoria
- `is_documentation_complete`: True se tutta la documentazione obbligatoria è completa e valida

## Admin Django

### Gestione Competenze
- Lista con filtri per categoria, obbligatorietà, scadenza
- Visualizzazione periodo rinnovo
- Conteggio fornitori che possiedono la competenza
- Azioni bulk: attiva/disattiva

### Gestione Documenti
- Lista con filtri per categoria, obbligatorietà
- Visualizzazione validità predefinita
- Conteggio documenti caricati
- Template e istruzioni

### Gestione Fornitori (estesa)
- **Inline VendorCompetence**: Gestisce competenze direttamente dal fornitore
- **Inline VendorDocument**: Gestisce documenti direttamente dal fornitore
- Visualizzazione stato competenze/documenti

### Gestione VendorCompetence
- Filtri per stato scadenza, verifica, categoria
- Visualizzazione colorata stato scadenza
- Autocomplete per vendor e competence

### Gestione VendorDocument
- Filtri per stato, categoria documento, scadenza
- Visualizzazione colorata stato e scadenza
- Azioni: approva, respingi, verifica
- Autocomplete per vendor e document_type

## Comandi Management

### populate_competences
Popola le 28 competenze iniziali dalla lista fornita.

```bash
python manage.py populate_competences
```

### populate_document_types
Popola i 22 tipi di documenti comuni.

```bash
python manage.py populate_document_types
```

## Utilizzo API

### Workflow tipico

1. **Creazione Competenze e Documenti** (già fatto con i comandi)
   ```bash
   python manage.py populate_competences
   python manage.py populate_document_types
   ```

2. **Associare competenze richieste a categorie**
   - Da admin: Category → seleziona categoria → aggiungi "required_competences"
   - Le competenze con `is_mandatory=True` saranno richieste

3. **Associare documenti richiesti a categorie**
   - Da admin: Category → seleziona categoria → aggiungi "required_documents"
   - I documenti con `is_mandatory=True` saranno richiesti

4. **Aggiungere competenze a un fornitore**
   - Da admin Vendor: apri fornitore → sezione "Vendor competences" (inline)
   - Oppure da VendorCompetence admin

5. **Caricare documenti di un fornitore**
   - Da admin Vendor: apri fornitore → sezione "Vendor documents" (inline)
   - Oppure da VendorDocument admin

6. **Verificare completezza fornitore**
   ```python
   vendor = Vendor.objects.get(id=...)
   
   # Competenze
   print(vendor.active_competences.count())
   print(vendor.expired_competences.count())
   print(vendor.missing_mandatory_competences.count())
   
   # Documenti
   print(vendor.valid_documents.count())
   print(vendor.expired_documents.count())
   print(vendor.is_documentation_complete)
   ```

## Esempio Query Utili

```python
from vendor_management_system.vendors.models import *

# Trovare fornitori con competenze scadute
vendors_with_expired = Vendor.objects.filter(
    vendor_competences__expiry_date__lt=timezone.now().date()
).distinct()

# Trovare fornitori senza RSPP
competence_rspp = Competence.objects.get(code='RSPP')
vendors_without_rspp = Vendor.objects.exclude(
    vendor_competences__competence=competence_rspp,
    vendor_competences__has_competence=True
)

# Trovare fornitori con DURC scaduto
durc_type = DocumentType.objects.get(code='DURC')
vendors_durc_expired = Vendor.objects.filter(
    vendor_documents__document_type=durc_type,
    vendor_documents__expiry_date__lt=timezone.now().date()
)

# Trovare fornitori con documentazione completa
vendors_compliant = [v for v in Vendor.objects.all() if v.is_documentation_complete]

# Report competenze per categoria
from django.db.models import Count
Competence.objects.values('competence_category').annotate(
    count=Count('id')
).order_by('competence_category')
```

## Notifiche e Alert (da implementare)

Il sistema è predisposto per implementare:
- Alert automatici per competenze in scadenza
- Alert per documenti in scadenza
- Dashboard con stato compliance fornitori
- Report periodici su scadenze

## Note Implementative

1. **File Upload**: I file sono salvati in:
   - `media/vendor_competences/YYYY/MM/` per certificati competenze
   - `media/vendor_documents/YYYY/MM/` per documenti fornitori
   - `media/document_templates/` per template documenti

2. **Validazione**: Il modello VendorDocument aggiorna automaticamente lo stato a EXPIRED se scaduto

3. **Performance**: Gli admin usano `select_related` e `prefetch_related` per ottimizzare le query

4. **Estendibilità**: È facile aggiungere nuove competenze e documenti tramite admin o comandi

## Prossimi Passi Suggeriti

1. Creare API REST endpoints per gestire competenze/documenti
2. Implementare sistema notifiche email per scadenze
3. Creare dashboard con stato compliance
4. Aggiungere report e statistiche
5. Implementare workflow approvazione documenti
6. Integrare con sistema di gestione ordini/contratti
