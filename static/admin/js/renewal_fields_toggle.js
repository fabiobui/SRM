/*
 * Campi di rinnovo dei cataloghi (Documenti e Requisiti Professionali)
 * --------------------------------------------------------------------
 * "Periodo validità (giorni)" e "Giorni di preavviso scadenza" hanno senso
 * solo se il tipo "Richiede Rinnovo": se il flag è spento le righe vengono
 * nascoste (e il salvataggio lato server svuota comunque i valori).
 */
(function () {
    'use strict';

    // Campo -> valore proposto quando si attiva il rinnovo su un tipo vuoto.
    var DEFAULTS = { validity_period_days: '365', reminder_days_before: '30' };
    var FIELDS = Object.keys(DEFAULTS);

    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function () {
        var flag = document.getElementById('id_requires_renewal');
        if (!flag) return;

        function apply() {
            FIELDS.forEach(function (name) {
                var input = document.getElementById('id_' + name);
                if (!input) return;
                var row = input.closest('.form-group, .form-row, .field-' + name);
                if (row) row.style.display = flag.checked ? '' : 'none';
            });
        }

        flag.addEventListener('change', function () {
            if (flag.checked) {
                FIELDS.forEach(function (name) {
                    var input = document.getElementById('id_' + name);
                    if (input && !input.value) input.value = DEFAULTS[name];
                });
            }
            apply();
        });
        apply();
    });
})();
