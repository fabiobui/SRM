/*
 * Calcolo automatico Data di Scadenza documenti
 * ---------------------------------------------
 * Nel tab "Documentazione" del VendorAdmin, quando l'utente inserisce la
 * Data di Emissione (o cambia il Tipo di Documento) di una riga dell'inline
 * Documenti, la Data di Scadenza viene calcolata automaticamente come:
 *
 *     scadenza = emissione + validity_period_days (del tipo documento)
 *
 * La durata di validità in giorni di ogni tipo documento viene caricata una
 * volta dall'endpoint admin `document-type-validity/`.
 *
 * Rispetta le modifiche manuali: se l'utente edita a mano la Data di Scadenza,
 * quella riga non viene più ricalcolata in automatico.
 *
 * Funziona anche con le righe create dal "Set Documentale"
 * (document_set_applier.js), perché intercetta gli eventi `change` sui campi.
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
        var group = findDocumentsGroup();
        if (!group) return;

        var endpoint = buildEndpoint();
        if (!endpoint) return;

        var validityMap = {};   // { <document_type_id>: {days, requires_renewal} }
        var loaded = false;

        fetch(endpoint, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (r) { return r.ok ? r.json() : { types: {} }; })
            .then(function (data) {
                validityMap = (data && data.types) || {};
                loaded = true;
            })
            .catch(function () { /* silenzioso: nessun calcolo automatico */ });

        // Delegazione eventi: copre anche le righe aggiunte dinamicamente
        // (pulsante "Aggiungi un altro" e Set Documentale).
        group.addEventListener('change', function (ev) {
            var t = ev.target;
            if (!t || !t.name) return;

            if (/-issue_date$/.test(t.name) || /-document_type$/.test(t.name)) {
                var row = t.closest('tr');
                if (row) recalcRow(row);
            } else if (/-expiry_date$/.test(t.name)) {
                // Modifica manuale della scadenza: da qui in poi non ricalcolare.
                markManual(t);
            }
        });

        // Se l'utente digita direttamente nella scadenza, segnala l'override.
        group.addEventListener('input', function (ev) {
            var t = ev.target;
            if (t && t.name && /-expiry_date$/.test(t.name)) {
                markManual(t);
            }
        });

        function recalcRow(row) {
            if (!loaded) return;

            var issueInput = row.querySelector('input[name$="-issue_date"]');
            var expiryInput = row.querySelector('input[name$="-expiry_date"]');
            var typeSelect = row.querySelector('select[name$="-document_type"]');
            if (!issueInput || !expiryInput || !typeSelect) return;

            // Non sovrascrivere una scadenza modificata a mano dall'utente.
            if (expiryInput.dataset.manualEdit === '1') return;

            var typeId = typeSelect.value;
            var info = typeId ? validityMap[typeId] : null;
            if (!info || !info.days && info.days !== 0) return;

            var issued = parseLocalizedDate(issueInput.value);
            if (!issued) return;

            var expiry = new Date(issued.getTime());
            expiry.setDate(expiry.getDate() + Number(info.days));

            expiryInput.value = formatLikeInput(expiry, issueInput.value);
            // Segna come impostata dallo script (non manuale) e notifica il form.
            expiryInput.dataset.autoCalc = '1';
            expiryInput.dispatchEvent(new Event('change', { bubbles: true }));
        }

        function markManual(input) {
            // Se è il nostro stesso change automatico, ignora.
            if (input.dataset.autoCalc === '1') {
                delete input.dataset.autoCalc;
                return;
            }
            input.dataset.manualEdit = '1';
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
        // .../vendors/vendor/<pk>/change/ oppure .../vendors/vendor/add/
        var m = window.location.pathname.match(/^(.*\/vendors\/vendor\/)/);
        if (!m) return null;
        return m[1] + 'document-type-validity/';
    }

    // Interpreta una data dal formato admin italiano (gg/mm/aaaa) oppure ISO
    // (aaaa-mm-gg), gestendo i separatori '/', '-' e '.'.
    function parseLocalizedDate(value) {
        if (!value) return null;
        var s = String(value).trim();
        if (!s) return null;

        var iso = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
        if (iso) {
            return buildDate(iso[1], iso[2], iso[3]);
        }

        // gg[sep]mm[sep]aaaa  (formato di default locale 'it')
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
        // Scarta date non valide (es. 31/02).
        if (dt.getFullYear() !== year || dt.getMonth() !== month - 1 || dt.getDate() !== day) {
            return null;
        }
        return dt;
    }

    // Formatta la scadenza usando lo stesso schema (ordine e separatore) del
    // valore digitato nella Data di Emissione, così resta coerente col locale.
    function formatLikeInput(date, issueValue) {
        var yyyy = date.getFullYear();
        var mm = pad2(date.getMonth() + 1);
        var dd = pad2(date.getDate());

        var s = String(issueValue || '').trim();
        if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
            return yyyy + '-' + mm + '-' + dd;
        }
        var sepMatch = s.match(/^\d{1,2}([\/\-.])\d{1,2}\1\d{2,4}$/);
        var sep = sepMatch ? sepMatch[1] : '/';
        return dd + sep + mm + sep + yyyy;
    }

    function pad2(n) {
        return (n < 10 ? '0' : '') + n;
    }
})();
