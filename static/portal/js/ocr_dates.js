/*
 * Pre-compila le date di rilascio/scadenza leggendole dal file scelto
 * (OCR lato server). Vale per ogni form con un input file e i campi
 * "issue_date"/"expiry_date". I campi modificati a mano dal fornitore non
 * vengono toccati (sovrascrive solo quelli vuoti o precompilati con i valori
 * del documento precedente) e restano sempre modificabili.
 */
(function () {
  'use strict';

  var ENDPOINT = document.currentScript.dataset.endpoint;

  // Un campo data digitato dal fornitore non va piu' sovrascritto.
  document.addEventListener('input', function (evento) {
    var nome = evento.target.name;
    if (evento.isTrusted && (nome === 'issue_date' || nome === 'expiry_date')) {
      evento.target.dataset.ocrTouched = '1';
    }
  });

  document.addEventListener('change', function (evento) {
    var input = evento.target;
    if (!input.matches || !input.matches('input[type="file"]')) {
      return;
    }
    var form = input.form;
    var rilascio = form && form.querySelector('[name="issue_date"]');
    var scadenza = form && form.querySelector('[name="expiry_date"]');
    var token = form && form.querySelector('[name="csrfmiddlewaretoken"]');
    if (!input.files.length || !rilascio || !scadenza || !token) {
      return;
    }

    var dati = new FormData();
    dati.append('file', input.files[0]);
    dati.append('csrfmiddlewaretoken', token.value);

    mostraEsito(input, 'Analisi delle date nel documento in corso…', true);
    fetch(ENDPOINT, { method: 'POST', body: dati, credentials: 'same-origin' })
      .then(function (risposta) {
        return risposta.ok ? risposta.json() : { error: 'http_' + risposta.status };
      })
      .then(function (date) {
        if (date.error) {
          mostraEsito(input, 'Lettura automatica delle date non riuscita: inseriscile a mano.');
          return;
        }
        var compilate = false;
        [[rilascio, date.issue_date], [scadenza, date.expiry_date]].forEach(
          function (coppia) {
            var campo = coppia[0];
            if (coppia[1] && !campo.dataset.ocrTouched) {
              campo.value = coppia[1];
              compilate = true;
            }
          }
        );
        delete rilascio.dataset.ocrTouched;
        delete scadenza.dataset.ocrTouched;
        mostraEsito(
          input,
          compilate
            ? 'Date lette dal documento: controllale e correggile se serve.'
            : ''
        );
      })
      .catch(function () {
        mostraEsito(input, 'Lettura automatica delle date non riuscita: inseriscile a mano.');
      });
  });

  function mostraEsito(input, testo, inCorso) {
    var nota = input.parentNode.querySelector('[data-ocr-note]');
    if (!nota) {
      nota = document.createElement('div');
      nota.className = 'form-text';
      nota.setAttribute('data-ocr-note', '');
      input.insertAdjacentElement('afterend', nota);
    }
    nota.textContent = '';
    if (inCorso) {
      // rotellina finché l'analisi è in corso
      var rotellina = document.createElement('span');
      rotellina.className = 'spinner-border spinner-border-sm me-2';
      rotellina.setAttribute('role', 'status');
      nota.appendChild(rotellina);
    }
    nota.appendChild(document.createTextNode(testo));
  }
})();
