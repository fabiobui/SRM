/* Sposta il comando di eliminazione riga (colonna "Cancellare?" in fondo)
   accanto alle icone matita/più/occhio del campo principale della riga, negli
   inline Servizi, Abilitazioni/Requisiti e Documenti del fornitore. La
   checkbox DELETE resta nel form: il cestino la attiva/disattiva. */
(function () {
    'use strict';

    var GROUPS = ['vendor_services-group', 'vendor_competences-group', 'documents-group'];

    function trashFor(row, td) {
        var checkbox = td.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (!checkbox) {
            // riga nuova (anche da "Applica set"): il link "Elimina" di Django
            // diventa lo stesso cestino delle righe salvate
            var link = row.querySelector('a.inline-deletelink');
            if (!link) return null;
            link.innerHTML = '<i class="fas fa-trash"></i>';
            link.classList.add('inline-trash');
            link.title = 'Rimuovi riga';
            return link;
        }
        var btn = document.createElement('a');
        btn.href = '#';
        btn.className = 'inline-trash';
        btn.title = 'Elimina riga (si applica con Salva)';
        btn.innerHTML = '<i class="fas fa-trash"></i>';
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            checkbox.checked = !checkbox.checked;
            row.classList.toggle('to-delete', checkbox.checked);
            btn.classList.toggle('active', checkbox.checked);
        });
        return btn;
    }

    function relocate(row) {
        if (row.dataset.trashMoved || row.classList.contains('empty-form')) return;
        var td = row.querySelector('td.delete');
        if (!td) return;
        var wrapper = row.querySelector('.related-widget-wrapper');
        var host = wrapper || row.querySelector('td[class^="field-"]');
        if (!host) return;
        var trash = trashFor(row, td);
        if (!trash) return;
        row.dataset.trashMoved = '1';
        if (wrapper) {
            var links = wrapper.querySelectorAll('.related-widget-wrapper-link');
            var last = links.length ? links[links.length - 1] : null;
            if (last && last.parentNode) {
                last.parentNode.insertBefore(trash, last.nextSibling);
            } else {
                wrapper.appendChild(trash);
            }
        } else {
            host.appendChild(trash);
        }
        // nasconde la colonna "Cancellare?" (cella e intestazione)
        td.classList.add('trash-moved');
        var idx = Array.prototype.indexOf.call(row.children, td);
        var table = row.closest('table');
        var th = table && table.querySelectorAll('thead th')[idx];
        if (th) th.classList.add('trash-moved');
        if (checkboxChecked(td)) row.classList.add('to-delete');
    }

    function checkboxChecked(td) {
        var c = td.querySelector('input[type="checkbox"][name$="-DELETE"]');
        return c && c.checked;
    }

    function processAll() {
        GROUPS.forEach(function (id) {
            var group = document.getElementById(id);
            if (!group) return;
            group.querySelectorAll('tbody tr.form-row').forEach(relocate);
        });
    }

    function observe() {
        processAll();
        // righe aggiunte dopo il caricamento (pulsante "Aggiungi", "Applica
        // set"): il link "Elimina" di Django compare dopo l'evento
        // formset:added, quindi si osserva il DOM invece dell'evento
        var scheduled = false;
        var observer = new MutationObserver(function () {
            if (scheduled) return;
            scheduled = true;
            requestAnimationFrame(function () {
                scheduled = false;
                processAll();
            });
        });
        GROUPS.forEach(function (id) {
            var group = document.getElementById(id);
            if (group) observer.observe(group, { childList: true, subtree: true });
        });
    }

    document.addEventListener('DOMContentLoaded', observe);
})();
