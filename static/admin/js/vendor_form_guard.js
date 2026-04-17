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

        // Intercetta click sui pulsanti di salvataggio: nessuna conferma
        var saveButtons = form.querySelectorAll(
            'input[type="submit"], button[type="submit"], ' +
            'input[name="_save"], input[name="_addanother"], input[name="_continue"]'
        );
        saveButtons.forEach(function(btn) {
            btn.addEventListener('click', function() {
                submitViaButton = true;
            });
        });

        // Blocca submit da Enter (non da click su pulsante)
        form.addEventListener('submit', function(e) {
            if (!submitViaButton) {
                e.preventDefault();
                submitViaButton = false;
                return false;
            }
            submitViaButton = false;
        });

        // Impedisci che Enter nei campi di testo triggeri il submit
        form.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                var tag = e.target.tagName.toLowerCase();
                var type = (e.target.type || '').toLowerCase();
                // Permetti Enter in textarea e nei submit button
                if (tag === 'textarea') return;
                if (tag === 'input' && type === 'submit') return;
                if (tag === 'button' && type === 'submit') return;
                e.preventDefault();
            }
        });
    });
})();
