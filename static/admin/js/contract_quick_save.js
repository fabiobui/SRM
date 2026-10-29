/* Bottone "Salva" accanto a "Elimina" nelle righe nuove dell'inline Contratti:
   crea subito il contratto via AJAX senza salvare l'intera scheda. Dopo il
   salvataggio la riga viene tolta dal formset (come con "Elimina"), altrimenti
   il submit finale la ricreerebbe: contract_number è unique. */
(function () {
    'use strict';

    var FIELD_NAMES = ['contract_number', 'title', 'contract_type', 'reference_person',
        'status', 'start_date', 'end_date', 'amount', 'notes'];

    function csrfToken() {
        var input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : '';
    }

    function clearFeedback(row) {
        row.querySelectorAll('.contract-qs-error').forEach(function (el) { el.remove(); });
    }

    function showErrors(row, errors) {
        var prefix = row.id + '-';
        Object.keys(errors).forEach(function (field) {
            var input = row.querySelector('[name="' + prefix + field + '"]');
            var host = (input && input.parentElement) || row.querySelector('.card-body') || row;
            var box = document.createElement('div');
            box.className = 'contract-qs-error text-danger small';
            box.textContent = errors[field].join(' ');
            host.appendChild(box);
        });
    }

    function showSaved(group, data) {
        var box = document.createElement('div');
        box.className = 'alert alert-success contract-qs-ok';
        box.textContent = 'Contratto ' + data.contract_number + ' (' + data.title + ') salvato. ' +
            'Comparirà nell\'elenco al prossimo salvataggio della scheda o ricaricando la pagina.';
        group.insertBefore(box, group.firstChild);
    }

    function save(row, group, link, button) {
        var prefix = row.id + '-';
        var body = new FormData();
        FIELD_NAMES.forEach(function (name) {
            var input = row.querySelector('[name="' + prefix + name + '"]');
            if (input) body.append(name, input.value);
        });
        clearFeedback(row);
        button.disabled = true;
        fetch(window.CONTRACT_SAVE_URL, {
            method: 'POST',
            body: body,
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (response) {
            return response.json().then(function (data) {
                return { ok: response.ok, data: data };
            });
        }).then(function (result) {
            if (result.ok) {
                showSaved(group, result.data);
                link.click(); // rimozione riga gestita da Django (TOTAL_FORMS e indici)
                return;
            }
            showErrors(row, result.data.errors || { contract_number: [result.data.error || 'Salvataggio non riuscito.'] });
        }).catch(function () {
            showErrors(row, { contract_number: ['Salvataggio non riuscito: riprova.'] });
        }).then(function () {
            button.disabled = false;
        });
    }

    function addButton(row, group) {
        var link = row.querySelector('a.inline-deletelink');
        if (!link || row.dataset.quickSave || row.classList.contains('empty-form')) return;
        row.dataset.quickSave = '1';
        var button = document.createElement('button');
        // type="button": il guard del form considera submit solo i bottoni senza type
        button.type = 'button';
        button.className = 'btn btn-success btn-sm contract-quick-save float-right mr-2';
        button.textContent = 'Salva';
        button.addEventListener('click', function () { save(row, group, link, button); });
        // "Elimina" è float:right: con lo stesso float, il bottone che lo segue nel DOM gli sta a sinistra
        link.parentNode.insertBefore(button, link.nextSibling);
    }

    function init() {
        // senza URL (scheda di aggiunta del fornitore) il contratto non ha ancora un fornitore
        if (!window.CONTRACT_SAVE_URL) return;
        var group = document.getElementById('contracts-group');
        if (!group) return;
        function processAll() {
            group.querySelectorAll('.inline-related').forEach(function (row) { addButton(row, group); });
        }
        processAll();
        // le righe nuove compaiono dopo il caricamento (pulsante "Aggiungi")
        new MutationObserver(processAll).observe(group, { childList: true, subtree: true });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
