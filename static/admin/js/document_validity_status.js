/*
 * Stato validità documenti (live)
 * -------------------------------
 * Nel tab "Documentazione" del VendorAdmin aggiorna in tempo reale la colonna
 * "Stato validità" (campo readonly expiry_status_display) al variare dello
 * "Stato lavorazione" o delle date, replicando la logica server:
 *
 *   - Stato lavorazione != 'Approvato'      -> NOT VALID (rosso)
 *   - Approvato, scaduto                     -> EXPIRED (rosso)
 *   - Approvato, in scadenza (<= reminder)   -> EXPIRING_SOON (arancione)
 *   - Approvato, altrimenti                  -> VALID (verde)
 *
 * Il valore autoritativo resta quello calcolato dal server al salvataggio;
 * questo è solo un'anteprima immediata per l'utente. Funziona anche con le
 * righe create dal Set Documentale e con quelle aggiunte a mano.
 */
(function () {
    'use strict';

    var APPROVED = 'APPROVED';

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        var group = findDocumentsGroup();
        if (!group) return;

        var validityMap = {};   // { <document_type_id>: {reminder, days, ...} }
        var endpoint = buildEndpoint();

        // Ricalcolo su qualsiasi cambio di stato / date / tipo documento.
        group.addEventListener('change', function (ev) {
            var t = ev.target;
            if (!t || !t.name) return;
            if (/-status$/.test(t.name) || /-issue_date$/.test(t.name) ||
                /-expiry_date$/.test(t.name) || /-document_type$/.test(t.name)) {
                var row = t.closest('tr');
                if (row) updateRow(row);
            }
        });

        // Primo passaggio con i dati già presenti (lo stato NOT VALID non
        // dipende dal reminder, quindi è già corretto da subito).
        eachDataRow(updateRow);

        if (endpoint) {
            fetch(endpoint, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                .then(function (r) { return r.ok ? r.json() : { types: {} }; })
                .then(function (data) {
                    validityMap = (data && data.types) || {};
                    // Ripassa: ora possiamo distinguere EXPIRING_SOON dal reminder.
                    eachDataRow(updateRow);
                })
                .catch(function () { /* anteprima best-effort */ });
        }

        function updateRow(row) {
            var cell = row.querySelector('td.field-expiry_status_display');
            var statusSel = row.querySelector('select[name$="-status"]');
            if (!cell || !statusSel) return;

            var text, color;
            if (statusSel.value !== APPROVED) {
                text = 'NOT VALID';
                color = 'red';
            } else {
                var expiryInput = row.querySelector('input[name$="-expiry_date"]');
                var typeSel = row.querySelector('select[name$="-document_type"]');
                var info = (typeSel && typeSel.value) ? validityMap[typeSel.value] : null;
                var reminder = (info && typeof info.reminder === 'number') ? info.reminder : 0;

                var expiry = parseLocalizedDate(expiryInput ? expiryInput.value : '');
                if (!expiry) {
                    text = 'VALID';
                    color = 'green';
                } else {
                    var today = startOfDay(new Date());
                    var days = Math.round((startOfDay(expiry).getTime() - today.getTime()) / 86400000);
                    if (days < 0) {
                        text = 'EXPIRED';
                        color = 'red';
                    } else if (days <= reminder) {
                        text = 'EXPIRING_SOON';
                        color = 'orange';
                    } else {
                        text = 'VALID';
                        color = 'green';
                    }
                }
            }
            renderCell(cell, text, color);
        }
    });

    // ----------------------------------------------------------------------

    function renderCell(cell, text, color) {
        var span = cell.querySelector('span.doc-validity-status');
        if (!span) {
            cell.textContent = '';
            span = document.createElement('span');
            span.className = 'doc-validity-status';
            cell.appendChild(span);
        }
        span.style.color = color;
        span.style.fontWeight = 'bold';
        span.textContent = text;
    }

    function eachDataRow(fn) {
        var rows = group_rows();
        for (var i = 0; i < rows.length; i++) fn(rows[i]);
    }

    var _group = null;
    function group_rows() {
        if (!_group) return [];
        var out = [];
        var rows = _group.querySelectorAll('tr');
        for (var i = 0; i < rows.length; i++) {
            var id = rows[i].id || '';
            // Salta la riga template (empty-form) e le intestazioni.
            if (id.indexOf('__prefix__') !== -1 || /-empty$/.test(id)) continue;
            if (rows[i].querySelector('select[name$="-status"]')) out.push(rows[i]);
        }
        return out;
    }

    function findDocumentsGroup() {
        var groups = document.querySelectorAll('.inline-group');
        for (var i = 0; i < groups.length; i++) {
            if (groups[i].querySelector('select[name$="-document_type"]')) {
                _group = groups[i];
                return groups[i];
            }
        }
        _group = document.getElementById('documents-group');
        return _group;
    }

    function buildEndpoint() {
        var m = window.location.pathname.match(/^(.*\/vendors\/vendor\/)/);
        if (!m) return null;
        return m[1] + 'document-type-validity/';
    }

    function startOfDay(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate());
    }

    // Data dal formato admin italiano (gg/mm/aaaa) o ISO (aaaa-mm-gg).
    function parseLocalizedDate(value) {
        if (!value) return null;
        var s = String(value).trim();
        if (!s) return null;

        var iso = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (iso) return buildDate(iso[1], iso[2], iso[3]);

        var dmy = s.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})$/);
        if (dmy) {
            var year = dmy[3];
            if (year.length === 2) year = '20' + year;
            return buildDate(year, dmy[2], dmy[1]);
        }
        return null;
    }

    function buildDate(y, m, d) {
        var year = Number(y), month = Number(m), day = Number(d);
        if (!year || !month || !day) return null;
        var dt = new Date(year, month - 1, day);
        if (dt.getFullYear() !== year || dt.getMonth() !== month - 1 || dt.getDate() !== day) {
            return null;
        }
        return dt;
    }
})();
