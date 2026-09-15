/*
 * Applicatore di "set" negli inline del VendorAdmin
 * -------------------------------------------------
 * Nucleo condiviso dai dropdown "Set Documentale" (tab Documenti),
 * "Set Requisiti" (tab Requisiti Professionali) e "Set Servizi" (tab Servizi).
 *
 * Espone window.vmsSetApplier(config): inietta in cima all'inline indicato un
 * dropdown con i set attivi e un pulsante "Applica set". Alla conferma vengono
 * create al volo (lato client) le righe dell'inline per ogni voce del set,
 * riutilizzando le righe vuote già presenti e saltando quelle già valorizzate.
 * Le righe vengono persistite al salvataggio normale del form.
 *
 * config:
 *   fieldSuffix  suffisso del <select> che identifica la voce nella riga
 *                (es. '-document_type', '-competence', '-service_type')
 *   endpoint     segmento di URL sotto .../vendors/vendor/ (es. 'service-sets/')
 *   label        etichetta mostrata accanto al dropdown
 *   itemsKey     chiave con l'elenco delle voci nel JSON del set (default 'items')
 *   onRow        hook opzionale (row, set) per impostare altri campi della riga
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

    window.vmsSetApplier = function (config) {
        var fieldSuffix = config.fieldSuffix;
        var itemsKey = config.itemsKey || 'items';

        ready(function () {
            // Solo nelle change/add form del Vendor (presenza dell'inline atteso).
            var group = findGroup(fieldSuffix);
            if (!group) return;

            var prefix = group.id.replace(/-group$/, '');
            var endpoint = buildEndpoint(config.endpoint);
            if (!endpoint) return;

            var ui = injectControls(group, config.label);
            var setsMap = {};

            // Carica i set pertinenti alla classificazione del fornitore.
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
                    ui.message.textContent = gettextSafe('Errore nel caricamento dei set.');
                });

            ui.button.addEventListener('click', function () {
                var setId = ui.select.value;
                if (!setId || !setsMap[setId]) {
                    ui.message.textContent = gettextSafe('Seleziona un set.');
                    return;
                }
                applySet(setsMap[setId]);
            });

            // --------------------------------------------------------------

            function applySet(set) {
                var items = set[itemsKey] || [];
                var existing = collectExistingIds();
                var emptyRows = collectEmptyRows();

                var added = 0, skipped = 0;
                items.forEach(function (item) {
                    var id = String(item.id);
                    if (existing.has(id)) { skipped += 1; return; }

                    var row = emptyRows.length ? emptyRows.shift() : addRow();
                    if (!row) { return; }

                    setChoice(row, item.id, item.text);
                    if (typeof config.onRow === 'function') {
                        config.onRow(row, set);
                    }
                    existing.add(id);
                    added += 1;
                });

                var parts = [];
                parts.push(interpolate(gettextSafe('Aggiunte %s righe'), [added]));
                if (skipped) parts.push(interpolate(gettextSafe('%s già presenti'), [skipped]));
                ui.message.textContent = parts.join(', ') + '. ' + gettextSafe('Ricordati di salvare.');
            }

            // Righe esistenti (non template, non in cancellazione) già valorizzate.
            function collectExistingIds() {
                var set = new Set();
                rowSelects().forEach(function (sel) {
                    if (isDeleted(sel.closest('tr'))) return;
                    if (sel.value) set.add(String(sel.value));
                });
                return set;
            }

            // Righe esistenti senza voce scelta (riutilizzabili: es. la riga extra vuota).
            function collectEmptyRows() {
                var rows = [];
                rowSelects().forEach(function (sel) {
                    var row = sel.closest('tr');
                    if (isDeleted(row)) return;
                    if (!sel.value) rows.push(row);
                });
                return rows;
            }

            function rowSelects() {
                var out = [];
                var selects = group.querySelectorAll('select[name$="' + fieldSuffix + '"]');
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

            function setChoice(row, id, text) {
                var sel = row.querySelector('select[name$="' + fieldSuffix + '"]');
                if (!sel) return;
                var value = String(id);

                if (!hasOption(sel, value)) {
                    // Widget autocomplete (select2 AJAX): le opzioni non sono precaricate.
                    sel.appendChild(new Option(text, value, true, true));
                }
                sel.value = value;
                notifyChange(sel);
            }
        });
    };

    // ----------------------------------------------------------------------

    function hasOption(sel, value) {
        for (var i = 0; i < sel.options.length; i++) {
            if (sel.options[i].value === value) return true;
        }
        return false;
    }

    // Nella change form convivono due copie di jQuery, ciascuna con il proprio
    // select2: quella dell'admin (django.jQuery, usata dai widget autocomplete)
    // e quella di Jazzmin (window.jQuery, che applica select2 alle select
    // normali sull'evento 'formset:added'). Gli handler registrati da una copia
    // non vedono i trigger dell'altra, quindi il change va notificato a
    // entrambe: altrimenti il valore viene impostato sulla <select> ma il
    // widget continua a mostrare "---------" (era il caso del tab Servizi).
    function notifyChange(el) {
        var instances = [];
        var dj = window.django && window.django.jQuery;
        if (typeof dj === 'function') instances.push(dj);
        if (typeof window.jQuery === 'function' && window.jQuery !== dj) {
            instances.push(window.jQuery);
        }
        for (var i = 0; i < instances.length; i++) {
            instances[i](el).trigger('change');
        }
        if (!instances.length) {
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    // Esposta per gli applier che devono impostare altri campi della riga.
    window.vmsSetApplier.notifyChange = notifyChange;

    function findGroup(fieldSuffix) {
        var groups = document.querySelectorAll('.inline-group');
        for (var i = 0; i < groups.length; i++) {
            if (groups[i].querySelector('select[name$="' + fieldSuffix + '"]')) {
                return groups[i];
            }
        }
        return null;
    }

    function buildEndpoint(segment) {
        // Path della change/add form: .../vendors/vendor/<pk>/change/ oppure .../vendors/vendor/add/
        var m = window.location.pathname.match(/^(.*\/vendors\/vendor\/)/);
        if (!m) return null;
        var url = m[1] + segment;
        var vm = window.location.pathname.match(/\/vendors\/vendor\/([^/]+)\/change/);
        if (vm && vm[1] && vm[1] !== 'add') {
            url += '?vendor=' + encodeURIComponent(vm[1]);
        }
        return url;
    }

    function injectControls(group, label) {
        var wrap = document.createElement('div');
        wrap.className = 'vms-set-applier';
        wrap.style.cssText = 'display:flex;align-items:center;flex-wrap:wrap;gap:.5rem;margin:.5rem 0 1rem;';

        var lbl = document.createElement('label');
        lbl.textContent = gettextSafe(label) + ':';
        lbl.style.cssText = 'margin:0;font-weight:600;';

        var select = document.createElement('select');
        select.className = 'form-control';
        select.style.width = 'auto';
        select.innerHTML = '<option value="">---------</option>';

        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-info btn-sm';
        button.textContent = gettextSafe('Applica set');

        var message = document.createElement('span');
        message.className = 'vms-set-message text-muted';
        message.style.cssText = 'font-size:.85rem;';

        wrap.appendChild(lbl);
        wrap.appendChild(select);
        wrap.appendChild(button);
        wrap.appendChild(message);

        // Inserisce il controllo in cima al gruppo inline.
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
