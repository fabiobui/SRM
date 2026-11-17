# Tecnici/mezzi Subappaltatori Implementation Plan

> **For agentic workers:** implemented natively in this session (execution method: Native, scelto da me). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dare ai fornitori Subappaltatori due sezioni, "Tecnici" e "Mezzi/dotazioni", con documenti e scadenze, validate dal back office e gestibili anche dall'admin, con promemoria email.

**Architecture:** Nuova app Django `subcontractors` con i modelli (Technician, TechnicianDocument, Equipment, EquipmentDocument), la logica di storico ("documento più recente validato per tipo") e la integrazione nei promemoria. Viste portale nell'app `portal` (stesso pattern di `MyOperationalAttributesView`), inline admin su `VendorAdmin` visibili solo per Subappaltatori.

**Tech Stack:** Django, pytest-django, factory_boy, Bootstrap portale, ruff.

**Spec:** [docs/superpowers/specs/2026-11-17-tecnici-mezzi-design.md](../specs/2026-11-17-tecnici-mezzi-design.md)

## Global Constraints

- Visibilità solo se `Vendor.is_subappaltatore` è vero (portale e admin); URL altri fornitori → 404.
- Ogni email passa da `core/emails.py::send_templated_email`.
- Storico: rinnovo = nuovo documento; la scadenza considerata è quella del documento più recente validato per ogni tipo.
- Solo documenti `VALIDATED` generano promemoria; soglia primo promemoria = `REMINDER_DAYS_DEFAULT`, secondo = `settings.EXPIRY_REMINDER_SECOND_DAYS`.
- Documentazione e guide in italiano; guide operative aggiornate; test guida fornitori invariato.
- Ruff pulito sui file toccati.

## Review Focus

1. Fornitore non Subappaltatore che digita l'URL delle sezioni → 404, nessun dato.
2. Rinnovo di un attestato: il promemoria segue il nuovo documento, non il vecchio.
3. Documento senza data di scadenza per un tipo che la richiede → errore di validazione.
4. Documento `IN_ATTESA`/`RESPINTO` non genera promemoria.
5. Tecnico/mezzo di un fornitore cambiato da Subappaltatore a non Subappaltatore: nessuna sezione visibile, dati conservati.

---

### Task 1: App `subcontractors` — modelli e regole di validità

**Files:**
- Create: `vendor_management_system/subcontractors/__init__.py`, `apps.py`, `models.py`, `migrations/__init__.py`, `tests/__init__.py`, `tests/test_models.py`
- Modify: `config/settings.py` (INSTALLED_APPS)

**Interfaces:**
- Produces:
  - `Technician(vendor FK related_name="technicians", surname, first_name, role, badge, validation_status, rejection_note, created_at)`
  - `TechnicianDocument(technician FK related_name="documents", doc_type, issue_date, expiry_date null, file, validation_status, rejection_note, uploaded_at)`
  - `Equipment(vendor FK related_name="equipment_items", equipment_type, plate, serial_code, instrument, validation_status, rejection_note)`
  - `EquipmentDocument(equipment FK related_name="documents", doc_type, issue_date, expiry_date null, file, validation_status, rejection_note, uploaded_at)`
  - `VALIDATION_CHOICES = PENDING | VALIDATED | REJECTED` (stringhe `"PENDING"`, `"VALIDATED"`, `"REJECTED"`)
  - `TECHNICIAN_DOC_TYPES: dict[str, tuple[label, has_expiry]]` dalle righe dell'Excel; `EQUIPMENT_DOC_TYPES` idem.
  - `current_documents(parent_qs) -> list` restituisce, per (parent, doc_type), il documento più recente `VALIDATED` (ordinato per issue_date).

- [ ] **Step 1: Write failing tests** in `tests/test_models.py`: (a) `TechnicianDocument.clean()` solleva `ValidationError` se il tipo ha scadenza e `expiry_date` è vuoto; (b) `current_documents` ritorna solo il più recente validato per tipo, ignorando `PENDING`/`REJECTED`.
- [ ] **Step 2: Run** `uv run pytest vendor_management_system/subcontractors/tests/test_models.py -v` → FAIL (modulo mancante).
- [ ] **Step 3: Implement** modelli, `clean()` sui documenti, `current_documents`, app config; aggiungere `"vendor_management_system.subcontractors"` a INSTALLED_APPS.
- [ ] **Step 4: Run** `uv run makemigrations subcontractors` e i test → PASS.
- [ ] **Step 5: Commit** `feat: modelli tecnici e mezzi dei subappaltatori (AIDEV-187)`.

### Task 2: Promemoria di scadenza per tecnici e mezzi

**Files:**
- Modify: `vendor_management_system/vendors/models.py` (`ExpiryReminderLog.KIND_CHOICES`, nuove costanti `KIND_TECHNICIAN_DOCUMENT`, `KIND_EQUIPMENT_DOCUMENT`) + migrazione vendors
- Modify: `vendor_management_system/vendors/expiry_reminders.py` (`_candidates`)
- Test: `vendor_management_system/subcontractors/tests/test_expiry.py`

