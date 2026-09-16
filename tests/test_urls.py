"""
Verifica che gli URL principali dell'app si generino correttamente con
`reverse()`, senza bisogno di un server in esecuzione.

Nota: questo test non copre lo scenario `USE_FORNITORI_PREFIX=True` (il
prefisso di produzione `/fornitori`), perché quel flag viene letto una sola
volta all'avvio del processo Django (vedi docs/URL_PREFIX_CONFIG.md) e non è
ricalcolabile a runtime con un semplice `override_settings`.
"""

import pytest
from django.urls import NoReverseMatch, reverse

URL_NAMES = [
    "home",
    "admin:index",
    "login",
    "logout",
    "vendor-portal",
    "admin-dashboard",
    "backoffice-dashboard",
    "document-upload",
    "schema-swagger-ui",
    "admin:vendors_vendor_add",
    "admin:documents_documenttype_add",
    "admin:logout",
]


@pytest.mark.parametrize("url_name", URL_NAMES)
def test_url_reverses_without_error(url_name):
    try:
        reverse(url_name)
    except NoReverseMatch as exc:
        pytest.fail(
            f"reverse({url_name!r}) ha sollevato NoReverseMatch: {exc}"
        )


def test_home_url():
    assert reverse("home") == "/"


def test_login_url():
    assert reverse("login") == "/auth/login/"


def test_logout_url():
    assert reverse("logout") == "/auth/logout/"


def test_swagger_ui_url():
    assert reverse("schema-swagger-ui") == "/swagger/"


def test_document_upload_url_under_documents_prefix():
    assert reverse("document-upload").startswith("/documents/")


def test_vendor_portal_legacy_redirect_url_under_documents_prefix():
    assert reverse("vendor-portal").startswith("/documents/")
