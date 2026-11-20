/*
 * Avviso documento/requisito già presente in un'altra sezione
 * ----------------------------------------------------------
 * Nella scheda fornitore (sezione Comune o di una società), quando si
 * sceglie il tipo di un documento o di un requisito nuovo, chiede al server
 * se lo stesso tipo è già caricato in un'ALTRA sezione dello stesso
 * fornitore (es. il DURC già caricato da un'altra società). In quel caso
 * mostra una modale di avviso: l'utente può annullare o procedere comunque.
 * Segnala anche i tipi "comuni" scelti dentro la sezione di una società.
 */
(function () {
    'use strict';

    var MODAL_ID = 'section-duplicate-modal';
    var SELECTORS = 'select[name$="-document_type"], select[name$="-competence"]';
    var lastChecked = {};

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        if (!window.SECTION_DUPLICATES_URL) return;
        injectModal();
        // L'autocomplete (select2) dell'admin notifica il cambio con
        // django.jQuery: un listener nativo non lo vedrebbe.
        [window.django && window.django.jQuery, window.jQuery].forEach(function ($) {
            if (!$) return;
            $(document).on('change', SELECTORS, function () { check(this); });
        });
    });

    function kindOf(select) {
        if (/-document_type$/.test(select.name)) return 'document';
        if (/-competence$/.test(select.name)) return 'competence';
        return null;
    }

    // Solo le righe nuove: quelle già salvate hanno l'id valorizzato e non
    // vanno segnalate (select2 emette "change" anche all'apertura).
    function isNewRow(select) {
        var prefix = select.name.replace(/-(document_type|competence)$/, '');
        var id = document.querySelector('input[name="' + prefix + '-id"]');
        return !id || !id.value;
    }

    function check(select) {
        var kind = kindOf(select);
        var value = select.value;
        if (!kind || !value || !isNewRow(select)) return;
        // Stesso select e stesso valore: la modale è già stata mostrata.
        if (lastChecked[select.name] === value) return;
        lastChecked[select.name] = value;

        var query = 'kind=' + kind + '&type=' + encodeURIComponent(value) +
            '&sezione=' + encodeURIComponent(window.VENDOR_SECTION || '');
        fetch(window.SECTION_DUPLICATES_URL + '?' + query, {
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!data) return;
                var commonHint = data.scope === 'COMMON' && data.section !== 'COMUNE';
                if ((data.matches && data.matches.length) || commonHint) {
                    show(select, data, commonHint);
                }
            })
            .catch(function () { /* solo un aiuto: nessun blocco */ });
    }

    function injectModal() {
        var wrap = document.createElement('div');
        wrap.innerHTML = [
            '<div class="modal fade" id="' + MODAL_ID + '" tabindex="-1" role="dialog" aria-hidden="true">',
            '  <div class="modal-dialog" role="document">',
            '    <div class="modal-content">',
            '      <div class="modal-header bg-warning">',
            '        <h5 class="modal-title"><i class="fas fa-exclamation-triangle"></i> Elemento già presente</h5>',
            '      </div>',
            '      <div class="modal-body" id="' + MODAL_ID + '-body"></div>',
            '      <div class="modal-footer">',
            '        <button type="button" class="btn btn-outline-secondary" id="' + MODAL_ID + '-cancel">Annulla</button>',
            '        <button type="button" class="btn btn-warning" id="' + MODAL_ID + '-proceed">Procedi comunque</button>',
            '      </div>',
            '    </div>',
            '  </div>',
            '</div>'
        ].join('');
        document.body.appendChild(wrap.firstChild);
    }

    function show(select, data, commonHint) {
        var body = document.getElementById(MODAL_ID + '-body');
        body.innerHTML = '';
        var intro = document.createElement('p');
        intro.textContent = '"' + data.name + '"';
        if (data.matches && data.matches.length) {
            intro.textContent += ' è già presente per questo fornitore in:';
            body.appendChild(intro);
            var list = document.createElement('ul');
            data.matches.forEach(function (m) {
                var li = document.createElement('li');
                li.textContent = m.label + ' — ' + m.status + (m.expiry ? ', scadenza ' + m.expiry : '');
                list.appendChild(li);
            });
            body.appendChild(list);
        } else {
            body.appendChild(intro);
        }
        if (commonHint) {
            var hint = document.createElement('p');
            hint.className = 'text-muted';
            hint.textContent = 'È un elemento comune a tutte le società: di norma va caricato nella sezione Comune.';
            body.appendChild(hint);
        }
        var question = document.createElement('p');
        question.className = 'mb-0';
        question.textContent = 'Vuoi caricarlo comunque nella sezione ' + (window.VENDOR_SECTION_LABEL || '') + '?';
        body.appendChild(question);

        var $ = window.jQuery;
        var modal = $ ? $('#' + MODAL_ID) : null;
        document.getElementById(MODAL_ID + '-proceed').onclick = function () { hide(modal); };
        document.getElementById(MODAL_ID + '-cancel').onclick = function () {
            lastChecked[select.name] = '';
            var dj = window.django && window.django.jQuery;
            if (dj) {
                dj(select).val(null).trigger('change');
            } else {
                select.value = '';
            }
            hide(modal);
        };
        if (modal && typeof modal.modal === 'function') {
            modal.modal({ backdrop: 'static', keyboard: false });
        } else {
            var el = document.getElementById(MODAL_ID);
            el.classList.add('show');
            el.style.display = 'block';
        }
    }

    function hide(modal) {
        if (modal && typeof modal.modal === 'function') {
            modal.modal('hide');
        } else {
            var el = document.getElementById(MODAL_ID);
            el.classList.remove('show');
            el.style.display = 'none';
        }
    }
})();
