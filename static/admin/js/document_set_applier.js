/*
 * Set Documentale applier
 * -----------------------
 * Aggiunge nel tab "Documenti" del VendorAdmin un dropdown con i Set Documentali
 * (modello documents.DocumentSet). Scegliendo un set e cliccando "Applica set",
 * vengono create al volo (lato client) le righe dell'inline Documenti per ogni
 * tipo di documento del set, impostando lo stato predefinito del set.
 * Le righe vengono persistite al salvataggio normale del form.
 */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        // Solo nelle change/add form del Vendor (presenza dell'inline Documenti).
        var group = findDocumentsGroup();
        if (!group) return;

        var prefix = group.id.replace(/-group$/, '');
        var endpoint = buildEndpoint();
        if (!endpoint) return;

        var ui = injectControls(group);
        var setsMap = {};

        // Carica i set documentali pertinenti.
        fetch(endpoint, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.ok ? r.json() : { sets: [] }; })
            .then(function (data) {
                var sets = (data && data.sets) || [];
                if (!sets.length) {
                    ui.select.innerHTML = '<option value="">' + gettextSafe('Nessun set disponibile') + '</option>';
                    ui.select.disabled = true;
                    ui.button.disabled = true;
                    return;
                }
                sets.forEach(function (s) {
                    setsMap[String(s.id)] = s;
                    var opt = document.createElement('option');
                    opt.value = String(s.id);
                    opt.textContent = s.name;
                    ui.select.appendChild(opt);
                });
            })
            .catch(function () {
                ui.message.textContent = gettextSafe('Errore nel caricamento dei set documentali.');
            });

        ui.button.addEventListener('click', function () {
            var setId = ui.select.value;
            if (!setId || !setsMap[setId]) {
                ui.message.textContent = gettextSafe('Seleziona un set documentale.');
                return;
            }
            applySet(setsMap[setId]);
        });

        // ------------------------------------------------------------------

        function applySet(set) {
            var types = set.document_types || [];
            var defaultStatus = set.default_status || 'PENDING';

            var existing = collectExistingTypeIds();
            var emptyRows = collectEmptyRows();

            var added = 0, skipped = 0;
            types.forEach(function (dt) {
                var id = String(dt.id);
                if (existing.has(id)) { skipped += 1; return; }

                var row = emptyRows.length ? emptyRows.shift() : addRow();
                if (!row) { return; }

                setDocumentType(row, dt.id, dt.text);
                setStatus(row, defaultStatus);
                existing.add(id);
                added += 1;
            });

            var parts = [];
            parts.push(interpolate(gettextSafe('Aggiunte %s righe'), [added]));
            if (skipped) parts.push(interpolate(gettextSafe('%s già presenti'), [skipped]));
            ui.message.textContent = parts.join(', ') + '. ' + gettextSafe('Ricordati di salvare.');
        }

        // Righe esistenti (non template, non in cancellazione) con un tipo già scelto.
        function collectExistingTypeIds() {
            var set = new Set();
            rowSelects('-document_type').forEach(function (sel) {
                var row = sel.closest('tr');
                if (isDeleted(row)) return;
                if (sel.value) set.add(String(sel.value));
            });
            return set;
        }

        // Righe esistenti senza tipo documento (riutilizzabili: es. la riga extra vuota).
        function collectEmptyRows() {
            var rows = [];
            rowSelects('-document_type').forEach(function (sel) {
                var row = sel.closest('tr');
                if (isDeleted(row)) return;
                if (!sel.value) rows.push(row);
            });
            return rows;
        }

        function rowSelects(suffix) {
            var out = [];
            var selects = group.querySelectorAll('select[name$="' + suffix + '"]');
            for (var i = 0; i < selects.length; i++) {
                var name = selects[i].getAttribute('name') || '';
                // Esclude la riga template (empty-form).
                if (name.indexOf('__prefix__') !== -1) continue;
                out.push(selects[i]);
            }
            return out;
        }

        function isDeleted(row) {
            if (!row) return true;
            var del = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
            return !!(del && del.checked);
        }

        // Crea una nuova riga cliccando il link "Aggiungi un altro" di Django
        // e ne restituisce l'elemento <tr> appena inserito (individuato per diff,
        // così è indipendente dallo schema di indicizzazione di inlines.js).
        function addRow() {
            var link = group.querySelector('.add-row a') ||
                       group.querySelector('a.addlink') ||
                       group.querySelector('.add-row');
            if (!link) return null;

            var before = {};
            forEachRow(function (tr) { before[tr.id] = true; });

            link.click();

            var added = null;
            forEachRow(function (tr) {
                if (tr.id === prefix + '-empty') return;
                if (!before[tr.id]) added = tr;
            });
            return added;
        }

        function forEachRow(fn) {
            var rows = group.querySelectorAll('tr[id^="' + prefix + '-"]');
            for (var i = 0; i < rows.length; i++) fn(rows[i]);
        }

        function setDocumentType(row, id, text) {
            var sel = row.querySelector('select[name$="-document_type"]');
            if (!sel) return;
            var dj = window.django && window.django.jQuery;
            if (dj) {
                var $sel = dj(sel);
                if ($sel.find("option[value='" + id + "']").length === 0) {
                    // Per i widget autocomplete (select2 AJAX) aggiungiamo l'option.
                    $sel.append(new Option(text, id, true, true));
                } else {
                    $sel.val(id);
                }
                $sel.trigger('change');
            } else {
                if (!sel.querySelector("option[value='" + id + "']")) {
                    var opt = new Option(text, id, true, true);
                    sel.appendChild(opt);
                }
                sel.value = id;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        function setStatus(row, status) {
            var sel = row.querySelector('select[name$="-status"]');
            if (sel) {
                sel.value = status;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }
    });

    // ----------------------------------------------------------------------

    function findDocumentsGroup() {
        var groups = document.querySelectorAll('.inline-group');
        for (var i = 0; i < groups.length; i++) {
            if (groups[i].querySelector('select[name$="-document_type"]')) {
                return groups[i];
            }
        }
        return document.getElementById('documents-group');
    }

    function buildEndpoint() {
        // Path della change/add form: .../vendors/vendor/<pk>/change/ oppure .../vendors/vendor/add/
        var m = window.location.pathname.match(/^(.*\/vendors\/vendor\/)/);
        if (!m) return null;
        var base = m[1];
        var url = base + 'document-sets/';
        var vm = window.location.pathname.match(/\/vendors\/vendor\/([^/]+)\/change/);
        if (vm && vm[1] && vm[1] !== 'add') {
            url += '?vendor=' + encodeURIComponent(vm[1]);
        }
        return url;
    }

    function injectControls(group) {
        var wrap = document.createElement('div');
        wrap.className = 'docset-applier';
        wrap.style.cssText = 'display:flex;align-items:center;flex-wrap:wrap;gap:.5rem;margin:.5rem 0 1rem;';

        var label = document.createElement('label');
        label.textContent = gettextSafe('Set Documentale') + ':';
        label.style.cssText = 'margin:0;font-weight:600;';

        var select = document.createElement('select');
        select.className = 'form-control';
        select.style.width = 'auto';
        select.innerHTML = '<option value="">---------</option>';

        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-info btn-sm';
        button.textContent = gettextSafe('Applica set');

        var message = document.createElement('span');
        message.className = 'docset-message text-muted';
        message.style.cssText = 'font-size:.85rem;';

        wrap.appendChild(label);
        wrap.appendChild(select);
        wrap.appendChild(button);
        wrap.appendChild(message);

        // Inserisce il controllo in cima al gruppo inline (tab Documenti).
        var related = group.querySelector('.inline-related') || group;
        related.insertBefore(wrap, related.firstChild);

        return { select: select, button: button, message: message };
    }

    function gettextSafe(s) {
        return (typeof window.gettext === 'function') ? window.gettext(s) : s;
    }

    function interpolate(fmt, args) {
        if (typeof window.interpolate === 'function') {
            return window.interpolate(fmt, args);
        }
        var i = 0;
        return fmt.replace(/%s/g, function () { return args[i++]; });
    }
})();