**Interfaces:**
- Consumes: `current_documents` (Task 1).

- [ ] **Step 1: Write failing tests**: un tecnico con attestato validato in scadenza entro soglia → compare in `due_items`; stesso documento `PENDING` → assente; documento rinnovato (nuovo VALIDATED più recente) → promemoria sul nuovo, non sul vecchio.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**: nuovi kind in `ExpiryReminderLog`, `_candidates` yield da `current_documents` per Technician e Equipment del fornitore (soglia `REMINDER_DAYS_DEFAULT`); migrazione choices.
- [ ] **Step 4: Run** i test promemoria esistenti + nuovi → PASS.
- [ ] **Step 5: Commit** `feat: promemoria scadenze per tecnici e mezzi (AIDEV-187)`.

### Task 3: Viste portale (Tecnici e Mezzi)

**Files:**
- Create: `vendor_management_system/portal/subcontractor_views.py`, `vendor_management_system/portal/forms_subcontractors.py`, templates in `vendor_management_system/portal/templates/portal/subcontractors/` (`technicians_list.html`, `technician_form.html`, `technician_detail.html`, `equipment_list.html`, `equipment_form.html`, `equipment_detail.html`)
- Modify: `vendor_management_system/portal/urls.py`, `vendor_management_system/portal/templates/portal/base_portal.html` (voci di menu condizionate a `user.vendor.is_subappaltatore`)
- Test: `vendor_management_system/portal/tests/test_subcontractors_portal.py`

**Interfaces:**
- Consumes: modelli Task 1. URL names: `portal:my-technicians`, `portal:my-technician-new`, `portal:my-technician-detail` (pk), `portal:my-technician-document-add` (pk), `portal:my-equipment`, `portal:my-equipment-new`, `portal:my-equipment-detail` (pk), `portal:my-equipment-document-add` (pk).
- Pattern: mixin `SubcontractorRequiredMixin(VendorRequiredMixin)` che risponde 404 se `not request.user.vendor.is_subappaltatore`. Ogni voce creata/modificata dal fornitore ha `validation_status=PENDING`.

- [ ] **Step 1: Write failing tests**: fornitore Subappaltatore crea tecnico (PENDING); fornitore non Subappaltatore → 404 su tutte le URL; documento con tipo a scadenza senza `expiry_date` → form errore; una voce di un altro fornitore non è accessibile (404).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** viste, form (ModelForm con `exclude` per vendor/status), template con Bootstrap, voci menu.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: sezioni Tecnici e Mezzi nel portale subappaltatori (AIDEV-187)`.

### Task 4: Admin — inline e validazione sul fornitore

**Files:**
- Modify: `vendor_management_system/subcontractors/admin.py` (inline `TechnicianInline`, `EquipmentInline`, con `TechnicianDocumentInline`, `EquipmentDocumentInline`, admin per validazione in massa)
- Modify: `vendor_management_system/vendors/admin.py` (`VendorAdmin.get_inline_instances` filtra gli inline quando `not obj.is_subappaltatore`)
- Test: `vendor_management_system/subcontractors/tests/test_admin.py`

- [ ] **Step 1: Write failing tests**: `VendorAdmin` per Subappaltatore include gli inline; per altro fornitore no; azione admin "Valida" imposta `VALIDATED`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement**.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: gestione admin di tecnici e mezzi per i subappaltatori (AIDEV-187)`.

### Task 5: Guide operative

**Files:**
- Modify: `vendor_management_system/templates/guide/vendor_body.html`, `admin_body.html` (+ chip `*_chips.html` se necessario)

- [ ] **Step 1: Run** `uv run pytest tests/test_guide_operative.py -v` → PASS baseline.
- [ ] **Step 2: Edit** le guide: sezione Tecnici/Mezzi (solo Subappaltatori), flusso di validazione, ruolo admin.
- [ ] **Step 3: Run** `uv run pytest tests/test_guide_operative.py -v` → PASS (nessun dato interno).
- [ ] **Step 4: Commit** `docs: guide operative per tecnici e mezzi (AIDEV-187)`.

### Task 6: Verifica finale

- [ ] **Step 1:** `uv run python manage.py makemigrations --check --dry-run` → "No changes detected".
- [ ] **Step 2:** `uv run ruff check` e `uv run ruff format --check` sui file toccati.
- [ ] **Step 3:** Suite fast: `DJANGO_SETTINGS_MODULE=config.settings_test LDAP_ENABLED=False uv run pytest --no-migrations` → tutto verde (eventuali test preesistenti rotti vanno segnalati).
- [ ] **Step 4:** Docker: `docker compose up -d`, `docker compose restart django`, poi `docker compose exec django pytest` (suite completa MySQL).
- [ ] **Step 5:** Verifica Playwright: utente di prova Subappaltatore e fornitore normale, creazione tecnico/mezzo, validazione admin; screenshot in `.playwright-mcp/`.
- [ ] **Step 6:** Lasciare Docker attivo su `http://localhost:8000/` per la verifica dell'utente.
