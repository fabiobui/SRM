(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        var form = document.getElementById('vendor_form') || document.querySelector('form#vendor_form');
        if (!form) {
            // Fallback: cerca il form principale di change_form
            form = document.querySelector('#content-main form');
        }
        if (!form) return;

        var submitViaButton = false;

        // Intercetta click sui pulsanti di salvataggio a livello documento
        // (funziona anche se i bottoni sono fuori dal <form> in alcuni temi admin)
        document.addEventListener('click', function(e) {
            var target = e.target;
            if (!target) return;
            var tag = (target.tagName || '').toLowerCase();
            var type = (target.type || '').toLowerCase();
            var name = (target.name || '');
            if (
                (tag === 'input' && type === 'submit') ||
                (tag === 'button' && type === 'submit') ||
                name === '_save' || name === '_addanother' || name === '_continue'
            ) {
                submitViaButton = true;
            }
        }, true); // capturing: intercetta prima di qualsiasi altro handler

        // Blocca submit da Enter (non da click su pulsante)
        form.addEventListener('submit', function(e) {
            if (!submitViaButton) {
                e.preventDefault();
                return;
            }
            submitViaButton = false;
        });

        // Impedisci che Enter nei campi di testo triggeri il submit.
        // Usa capturing (true) per intercettare PRIMA di Select2/autocomplete
        // che potrebbero fermare la propagazione dell'evento.
        form.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter') return;
            var tag = (e.target.tagName || '').toLowerCase();
            var type = (e.target.type || '').toLowerCase();
            // Permetti Enter in textarea
            if (tag === 'textarea') return;
            // Permetti Enter sui pulsanti di submit (clic con tastiera)
            if (type === 'submit') return;
            if (tag === 'button' && (type === 'submit' || type === '')) return;
            // Blocca Enter su tutti gli altri input (testo, email, number, ecc.)
            e.preventDefault();
        }, true); // capturing: si attiva prima che l'evento raggiunga i widget figli
    });
})();
