"""Filtri della changelist fornitori per zona di competenza.

Tre tendine a cascata nella barra filtri di jazzmin: Nazione, poi Regione
(limitata alla nazione scelta), poi Provincia (limitata alla regione
scelta). Sono `SimpleListFilter` standard, quindi la selezione finisce
nella querystring ed e' condivisibile: `?comp_country=IT&comp_region=LOM`.

**La cascata legge `request.GET`, non `params`.** In Django 5.0 ogni
filtro fa `params.pop()` del proprio parametro mentre viene istanziato,
quindi il dizionario si svuota progressivamente e il comportamento
dipenderebbe dall'ordine di `list_filter`. `request.GET` resta intatto.

Sui codici: si filtra per codice (`IT`, `LOM`, `MI`) e non per UUID, cosi'
l'URL resta leggibile. Nazioni e province stanno in parametri distinti
anche perche' i codici possono collidere - `FR` e' sia la Francia sia
Frosinone.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .competence import filter_by_competence
from .models import Country, Province, Region


class _CompetenceFilterBase(admin.SimpleListFilter):
    """Base comune alle tre tendine.

    Include l'auto-guarigione: se il valore selezionato non e' fra quelli
    ammessi dal livello superiore (perche' l'utente ha cambiato nazione
    lasciando in querystring una regione di un'altra), il filtro viene
    semplicemente ignorato. Senza, l'utente vedrebbe zero risultati senza
    capire perche'.
    """

    campo_competenza = None

    def valore_valido(self):
        scelto = self.value()
        if not scelto:
            return None
        ammessi = {codice for codice, _etichetta in self.lookup_choices}
        return scelto if scelto in ammessi else None

    def queryset(self, request, queryset):
        scelto = self.valore_valido()
        if not scelto:
            return queryset
        return filter_by_competence(
            queryset, **{self.campo_competenza: [scelto]}
        )


class CompetenceCountryFilter(_CompetenceFilterBase):
    title = _("Competenza: Nazione")
    parameter_name = "comp_country"
    campo_competenza = "countries"

    def lookups(self, request, model_admin):
        nazioni = Country.objects.filter(is_active=True).order_by(
            "sort_order", "name"
        )
        return [(n.code, n.name) for n in nazioni]


class CompetenceRegionFilter(_CompetenceFilterBase):
    title = _("Competenza: Regione")
    parameter_name = "comp_region"
    campo_competenza = "regions"

    def lookups(self, request, model_admin):
        regioni = (
            Region.objects.filter(is_active=True)
            .select_related("country")
            .order_by("sort_order", "name")
        )
        nazione = request.GET.get(CompetenceCountryFilter.parameter_name)
        if nazione:
            regioni = regioni.filter(country__code=nazione)
        return [(r.code, r.name) for r in regioni]


class CompetenceProvinceFilter(_CompetenceFilterBase):
    title = _("Competenza: Provincia")
    parameter_name = "comp_province"
    campo_competenza = "provinces"

    def lookups(self, request, model_admin):
        province = (
            Province.objects.filter(is_active=True)
            .select_related("region")
            .order_by("sort_order", "name")
        )
        regione = request.GET.get(CompetenceRegionFilter.parameter_name)
        nazione = request.GET.get(CompetenceCountryFilter.parameter_name)
        if regione:
            province = province.filter(region__code=regione)
        elif nazione:
            province = province.filter(region__country__code=nazione)
        return [(p.code, f"{p.name} ({p.code})") for p in province]
