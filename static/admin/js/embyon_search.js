/*
 * Ricerca fornitore (lente)
 * -------------------------
 * Aggiunge un'icona "cerca" accanto al campo "Codice SAGE" nel tab
 * "Informazioni Base" del VendorAdmin (sezione Comune e creazione). Il modal cerca nelle viste
 * FABRIC_HUB dei fornitori condivisi tra società (v_suppliers e
 * v_supplier_companies) per ragione sociale, codice Embyon, codice SAGE,
 * partita IVA o codice fiscale.
 *
 * Il codice SAGE identifica il fornitore tra tutte le società:
 * - se il fornitore è già censito non se ne crea un altro: si apre il
 *   fornitore esistente aggiungendo, se manca, la sezione della società;
 * - altrimenti il risultato precompila il form del nuovo fornitore (codice
 *   SAGE e conti compresi); al salvataggio nascono la sezione Comune e
 *   quella della società scelta.
 */
(function () {
    'use strict';

    var MODAL_ID = 'embyon-search-modal';
    var FIELDS = [
        ['embyon-f-name', 'name'],
        ['embyon-f-code', 'account_code'],
        ['embyon-f-sage', 'sage_code'],
        ['embyon-f-vat', 'vat_number'],
        ['embyon-f-fiscal', 'fiscal_code']
    ];

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        // Solo nella sezione Comune o in creazione: nelle sezioni delle
        // società il codice SAGE è solo informativo.
        if (window.VENDOR_SECTION && window.VENDOR_SECTION !== 'COMUNE') return;
        var target = sageTarget();
        if (!target) return; // Solo nelle change/add form del Vendor.

        injectSearchButton(target);
        injectModal();
    });

    // Il campo codice SAGE: input in creazione, testo in sola lettura sulla
    // scheda di un fornitore già censito.
    function sageTarget() {
        var input = document.getElementById('id_sage_code');
        if (input) return input;
        var row = document.querySelector('.field-sage_code');
        return row ? row.querySelector('.readonly') : null;
    }

    function currentSage() {
        var target = sageTarget();
        if (!target) return '';
        var value = (target.value !== undefined ? target.value : target.textContent) || '';
        value = value.trim();
        return value === '-' ? '' : value;
    }

    // ----------------------------------------------------------------------

    function injectSearchButton(input) {
        if (document.getElementById('embyon-search-btn')) return;

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'embyon-search-btn';
        btn.className = 'btn btn-outline-secondary btn-sm';
        btn.title = gettextSafe('Cerca fornitore (Embyon / SAGE)');
        btn.style.cssText = 'flex:0 0 auto;';
        btn.innerHTML = '<i class="fas fa-search"></i>';

        var wrap = document.createElement('div');
        wrap.style.cssText = 'display:flex;align-items:center;gap:.5rem;';
        input.parentNode.insertBefore(wrap, input);
        input.style.flex = '0 1 400px';
        input.style.maxWidth = '400px';
        wrap.appendChild(input);
        wrap.appendChild(btn);

        btn.addEventListener('click', openModal);
    }

    function field(id, label, cols) {
        return '<div class="form-group col-md-' + cols + '">' +
            '<label for="' + id + '">' + gettextSafe(label) + '</label>' +
            '<input type="text" class="form-control" id="' + id + '" autocomplete="off">' +
            '</div>';
    }

    function injectModal() {
        if (document.getElementById(MODAL_ID)) return;

        var wrap = document.createElement('div');
        wrap.innerHTML = [
            '<div class="modal fade" id="' + MODAL_ID + '" tabindex="-1" role="dialog" aria-hidden="true">',
            '  <div class="modal-dialog modal-xl" role="document">',
            '    <div class="modal-content">',
            '      <div class="modal-header">',
            '        <h4 class="modal-title">' + gettextSafe('Ricerca fornitore') + '</h4>',
            '        <button type="button" class="close" data-dismiss="modal" aria-label="' + gettextSafe('Chiudi') + '">',
            '          <span aria-hidden="true">&times;</span>',
            '        </button>',
            '      </div>',
            '      <div class="modal-body">',
            '        <form id="embyon-search-form" onsubmit="return false;">',
            '          <div class="form-row">',
            field('embyon-f-name', 'Ragione sociale', 6),
            field('embyon-f-code', 'Codice Embyon', 3),
            field('embyon-f-sage', 'Codice SAGE', 3),
            '          </div>',
            '          <div class="form-row">',
            field('embyon-f-vat', 'Partita IVA', 4),
            field('embyon-f-fiscal', 'Codice Fiscale', 4),
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
            '                <th>' + gettextSafe('Codice SAGE') + '</th>',
            '                <th>' + gettextSafe('Ragione sociale') + '</th>',
            '                <th>' + gettextSafe('Partita IVA') + '</th>',
            '                <th>' + gettextSafe('Codice Fiscale') + '</th>',
            '                <th>' + gettextSafe('Provincia') + '</th>',
            '                <th>' + gettextSafe('Società e codici Embyon') + '</th>',
            '                <th></th>',
            '              </tr>',
            '            </thead>',
            '            <tbody id="embyon-results-body"></tbody>',
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
        clearResults();

        var form = document.getElementById('embyon-search-form');
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            runSearch();
        });
        document.getElementById('embyon-search-reset').addEventListener('click', function () {
            form.reset();
            clearResults();
            setMessage('');
        });
        wireMutualExclusion();
    }

    // I criteri sono mutuamente esclusivi: digitando in uno si azzerano gli altri.
    function wireMutualExclusion() {
        FIELDS.forEach(function (pair) {
            var el = document.getElementById(pair[0]);
            el.addEventListener('input', function () {
                if (!el.value) return;
                FIELDS.forEach(function (other) {
                    if (other[0] !== pair[0]) document.getElementById(other[0]).value = '';
                });
            });
        });
    }

    // ----------------------------------------------------------------------

    function openModal() {
        var sage = document.getElementById('embyon-f-sage');
        if (sage && !sage.value) sage.value = currentSage();

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
        var filters = {};
        FIELDS.forEach(function (pair) { filters[pair[1]] = valueOf(pair[0]); });
        return filters;
    }

    function runSearch() {
        var filters = getFilters();
        var primary = FIELDS.some(function (pair) { return filters[pair[1]]; });
        if (!primary) {
            setMessage(gettextSafe('Imposta un criterio: ragione sociale, codice Embyon, codice SAGE, partita IVA o codice fiscale.'));
            return;
        }
        if (filters.name && filters.name.length < 3) {
            setMessage(gettextSafe('Inserisci almeno 3 caratteri per la ragione sociale.'));
            return;
        }
        var endpoint = window.EMBYON_SEARCH_URL;
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
            .then(function (r) {
                return r.text().then(function (t) {
                    var data = null;
                    try { data = JSON.parse(t); } catch (e) { /* non-JSON */ }
                    return { status: r.status, data: data };
                });
            })
            .then(function (res) {
                if (!res.data) {
                    setMessage(gettextSafe('Errore server') + ' (HTTP ' + res.status + ')');
                    return;
                }
                if (res.data.error) {
                    setMessage(res.data.error);
                    return;
                }
                renderResults(res.data.results || [], res.data.user_company || '');
            })
            .catch(function () {
                setMessage(gettextSafe('Errore durante la ricerca.'));
            });
    }

    function toQuery(obj) {
        return Object.keys(obj).map(function (k) {
            return encodeURIComponent(k) + '=' + encodeURIComponent(obj[k] || '');
        }).join('&');
    }

    // Società per cui si sta censendo il fornitore: quella scelta nel form
    // (solo in creazione) o, in mancanza, quella dell'utente.
    function chosenCompany(userCompany) {
        var select = document.getElementById('id_initial_company');
        return (select && select.value) || userCompany || '';
    }

    function companiesCell(row) {
        var td = document.createElement('td');
        (row.companies || []).forEach(function (c) {
            var line = document.createElement('div');
            line.className = 'small';
            line.textContent = c.company + ': ' + c.account_code + (c.status ? ' (' + c.status + ')' : '');
            td.appendChild(line);
        });
        if (!td.childNodes.length) td.textContent = '-';
        return td;
    }

    function renderResults(rows, userCompany) {
        var body = document.getElementById('embyon-results-body');
        body.innerHTML = '';
        if (!rows.length) {
            body.innerHTML = '<tr><td colspan="7" class="text-muted text-center">' +
                gettextSafe('Nessun risultato trovato.') + '</td></tr>';
            setMessage('');
            return;
        }
        rows.forEach(function (row) {
            var tr = document.createElement('tr');
            tr.appendChild(cell(row.sage_code));
            tr.appendChild(cell(row.name));
            tr.appendChild(cell(row.vat_number));
            tr.appendChild(cell(row.fiscal_code));
            tr.appendChild(cell(row.province));
            tr.appendChild(companiesCell(row));
            tr.appendChild(actionCell(row, userCompany));
            body.appendChild(tr);
        });
        setMessage(interpolate(gettextSafe('%s risultati.'), [rows.length]));
    }

    function button(label, css, onClick) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'btn btn-sm ' + css;
        b.textContent = gettextSafe(label);
        b.addEventListener('click', onClick);
        return b;
    }

    function actionCell(row, userCompany) {
        var td = document.createElement('td');
        var current = window.VENDOR_CURRENT_PK || '';
        var existing = row.existing_vendor;
        var company = chosenCompany(userCompany);

        if (existing && existing.pk === current) {
            td.appendChild(badge(gettextSafe('Fornitore corrente'), 'info'));
            return td;
        }
        if (existing) {
            // Già censito: niente doppione, si apre l'esistente aggiungendo
            // (se manca) la sezione della società.
            td.appendChild(badge(gettextSafe('Già censito: ') + existing.name, 'warning'));
            var missing = company && existing.sections.indexOf(company) === -1;
            var label = missing ? 'Aggiungi sezione ' + company : 'Apri fornitore';
            td.appendChild(document.createElement('br'));
            td.appendChild(button(label, 'btn-warning mt-1', function () {
                linkSage(existing.pk, row, missing ? company : '');
            }));
            return td;
        }
        if (current) {
            // Scheda di un fornitore esistente senza codice SAGE: collega.
            td.appendChild(button('Collega a questo fornitore', 'btn-success', function () {
                linkSage(current, row, '');
            }));
            return td;
        }
        td.appendChild(button('Seleziona', 'btn-success', function () { selectResult(row, company); }));
        return td;
    }

    function badge(text, kind) {
        var span = document.createElement('span');
        span.className = 'badge badge-' + kind;
        span.textContent = text;
        return span;
    }

    function csrfToken() {
        var el = document.querySelector('input[name=csrfmiddlewaretoken]');
        return el ? el.value : '';
    }

    function linkSage(vendorPk, row, company) {
        var data = new FormData();
        data.append('vendor', vendorPk);
        data.append('sage_code', row.sage_code);
        data.append('company', company || '');
        data.append('accounts', JSON.stringify(row.companies || []));
        fetch(window.VENDOR_LINK_SAGE_URL, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': csrfToken() },
            body: data
        })
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (res.url) {
                    window.location.href = res.url;
                } else {
                    setMessage(res.error || gettextSafe('Collegamento non riuscito.'));
                }
            })
            .catch(function () { setMessage(gettextSafe('Collegamento non riuscito.')); });
    }

    // Precompila il form del nuovo fornitore con il risultato scelto.
    function selectResult(row, company) {
        setFieldValue('id_sage_code', row.sage_code);
        setFieldValue('id_name', row.name);
        setFieldValue('id_vat_number', row.vat_number);
        setFieldValue('id_fiscal_code', row.fiscal_code);
        setFieldValue('id_email', row.email);
        setFieldValue('id_phone', row.phone);
        var accounts = document.getElementById('id_sage_accounts');
        if (accounts) accounts.value = JSON.stringify(row.companies || []);
        closeModal();
    }

    function clearResults() {
        var body = document.getElementById('embyon-results-body');
        if (body) {
            body.innerHTML = '<tr><td colspan="7" class="text-muted text-center">' +
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
        if (!el || value == null || value === '') return;
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
