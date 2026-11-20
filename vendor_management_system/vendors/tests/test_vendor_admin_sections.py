"""Scheda fornitore per sezioni nell'admin.

Il click sul fornitore apre la scelta della sezione; ogni sezione mostra
solo i propri elementi; la sezione di un'altra società è in sola lettura;
scegliendo un tipo già presente in un'altra sezione arriva un avviso.
"""

import pytest
from django.urls import reverse

from vendor_management_system.documents.models import Document
from vendor_management_system.portal.tests.factories import (
    DocumentCatalogFactory,
    DocumentFactory,
)
from vendor_management_system.users.models import User
from vendor_management_system.vendors.models import VendorCompany
from vendor_management_system.vendors.tests.factories import VendorFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def shared_vendor():
    vendor = VendorFactory()
    VendorCompany.objects.create(vendor=vendor, company_id="SICURA")
    VendorCompany.objects.create(vendor=vendor, company_id="EVIMED")
    return vendor


def _login(client, company):
    user = User.objects.create_user(
        email=f"admin-{company}@example.invalid",
        password="x",
        role="admin",
        company_id=company,
    )
    client.force_login(user)
    return user


def _change_url(vendor, section):
    url = reverse("admin:vendors_vendor_change", args=[vendor.pk])
    return f"{url}?sezione={section}"


def test_scheda_senza_sezione_porta_alla_scelta(client, shared_vendor):
    _login(client, "SICURA")
    url = reverse("admin:vendors_vendor_change", args=[shared_vendor.pk])
    response = client.get(url)
    assert response.url == reverse(
        "admin:vendors_vendor_sections", args=[shared_vendor.pk]
    )


def test_changelist_apre_la_scelta_sezione(client, shared_vendor):
    _login(client, "SICURA")
    content = client.get(reverse("admin:vendors_vendor_changelist")).content
    sections_url = reverse(
        "admin:vendors_vendor_sections", args=[shared_vendor.pk]
    )
    assert sections_url in content.decode()


def test_pagina_sezioni_mostra_permessi(client, shared_vendor):
    _login(client, "SICURA")
    response = client.get(
        reverse("admin:vendors_vendor_sections", args=[shared_vendor.pk])
    )
    cards = {c["code"]: c["editable"] for c in response.context["cards"]}
    assert cards == {"COMUNE": True, "SICURA": True, "EVIMED": False}
    assert response.context["addable"] == []


def test_aggiunta_sezione_della_propria_societa(client):
    vendor = VendorFactory()
    VendorCompany.objects.create(vendor=vendor, company_id="EVIMED")
    _login(client, "SICURA")
    url = reverse("admin:vendors_vendor_add_section", args=[vendor.pk])
    response = client.post(url, {"company": "SICURA"})
    assert response.url.endswith("?sezione=SICURA")
    assert VendorCompany.objects.filter(
        vendor=vendor, company_id="SICURA"
    ).exists()
    assert client.post(url, {"company": "IGEAM"}).status_code == 403


def test_sezione_mostra_solo_i_suoi_documenti(client, shared_vendor):
    _login(client, "SICURA")
    DocumentFactory(vendor=shared_vendor, company_id="SICURA")
    DocumentFactory(vendor=shared_vendor, company_id="EVIMED")
    DocumentFactory(vendor=shared_vendor)
    response = client.get(_change_url(shared_vendor, "SICURA"))
    formsets = {
        f.formset.prefix: f.formset
        for f in response.context["inline_admin_formsets"]
    }
    sections = {
        form.instance.company_id
        for form in formsets["documents"].initial_forms
    }
    assert sections == {"SICURA"}


def test_sezione_di_altra_societa_in_sola_lettura(client, shared_vendor):
    _login(client, "SICURA")
    response = client.get(_change_url(shared_vendor, "EVIMED"))
    assert response.status_code == 200
    content = response.content.decode()
    assert 'name="_save"' not in content
    delete_url = reverse(
        "admin:vendors_vendor_delete", args=[shared_vendor.pk]
    )
    assert delete_url not in content
    assert "section-readonly-badge" in content
    response = client.get(_change_url(shared_vendor, "SICURA"))
    assert 'name="_save"' in response.content.decode()


def test_sezione_non_presente_404(client, shared_vendor):
    _login(client, "SICURA")
    assert client.get(_change_url(shared_vendor, "IGEAM")).status_code == 404


def test_nuovo_documento_prende_la_sezione_aperta(client, shared_vendor):
    _login(client, "SICURA")
    catalog = DocumentCatalogFactory()
    response = client.get(_change_url(shared_vendor, "SICURA"))
    data = _formset_post_data(response)
    data.update(
        {
            "documents-TOTAL_FORMS": "1",
            "documents-0-document_type": catalog.pk,
            "documents-0-vendor": shared_vendor.pk,
            "_save": "Salva",
        }
    )
    response = client.post(_change_url(shared_vendor, "SICURA"), data)
    assert response.status_code == 302, _errors(response)
    assert "sezione=SICURA" in response.url
    doc = Document.objects.get(vendor=shared_vendor, document_type=catalog)
    assert doc.company_id == "SICURA"


def test_salvataggio_sezione_societa_non_azzera_le_zone(client, shared_vendor):
    from vendor_management_system.vendors.models import Country

    # Su MySQL le nazioni sono già seminate dalle migrazioni.
    country, _ = Country.objects.get_or_create(
        code="FR", defaults={"name": "Francia"}
    )
    shared_vendor.competence_countries.add(country)
    _login(client, "SICURA")
    response = client.get(_change_url(shared_vendor, "SICURA"))
    data = _formset_post_data(response)
    data["_save"] = "Salva"
    response = client.post(_change_url(shared_vendor, "SICURA"), data)
    assert response.status_code == 302, _errors(response)
    assert list(shared_vendor.competence_countries.all()) == [country]


def test_avviso_documento_gia_presente_in_altra_sezione(client, shared_vendor):
    _login(client, "SICURA")
    catalog = DocumentCatalogFactory(scope="COMMON", name="DURC")
    DocumentFactory(
        vendor=shared_vendor, document_type=catalog, company_id="EVIMED"
    )
    url = reverse(
        "admin:vendors_vendor_section_duplicates", args=[shared_vendor.pk]
    )
    data = client.get(
        url, {"kind": "document", "type": catalog.pk, "sezione": "SICURA"}
    ).json()
    assert [m["company"] for m in data["matches"]] == ["EVIMED"]
    assert data["scope"] == "COMMON"
    data = client.get(
        url, {"kind": "document", "type": catalog.pk, "sezione": "EVIMED"}
    ).json()
    assert data["matches"] == []


def _formset_post_data(response):
    """Dati POST della scheda così come renderizzata (management form e
    righe esistenti), da completare nel test."""
    data = {}
    adminform = response.context["adminform"]
    for name, field in adminform.form.fields.items():
        value = adminform.form.initial.get(name, field.initial)
        if value is not None and not isinstance(value, (list, dict)):
            data[name] = value
    for inline in response.context["inline_admin_formsets"]:
        formset = inline.formset
        mgmt = formset.management_form
        for name in mgmt.fields:
            data[f"{formset.prefix}-{name}"] = mgmt[name].value()
        for form in formset.initial_forms:
            for name in form.fields:
                value = form[name].value()
                if value is not None and not isinstance(value, (list, dict)):
                    data[form.add_prefix(name)] = value
    return data


def _errors(response):
    context = getattr(response, "context", None)
    if not context:
        return response.content[:500]
    errors = [context["adminform"].form.errors]
    errors += [f.formset.errors for f in context["inline_admin_formsets"]]
    return errors
