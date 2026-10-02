/*
 * Calcolo automatico Data di Scadenza (documenti e abilitazioni)
 * --------------------------------------------------------------
 * Nel VendorAdmin, quando l'utente inserisce la Data di Emissione/Rilascio
 * (o cambia il Tipo di Documento / il Requisito) di una riga dell'inline
 * Documenti o Abilitazioni, la Data di Scadenza viene calcolata come:
 *
 *     scadenza = emissione + validity_period_days (del tipo o requisito)
 *
 * La durata di validità in giorni viene caricata una volta dall'endpoint
 * admin `document-type-validity/` (documenti) o `competence-validity/`
 * (abilitazioni). I tipi senza rinnovo non hanno durata: nessun calcolo.
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

    // Un inline per ogni coppia (select del tipo, endpoint di validità).
    var GROUPS = [
        { typeField: 'document_type', endpoint: 'document-type-validity/' },
        { typeField: 'competence', endpoint: 'competence-validity/' }
    ];

    ready(function () {
        GROUPS.forEach(setupGroup);
    });

    function setupGroup(cfg) {
        var group = findGroup(cfg.typeField);
        if (!group) return;

        var endpoint = buildEndpoint(cfg.endpoint);
        if (!endpoint) return;

        var typeRe = new RegExp('-' + cfg.typeField + '$');
        var validityMap = {};   // { <id tipo>: {days, requires_renewal} }
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

            if (/-issue_date$/.test(t.name) || typeRe.test(t.name)) {
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
            var typeSelect = row.querySelector('select[name$="-' + cfg.typeField + '"]');
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
    }

    // ----------------------------------------------------------------------

    function findGroup(typeField) {
        var groups = document.querySelectorAll('.inline-group');
        for (var i = 0; i < groups.length; i++) {
            if (groups[i].querySelector('select[name$="-' + typeField + '"]')) {
                return groups[i];
            }
        }
        return null;
    }

    function buildEndpoint(path) {
        // .../vendors/vendor/<pk>/change/ oppure .../vendors/vendor/add/
        var m = window.location.pathname.match(/^(.*\/vendors\/vendor\/)/);
        if (!m) return null;
        return m[1] + path;
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
