/*
 * Selettore territoriale delle zone di competenza.
 *
 * Comportamento puro: l'albero e' gia' nel DOM, renderizzato server-side
 * dal widget. Qui si aggiungono cascata, stato tri-stato derivato,
 * comandi per livello, ricerca e accordion.
 *
 * Invariante da cui dipende la sicurezza del tutto: hanno un attributo
 * `name` soltanto le foglie (.vms-geo__cb--leaf). Le checkbox di regione e
 * nazione sono derivate e non vengono mai inviate, quindi un errore qui
 * puo' al massimo mostrare un pallino sbagliato.
 *
 * Performance: tre soli listener delegati sulla radice, nessun listener
 * per nodo, e un indice nodo -> foglie costruito una volta all'init.
 */
(function () {
  'use strict';

  var SEL_LEAF = '.vms-geo__cb--leaf';
  var SEL_NODE = '[data-geo-node="country"], [data-geo-node="region"]';

  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  function setHidden(el, hidden) {
    if (hidden) {
      el.setAttribute('hidden', '');
    } else {
      el.removeAttribute('hidden');
    }
  }

  /* Testo su cui cerca il filtro: quello della foglia piu' quello di
     tutti i suoi antenati, cosi' cercare "lombardia" mostra le sue
     province e cercare "rav" mostra la sola Ravenna. */
  function buildSearchText(leafLi) {
    var parti = [leafLi.dataset.geoText || ''];
    var nodo = leafLi.parentElement;
    while (nodo && !nodo.hasAttribute('data-vms-geo')) {
      if (nodo.dataset && nodo.dataset.geoText) {
        parti.push(nodo.dataset.geoText);
      }
      nodo = nodo.parentElement;
    }
    return parti.join(' ');
  }

  function initRoot(root) {
    var leaves = Array.prototype.slice.call(root.querySelectorAll(SEL_LEAF));
    if (!leaves.length) {
      return;
    }

    var nodes = Array.prototype.slice.call(root.querySelectorAll(SEL_NODE));
    var subtree = new Map();
    nodes.forEach(function (nodo) {
      subtree.set(
        nodo,
        Array.prototype.slice.call(nodo.querySelectorAll(SEL_LEAF))
      );
    });

    leaves.forEach(function (cb) {
      var li = cb.closest('li');
      if (li) {
        li.dataset.geoAll = buildSearchText(li);
      }
    });

    var stato = { query: '', soloSelezionate: false, espansiSalvati: null };

    /* ---- stato derivato ------------------------------------------- */

    function recomputeAll() {
      nodes.forEach(function (nodo) {
        var figlie = subtree.get(nodo) || [];
        var selezionate = figlie.filter(function (cb) {
          return cb.checked;
        }).length;
        var derivata = nodo.querySelector('[data-geo-derived]');
        var badge = nodo.querySelector('[data-geo-badge]');
        var pieno = figlie.length > 0 && selezionate === figlie.length;
        var parziale = selezionate > 0 && !pieno;

        if (derivata) {
          derivata.checked = pieno;
          derivata.indeterminate = parziale;
          derivata.dataset.state = pieno
            ? 'full'
            : parziale
              ? 'partial'
              : 'none';
          // I browser non espongono `indeterminate` agli screen reader.
          derivata.setAttribute(
            'aria-checked',
            parziale ? 'mixed' : String(pieno)
          );
        }
        if (badge) {
          badge.textContent = selezionate
            ? selezionate + '/' + figlie.length
            : '';
        }
      });
      updateCounter();
    }

    function updateCounter() {
      var contatore = root.querySelector('[data-geo-counter]');
      if (!contatore) {
        return;
      }
      var province = 0;
      var nazioni = 0;
      leaves.forEach(function (cb) {
        if (!cb.checked) {
          return;
        }
        if (cb.closest('[data-geo-node="province"]')) {
          province += 1;
        } else {
          nazioni += 1;
        }
      });
      var pezzi = [];
      if (province) {
        pezzi.push(province + (province === 1 ? ' provincia' : ' province'));
      }
      if (nazioni) {
        pezzi.push(nazioni + (nazioni === 1 ? ' nazione' : ' nazioni'));
      }
      if (!pezzi.length) {
        contatore.textContent = 'Nessuna area selezionata';
        return;
      }
      // Concordanza: "1 provincia selezionata" ma "13 province
      // selezionate", e plurale appena ci sono due gruppi.
      var singolare = pezzi.length === 1 && province + nazioni === 1;
      contatore.textContent =
        pezzi.join(', ') + (singolare ? ' selezionata' : ' selezionate');
    }

    /* ---- selezione in blocco -------------------------------------- */

    function foglieDi(ambito, elemento) {
      if (ambito === 'node') {
        var nodo = elemento.closest('[data-geo-node]');
        return nodo ? subtree.get(nodo) || [] : [];
      }
      if (ambito === 'section') {
        var sezione = elemento.closest('[data-geo-section]');
        return sezione
          ? Array.prototype.slice.call(sezione.querySelectorAll(SEL_LEAF))
          : [];
      }
      return leaves;
    }

    /* Agisce solo sulle foglie non filtrate via: dopo una ricerca
       "seleziona tutto" deve fare quello che l'utente sta vedendo. Una
       foglia dentro un ramo semplicemente chiuso resta invece inclusa. */
    function visibile(cb) {
      var li = cb.closest('li');
      while (li && !li.hasAttribute('data-vms-geo')) {
        if (li.hasAttribute('hidden')) {
          return false;
        }
        li = li.parentElement;
      }
      return true;
    }

    function imposta(elenco, valore) {
      elenco.forEach(function (cb) {
        if (visibile(cb)) {
          cb.checked = valore;
        }
      });
      recomputeAll();
    }

    /* ---- accordion e ricerca --------------------------------------- */

    function espansi() {
      return Array.prototype.slice
        .call(root.querySelectorAll('[data-geo-twisty]'))
        .filter(function (b) {
          return b.getAttribute('aria-expanded') === 'true';
        });
    }

    function espandi(twisty, aperto) {
      twisty.setAttribute('aria-expanded', String(aperto));
      var target = document.getElementById(
        twisty.getAttribute('aria-controls')
      );
      if (target) {
        target.classList.toggle('is-collapsed', !aperto);
      }
    }

    function applyFilter() {
      var q = stato.query;
      var solo = stato.soloSelezionate;

      leaves.forEach(function (cb) {
        var li = cb.closest('li');
        if (!li) {
          return;
        }
        var ok = !q || (li.dataset.geoAll || '').indexOf(q) !== -1;
        if (ok && solo && !cb.checked) {
          ok = false;
        }
        setHidden(li, !ok);
      });

      // Un ramo e' visibile se contiene almeno una foglia visibile.
      nodes
        .slice()
        .reverse()
        .forEach(function (nodo) {
          var visibili = (subtree.get(nodo) || []).some(function (cb) {
            var li = cb.closest('li');
            return li && !li.hasAttribute('hidden');
          });
          setHidden(nodo, !visibili);
        });

      if (q || solo) {
        Array.prototype.slice
          .call(root.querySelectorAll('[data-geo-twisty]'))
          .forEach(function (t) {
            espandi(t, true);
          });
      }
    }

    function impostaQuery(valore) {
      var nuova = (valore || '').trim().toLowerCase();
      if (nuova === stato.query) {
        return;
      }
      if (!stato.query && nuova && stato.espansiSalvati === null) {
        stato.espansiSalvati = espansi();
      }
      stato.query = nuova;
      applyFilter();
      if (!nuova && !stato.soloSelezionate) {
        ripristinaEspansione();
      }
    }

    function ripristinaEspansione() {
      if (stato.espansiSalvati === null) {
        return;
      }
      var aperti = stato.espansiSalvati;
      Array.prototype.slice
        .call(root.querySelectorAll('[data-geo-twisty]'))
        .forEach(function (t) {
          espandi(t, aperti.indexOf(t) !== -1);
        });
      stato.espansiSalvati = null;
    }

    /* ---- listener (tre in tutto, delegati) ------------------------- */

    root.addEventListener('change', function (evento) {
      var bersaglio = evento.target;
      if (bersaglio.classList.contains('vms-geo__cb--leaf')) {
        recomputeAll();
        if (stato.soloSelezionate) {
          applyFilter();
        }
      }
    });

    root.addEventListener('click', function (evento) {
      var derivata = evento.target.closest('[data-geo-derived]');
      if (derivata) {
        // Da "parziale" si va a "tutto selezionato": e' la convenzione
        // abituale delle checkbox tri-stato.
        var precedente = derivata.dataset.state || 'none';
        var nodo = derivata.closest('[data-geo-node]');
        imposta(subtree.get(nodo) || [], precedente !== 'full');
        if (stato.soloSelezionate) {
          applyFilter();
        }
        return;
      }

      var twisty = evento.target.closest('[data-geo-twisty]');
      if (twisty) {
        espandi(twisty, twisty.getAttribute('aria-expanded') !== 'true');
        return;
      }

      var bottone = evento.target.closest('[data-geo-action]');
      if (!bottone) {
        return;
      }
      var azione = bottone.dataset.geoAction;
      if (azione === 'only-selected') {
        stato.soloSelezionate = !stato.soloSelezionate;
        bottone.setAttribute('aria-pressed', String(stato.soloSelezionate));
        if (stato.soloSelezionate && stato.espansiSalvati === null) {
          stato.espansiSalvati = espansi();
        }
        applyFilter();
        if (!stato.soloSelezionate && !stato.query) {
          ripristinaEspansione();
        }
        return;
      }
      if (azione === 'select-all' || azione === 'clear-all') {
        imposta(
          foglieDi(bottone.dataset.geoScope, bottone),
          azione === 'select-all'
        );
        if (stato.soloSelezionate) {
          applyFilter();
        }
      }
    });

    var timerRicerca = null;
    root.addEventListener('input', function (evento) {
      if (!evento.target.hasAttribute('data-geo-search')) {
        return;
      }
      var valore = evento.target.value;
      window.clearTimeout(timerRicerca);
      timerRicerca = window.setTimeout(function () {
        impostaQuery(valore);
      }, 120);
    });

    recomputeAll();
  }

  ready(function () {
    Array.prototype.slice
      .call(document.querySelectorAll('[data-vms-geo]'))
      .forEach(initRoot);
  });
})();
