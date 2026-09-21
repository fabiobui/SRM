/*
 * Controllo duplicati Codice Embyon / Partita IVA / Codice Fiscale (AIDEV-21)
 * ----------------------------------------------------------------------------
 * Nel tab "Informazioni Base" del VendorAdmin, appena l'utente esce da uno dei
 * campi old_code, vat_number o fiscal_code, interroga in AJAX l'endpoint
 * duplicate-check/ e, se il valore è già usato da un altro fornitore, mostra
 * un banner rosso sotto il campo con un link al Codice Fornitore esistente.
 *
 * Il controllo è solo un aiuto immediato: la validazione vera e propria (che
 * blocca comunque il salvataggio anche a JS disattivato) è in
 * VendorAdminForm, lato server.
 */
(function () {
    'use strict';

    var FIELDS = [
        { id: 'id_old_code', name: 'old_code', label: null },
        { id: 'id_vat_number', name: 'vat_number', label: null },
        { id: 'id_fiscal_code', name: 'fiscal_code', label: null }
    ];

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        FIELDS.forEach(function (field) {
            var input = document.getElementById(field.id);
            if (!input) return; // Solo nelle change/add form del Vendor.

            // 'change' basta: scatta sia sul tab-out dopo digitazione manuale
            // (comportamento nativo dei campi testo) sia quando il modal di
            // ricerca Embyon (embyon_search.js) valorizza il campo via
            // dispatchEvent('change'). Aggiungere anche 'blur' duplicava la
            // chiamata (e quindi il banner) nel caso di digitazione manuale.
            input.addEventListener('change', function () {
                checkDuplicate(field, input.value);
            });
        });
    });

    // ----------------------------------------------------------------------

    function checkDuplicate(field, rawValue) {
        var value = (rawValue || '').trim();
        removeBanner(field.id);
        if (!value) return;

        var endpoint = window.VENDOR_DUPLICATE_CHECK_URL;
        if (!endpoint) return;

        var params = {
            field: field.name,
            value: value,
            pk: window.VENDOR_CURRENT_PK || ''
        };

        fetch(endpoint + '?' + toQuery(params), {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!data || !data.duplicate) return;
                showBanner(field, data);
            })
            .catch(function () {
                // Silenzioso: il controllo è solo un aiuto, la validazione
                // reale resta lato server al salvataggio.
            });
    }

    function showBanner(field, data) {
        var input = document.getElementById(field.id);
        if (!input) return;
        removeBanner(field.id); // idempotente: evita doppioni su risposte ravvicinate

        var banner = document.createElement('div');
        banner.id = 'duplicate-banner-' + field.id;
        banner.className = 'alert alert-danger';
        banner.style.cssText = 'margin-top:.5rem;padding:.5rem .75rem;font-size:.85rem;';

        var link = document.createElement('a');
        link.href = data.change_url;
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = gettextSafe('Codice Fornitore') + ' ' + data.vendor_code;

        banner.appendChild(document.createTextNode(
            gettextSafe('Valore già usato dal fornitore') + ' "' + data.vendor_name + '" ('
        ));
        banner.appendChild(link);
        banner.appendChild(document.createTextNode(').'));

        // Il campo old_code viene racchiuso da embyon_search.js in un
        // wrapper flex (input + bottone ricerca): il banner va appeso dopo
        // il .form-group che contiene tutto, non dopo il singolo input
        // (altrimenti finirebbe dentro la riga flex).
        var container = input.closest('.form-group') || input.parentNode;
        container.appendChild(banner);
    }

    function removeBanner(fieldId) {
        var existing = document.getElementById('duplicate-banner-' + fieldId);
        if (existing) existing.remove();
    }

    // ----------------------------------------------------------------------
    // Helpers (identici a embyon_search.js, per coerenza)

    function toQuery(obj) {
        return Object.keys(obj).map(function (k) {
            return encodeURIComponent(k) + '=' + encodeURIComponent(obj[k] || '');
        }).join('&');
    }

    function gettextSafe(s) {
        return (typeof window.gettext === 'function') ? window.gettext(s) : s;
    }
})();
