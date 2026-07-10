/*
 * Ricerca Codice Embyon
 * ---------------------
 * Aggiunge un'icona "cerca" accanto al campo "Codice Embyon" (old_code) nel
 * tab "Informazioni Base" del VendorAdmin. Cliccandola si apre un modal con i
 * campi di ricerca: Codice Embyon, Partita IVA, Codice Fiscale, Ragione sociale
 * e Provincia.
 *
 * NB: la logica di ricerca vera e propria (chiamata al backend + popolamento
 * dei risultati) è agganciata alla funzione `runSearch()` più in basso, che al
 * momento è un placeholder da completare.
 */
(function () {
    'use strict';

    var MODAL_ID = 'embyon-search-modal';

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        var input = document.getElementById('id_old_code');
        if (!input) return; // Solo nelle change/add form del Vendor.

        injectSearchButton(input);
        injectModal();
    });

    // ----------------------------------------------------------------------

    function injectSearchButton(input) {
        // Evita doppie iniezioni.
        if (document.getElementById('embyon-search-btn')) return;

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'embyon-search-btn';
        btn.className = 'btn btn-outline-secondary btn-sm';
        btn.title = gettextSafe('Cerca fornitore su Embyon');
        btn.style.cssText = 'flex:0 0 auto;';
        btn.innerHTML = '<i class="fas fa-search"></i>';

        // Racchiude il campo e il bottone in una riga flex, così il bottone
        // resta accanto al campo e il campo non occupa tutta la larghezza.
        var wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;align-items:center;gap:.5rem;';
        input.parentNode.insertBefore(wrap, input);
        input.style.flex = '0 1 400px';
        input.style.maxWidth = '400px';
        wrap.appendChild(input);
        wrap.appendChild(btn);

        btn.addEventListener('click', function () {
            openModal();
        });
    }

    function injectModal() {
        if (document.getElementById(MODAL_ID)) return;

        var wrap = document.createElement('div');
        wrap.innerHTML = [
            '<div class="modal fade" id="' + MODAL_ID + '" tabindex="-1" role="dialog" aria-hidden="true">',
            '  <div class="modal-dialog modal-lg" role="document">',
            '    <div class="modal-content">',
            '      <div class="modal-header">',
            '        <h4 class="modal-title">' + gettextSafe('Ricerca fornitore Embyon') + '</h4>',
            '        <button type="button" class="close" data-dismiss="modal" aria-label="' + gettextSafe('Chiudi') + '">',
            '          <span aria-hidden="true">&times;</span>',
            '        </button>',
            '      </div>',
            '      <div class="modal-body">',
            '        <form id="embyon-search-form" onsubmit="return false;">',
            '          <div class="form-row">',
            '            <div class="form-group col-md-4">',
            '              <label for="embyon-f-code">' + gettextSafe('Codice Embyon') + '</label>',
            '              <input type="text" class="form-control" id="embyon-f-code" name="old_code" autocomplete="off">',
            '            </div>',
            '            <div class="form-group col-md-4">',
            '              <label for="embyon-f-vat">' + gettextSafe('Partita IVA') + '</label>',
            '              <input type="text" class="form-control" id="embyon-f-vat" name="vat_number" autocomplete="off">',
            '            </div>',
            '            <div class="form-group col-md-4">',
            '              <label for="embyon-f-fiscal">' + gettextSafe('Codice Fiscale') + '</label>',
            '              <input type="text" class="form-control" id="embyon-f-fiscal" name="fiscal_code" autocomplete="off">',
            '            </div>',
            '          </div>',
            '          <div class="form-row">',
            '            <div class="form-group col-md-8">',
            '              <label for="embyon-f-name">' + gettextSafe('Ragione sociale') + '</label>',
            '              <input type="text" class="form-control" id="embyon-f-name" name="name" autocomplete="off">',
            '            </div>',
            '            <div class="form-group col-md-4">',
            '              <label for="embyon-f-province">' + gettextSafe('Provincia') + '</label>',
            '              <input type="text" class="form-control" id="embyon-f-province" name="province" autocomplete="off" disabled placeholder="' + gettextSafe('non disponibile') + '">',
            '              <small class="form-text text-muted">' + gettextSafe('Non disponibile per questa sorgente.') + '</small>',
            '            </div>',
            '          </div>',
            '          <div class="form-row">',
            '            <div class="col-12 d-flex align-items-center">',
            '              <button type="submit" class="btn btn-primary" id="embyon-search-submit">',
            '                <i class="fas fa-search"></i> ' + gettextSafe('Cerca'),
            '              </button>',
            '              <button type="button" class="btn btn-outline-secondary ml-2" id="embyon-search-reset">' + gettextSafe('Pulisci') + '</button>',
            '              <span class="text-muted ml-3" id="embyon-search-message" style="font-size:.85rem;"></span>',
            '            </div>',
            '          </div>',
            '        </form>',
            '        <hr>',
            '        <div class="table-responsive">',
            '          <table class="table table-sm table-hover" id="embyon-results-table">',
            '            <thead>',
            '              <tr>',
            '                <th>' + gettextSafe('Codice Embyon') + '</th>',
            '                <th>' + gettextSafe('Società') + '</th>',
            '                <th>' + gettextSafe('Ragione sociale') + '</th>',
            '                <th>' + gettextSafe('Partita IVA') + '</th>',
            '                <th>' + gettextSafe('Codice Fiscale') + '</th>',
            '                <th>' + gettextSafe('Provincia') + '</th>',
            '                <th>' + gettextSafe('Stato') + '</th>',
            '                <th></th>',
            '              </tr>',
            '            </thead>',
            '            <tbody id="embyon-results-body">',
            '              <tr><td colspan="8" class="text-muted text-center">' + gettextSafe('Nessun risultato. Imposta i filtri e premi Cerca.') + '</td></tr>',
            '            </tbody>',
            '          </table>',
            '        </div>',
            '      </div>',
            '      <div class="modal-footer">',
            '        <button type="button" class="btn btn-secondary" data-dismiss="modal">' + gettextSafe('Chiudi') + '</button>',
            '      </div>',
            '    </div>',
            '  </div>',
            '</div>'
        ].join('');

        document.body.appendChild(wrap.firstChild);

        var form = document.getElementById('embyon-search-form');
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            runSearch();
        });

        var reset = document.getElementById('embyon-search-reset');
        reset.addEventListener('click', function () {
            form.reset();
            clearResults();
            setMessage('');
        });

        wireMutualExclusion();
    }

    // Codice Embyon, Partita IVA, Codice Fiscale e Ragione sociale sono
    // mutuamente esclusivi: digitando in uno si azzerano gli altri tre.
    // La Provincia resta indipendente (filtro di restrizione).
    function wireMutualExclusion() {
        var ids = ['embyon-f-code', 'embyon-f-vat', 'embyon-f-fiscal', 'embyon-f-name'];
        ids.forEach(function (id) {
            var el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('input', function () {
                if (!el.value) return;
                ids.forEach(function (other) {
                    if (other === id) return;
                    var oe = document.getElementById(other);
                    if (oe) oe.value = '';
                });
            });
        });
    }

    // ----------------------------------------------------------------------

    function openModal() {
        // Precompila il Codice Embyon con il valore attuale del form, se presente.
        var current = document.getElementById('id_old_code');
        var field = document.getElementById('embyon-f-code');
        if (current && field && !field.value) {
            field.value = current.value || '';
        }

        var $ = window.jQuery || window.$;
        if ($ && typeof $.fn.modal === 'function') {
            $('#' + MODAL_ID).modal('show');
        } else {
            var el = document.getElementById(MODAL_ID);
            el.classList.add('show');
            el.style.display = 'block';
        }
    }

    function closeModal() {
        var $ = window.jQuery || window.$;
        if ($ && typeof $.fn.modal === 'function') {
            $('#' + MODAL_ID).modal('hide');
        } else {
            var el = document.getElementById(MODAL_ID);
            el.classList.remove('show');
            el.style.display = 'none';
        }
    }

    function getFilters() {
        return {
            old_code: valueOf('embyon-f-code'),
            vat_number: valueOf('embyon-f-vat'),
            fiscal_code: valueOf('embyon-f-fiscal'),
            name: valueOf('embyon-f-name'),
            province: valueOf('embyon-f-province')
        };
    }

    // ----------------------------------------------------------------------
    // Logica di ricerca: interroga l'endpoint embyon-search/ del VendorAdmin
    // con i filtri correnti e popola la tabella dei risultati.
    // ----------------------------------------------------------------------
    function runSearch() {
        var filters = getFilters();

        // Serve un criterio primario (la provincia da sola non basta).
        var primary = filters.old_code || filters.vat_number || filters.fiscal_code || filters.name;
        if (!primary) {
            setMessage(gettextSafe('Imposta un criterio: codice Embyon, partita IVA, codice fiscale o ragione sociale.'));
            return;
        }
        if (filters.name && filters.name.length < 3) {
            setMessage(gettextSafe('Inserisci almeno 3 caratteri per la ragione sociale.'));
            return;
        }

        var endpoint = buildEndpoint();
        if (!endpoint) {
            setMessage(gettextSafe('Impossibile determinare l\'endpoint di ricerca.'));
            return;
        }

        setMessage(gettextSafe('Ricerca in corso…'));
        clearResults();

        fetch(endpoint + '?' + toQuery(filters), {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (r) { return r.json().catch(function () { return {}; }); })
            .then(function (data) {
                if (data && data.error) {
                    setMessage(data.error);
                }
                renderResults((data && data.results) || []);
            })
            .catch(function () {
                setMessage(gettextSafe('Errore durante la ricerca.'));
            });
    }

    function buildEndpoint() {
        // Path della change/add form: .../vendors/vendor/<pk>/change/ oppure .../vendors/vendor/add/
        var m = window.location.pathname.match(/^(.*\/vendors\/vendor\/)/);
        if (!m) return null;
        return m[1] + 'embyon-search/';
    }

    function toQuery(obj) {
        return Object.keys(obj).map(function (k) {
            return encodeURIComponent(k) + '=' + encodeURIComponent(obj[k] || '');
        }).join('&');
    }

    // Popola la tabella dei risultati. `rows` è un array di oggetti con:
    // { old_code, company, name, vat_number, fiscal_code, province }
    function renderResults(rows) {
        var body = document.getElementById('embyon-results-body');
        if (!body) return;
        body.innerHTML = '';

        if (!rows || !rows.length) {
            body.innerHTML = '<tr><td colspan="8" class="text-muted text-center">' +
                gettextSafe('Nessun risultato trovato.') + '</td></tr>';
            setMessage('');
            return;
        }

        rows.forEach(function (row) {
            var tr = document.createElement('tr');
            tr.appendChild(cell(row.old_code));
            tr.appendChild(cell(row.company));
            tr.appendChild(cell(row.name));
            tr.appendChild(cell(row.vat_number));
            tr.appendChild(cell(row.fiscal_code));
            tr.appendChild(cell(row.province));
            tr.appendChild(cell(row.status));

            var actionTd = document.createElement('td');
            var pick = document.createElement('button');
            pick.type = 'button';
            pick.className = 'btn btn-sm btn-success';
            pick.textContent = gettextSafe('Seleziona');
            pick.addEventListener('click', function () { selectResult(row); });
            actionTd.appendChild(pick);
            tr.appendChild(actionTd);

            body.appendChild(tr);
        });
        setMessage(interpolate(gettextSafe('%s risultati.'), [rows.length]));
    }

    // Applica il risultato scelto ai rispettivi campi del form Vendor.
    function selectResult(row) {
        setFieldValue('id_old_code', row.old_code);
        setFieldValue('id_name', row.name);
        setFieldValue('id_vat_number', row.vat_number);
        setFieldValue('id_fiscal_code', row.fiscal_code);
        setFieldValue('id_email', row.email);
        setFieldValue('id_phone', row.phone);
        setSelectValue('id_vendor_type', row.vendor_type);
        // Flag "Attivo su Embyon": spuntato solo se lo stato Embyon è "attivo".
        setCheckbox('id_embyon_active', !!row.embyon_active);
        closeModal();
    }

    // Imposta lo stato di un checkbox del form.
    function setCheckbox(id, checked) {
        var el = document.getElementById(id);
        if (!el || el.type !== 'checkbox') return;
        el.checked = !!checked;
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // Imposta il valore di una <select> solo se l'opzione esiste.
    function setSelectValue(id, value) {
        var el = document.getElementById(id);
        if (!el || !value) return;
        var found = false;
        for (var i = 0; i < el.options.length; i++) {
            if (el.options[i].value === value) { found = true; break; }
        }
        if (!found) return;
        el.value = value;
        var $ = window.jQuery || window.$;
        if ($ && $.fn && $.fn.select2) {
            $(el).trigger('change');
        } else {
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function clearResults() {
        var body = document.getElementById('embyon-results-body');
        if (body) {
            body.innerHTML = '<tr><td colspan="8" class="text-muted text-center">' +
                gettextSafe('Nessun risultato. Imposta i filtri e premi Cerca.') + '</td></tr>';
        }
    }

    // ----------------------------------------------------------------------
    // Helpers

    function cell(text) {
        var td = document.createElement('td');
        td.textContent = (text == null) ? '' : String(text);
        return td;
    }

    function valueOf(id) {
        var el = document.getElementById(id);
        return el ? el.value.trim() : '';
    }

    function setFieldValue(id, value) {
        var el = document.getElementById(id);
        if (!el) return;
        // Non sovrascrive i campi del form con valori vuoti provenienti da Embyon.
        if (value == null || value === '') return;
        el.value = value;
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function setMessage(text) {
        var el = document.getElementById('embyon-search-message');
        if (el) el.textContent = text || '';
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
