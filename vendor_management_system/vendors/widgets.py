"""Selettore territoriale delle zone di competenza.

Un solo widget, usato identico in due posti: il form fornitore del Django
admin e la pagina di proposta modifiche del portale fornitori. E' un
`Widget` Django con `template_name` (e non un partial + JS incluso a mano
nei due template) perche' cosi' rendering, parsing del POST, validazione,
re-render dopo un errore e dichiarazione degli asset sono definiti una
volta sola.

L'albero e' renderizzato **server-side**: sono ~157 nodi in 2 query, e un
round-trip AJAX costerebbe un URL da iniettare (per `FORCE_SCRIPT_NAME`),
un flash di contenuto vuoto, la gestione degli errori di rete e la perdita
del funzionamento senza JavaScript.

**L'invariante su cui poggia tutto il resto**: nel form hanno un attributo
`name` soltanto le *foglie* dell'albero, cioe' le province e le nazioni
estere. Le checkbox di regione e di nazione-con-regioni ne sono prive:
esistono solo come comando dell'interfaccia e non raggiungono mai il
server. Ne segue che un bug nella logica tri-stato del JavaScript puo'
mostrare un pallino sbagliato ma **non puo' corrompere i dati salvati**, e
che il degrado senza JavaScript e' corretto per costruzione.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from vendor_management_system.vendors.competence import (
    geo_tree_data,
    leaf_countries_qs,
)
from vendor_management_system.vendors.models import Province

SUFFISSO_PROVINCE = "_provinces"
SUFFISSO_NAZIONI = "_countries"


def normalizza_selezione(value):
    """Riconduce un valore qualsiasi a `(set[str], set[str])`.

    Il valore arriva da tre strade diverse - `initial` (form non bound),
    `value_from_datadict` (form bound) e il re-render dopo un errore di
    validazione - quindi puo' essere `None`, un dizionario di liste di
    stringhe o un dizionario di istanze/QuerySet.
    """
    if not value:
        return set(), set()

    def _codici(elenco):
        codici = set()
        for voce in elenco or []:
            codici.add(getattr(voce, "code", voce))
        return {str(c) for c in codici}

    return (
        _codici(value.get("provinces")),
        _codici(value.get("countries")),
    )


class CompetenceAreaSelectorWidget(forms.Widget):
    """Albero di checkbox Nazione -> Regione -> Provincia."""

    template_name = "vendors/widgets/competence_area_selector.html"

    class Media:
        css = {"all": ("geo/css/competence_area_selector.css",)}
        js = ("geo/js/competence_area_selector.js",)

    def value_from_datadict(self, data, files, name):
        getlist = getattr(data, "getlist", None)
        if getlist is None:
            return {
                "provinces": list(data.get(name + SUFFISSO_PROVINCE) or []),
                "countries": list(data.get(name + SUFFISSO_NAZIONI) or []),
            }
        return {
            "provinces": getlist(name + SUFFISSO_PROVINCE),
            "countries": getlist(name + SUFFISSO_NAZIONI),
        }

    def value_omitted_from_data(self, data, files, name):
        # Come per ogni checkbox: l'assenza dal POST significa "nessuna
        # selezione", non "campo non inviato". Senza questo, deselezionare
        # tutto verrebbe interpretato come "non toccare il campo".
        return False

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        province, nazioni = normalizza_selezione(value)
        albero = geo_tree_data()

        context["widget"].update(
            {
                "nome_province": name + SUFFISSO_PROVINCE,
                "nome_nazioni": name + SUFFISSO_NAZIONI,
                "tree_detailed": [n for n in albero if not n["leaf"]],
                "tree_leaf": [n for n in albero if n["leaf"]],
                "selected_provinces": province,
                "selected_countries": nazioni,
            }
        )
        return context


class CompetenceAreaField(forms.Field):
    """Campo composito: province italiane + nazioni estere.

    Un campo solo e non due perche' il selettore e' un unico blocco
    visivo (con un "seleziona tutto" di radice che copre entrambe le
    sezioni) e perche' la proposta di modifica del portale ha bisogno di
    un valore atomico da congelare nel diff.
    """

    widget = CompetenceAreaSelectorWidget

    default_error_messages = {
        "sconosciuta": _(
            "Selezione territoriale non valida: alcune aree non esistono "
            "o non sono piu' attive. Ricarica la pagina e riprova."
        ),
    }

    def clean(self, value):
        province, nazioni = normalizza_selezione(value)

        valide_province = set(
            Province.objects.filter(
                is_active=True, code__in=province
            ).values_list("code", flat=True)
        )
        # `regions__isnull=True` e' la difesa contro un POST manomesso che
        # mandi l'Italia fra le nazioni: la copertura italiana si esprime
        # solo con le province.
        valide_nazioni = set(
            leaf_countries_qs()
            .filter(code__in=nazioni)
            .values_list("code", flat=True)
        )

        if valide_province != province or valide_nazioni != nazioni:
            raise forms.ValidationError(
                self.error_messages["sconosciuta"], code="sconosciuta"
            )

        if self.required and not (valide_province or valide_nazioni):
            raise forms.ValidationError(
                self.error_messages["required"], code="required"
            )

        return {
            "provinces": sorted(valide_province),
            "countries": sorted(valide_nazioni),
        }

    def has_changed(self, initial, data):
        return normalizza_selezione(initial) != normalizza_selezione(data)
