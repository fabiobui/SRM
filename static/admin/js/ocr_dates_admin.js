/*
 * Pre-compilazione date da file (OCR) nell'admin del fornitore
 * -------------------------------------------------------------
 * Quando si sceglie un file in una riga dell'inline Documenti Contrattuali
 * o Abilitazioni e Requisiti, il file viene inviato all'endpoint admin
 * `extract-dates/` (Tesseract lato server) e le date lette vengono messe
 * nei campi Emissione/Rilascio e Scadenza della stessa riga.
 *
 * Le date digitate a mano nella riga non vengono toccate; restano sempre
 * modificabili. La scadenza letta dal file ha la precedenza sul calcolo
 * automatico di document_expiry_calc.js (marcata come impostata a mano);
 * se il file contiene solo la data di emissione, la scadenza la calcola
 * quello script come al solito.
 */
(function () {
    'use strict';

    var FILE_FIELD = /-(file|document_file)$/;

    function endpoint() {
        var m = window.location.pathname.match(/^(.*\/vendors\/vendor\/)/);
        return m ? m[1] + 'extract-dates/' : null;
    }

    // Stesso formato (ISO o gg/mm/aaaa) del campo che si sta riempiendo.
    function formatFor(input, iso) {
        var p = iso.split('-');
        var current = (input.value || '').trim();
        if (input.type === 'date' || /^\d{4}-\d{2}-\d{2}$/.test(current)) {
            return iso;
        }
        var sep = (current.match(/^\d{1,2}([\/\-.])/) || [null, '/'])[1];
        return p[2] + sep + p[1] + sep + p[0];
    }

    // Un campo data digitato dall'utente non va piu' sovrascritto.
    document.addEventListener('input', function (ev) {
        var t = ev.target;
        if (ev.isTrusted && t && t.name && /-(issue_date|expiry_date)$/.test(t.name)) {
            t.dataset.ocrTouched = '1';
        }
    });

    document.addEventListener('change', function (ev) {
        var input = ev.target;
        if (!input || input.type !== 'file' || !FILE_FIELD.test(input.name || '')) {
            return;
        }
        var row = input.closest('tr') || input.closest('.inline-related');
        var url = endpoint();
        var token = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (!row || !url || !token || !input.files.length) {
            return;
        }
        var issue = row.querySelector('input[name$="-issue_date"]');
        var expiry = row.querySelector('input[name$="-expiry_date"]');
        if (!issue || !expiry) {
            return;
        }

        var data = new FormData();
        data.append('file', input.files[0]);
        data.append('csrfmiddlewaretoken', token.value);

        note(input, 'Analisi delle date nel documento in corso…', true);
        fetch(url, { method: 'POST', body: data, credentials: 'same-origin' })
            .then(function (r) { return r.ok ? r.json() : { error: 'http_' + r.status }; })
            .then(function (dates) {
                if (dates.error) {
                    note(input, 'Lettura automatica delle date non riuscita: inseriscile a mano.');
                    return;
                }
                var filled = false;
                if (dates.auto_renewal && !dates.expiry_date) {
                    // rinnovo tacito: niente scadenza calcolata dalla
                    // validità del tipo documento (marcata come manuale)
                    expiry.dataset.manualEdit = '1';
                }
                // Scadenza per prima: marcata come manuale, il calcolo
                // automatico scatterebbe sul change della emissione.
                if (dates.expiry_date && !expiry.dataset.ocrTouched) {
                    expiry.value = formatFor(expiry, dates.expiry_date);
                    expiry.dataset.manualEdit = '1';
                    expiry.dispatchEvent(new Event('change', { bubbles: true }));
                    filled = true;
                }
                if (dates.issue_date && !issue.dataset.ocrTouched) {
                    issue.value = formatFor(issue, dates.issue_date);
                    issue.dispatchEvent(new Event('change', { bubbles: true }));
                    filled = true;
                }
                delete issue.dataset.ocrTouched;
                delete expiry.dataset.ocrTouched;
                var msg = filled
                    ? 'Date lette dal documento: controllale e correggile se serve.'
                    : '';
                if (dates.auto_renewal) {
                    msg += ' Rinnovo tacito o durata indeterminata: scadenza lasciata vuota.';
                }
                note(input, msg.trim());
            })
            .catch(function () {
                note(input, 'Lettura automatica delle date non riuscita: inseriscile a mano.');
            });
    });

    function note(input, text, busy) {
        var holder = input.closest('td') || input.parentNode;
        var el = holder.querySelector('[data-ocr-note]');
        if (!el) {
            el = document.createElement('div');
            el.setAttribute('data-ocr-note', '');
            el.style.fontSize = '0.85em';
            holder.appendChild(el);
        }
        el.textContent = '';
        if (busy) {
            // rotellina finché l'analisi è in corso
            var spinner = document.createElement('span');
            spinner.className = 'spinner-border spinner-border-sm mr-1';
            spinner.setAttribute('role', 'status');
            el.appendChild(spinner);
        }
        el.appendChild(document.createTextNode(text));
    }
})();
