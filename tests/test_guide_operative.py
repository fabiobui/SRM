"""Guide operative nelle tre dashboard (admin, back office, portale)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from vendor_management_system.portal.tests.factories import VendorUserFactory

User = get_user_model()
PASSWORD = "test-pass-1234"

GUIDE = {
    "admin": ("guide-admin", "Guida operativa - amministrazione"),
    "bo": ("guide-bo", "Guida operativa - back office"),
    "vendor": ("guide-vendor", "Guida operativa - fornitori"),
}


def _html(response):
    return response.content.decode()


@pytest.mark.django_db
def test_guida_admin_nella_index_admin(client):
    admin = User.objects.create_user(
        email="guida-admin@example.invalid", password=PASSWORD, role="admin"
    )
    client.force_login(admin)

    html = _html(client.get(reverse("admin:index")))

    guide_id, title = GUIDE["admin"]
    assert guide_id in html and title in html
    assert 'id="ga-portale"' in html
    # Le altre guide non vanno mescolate.
    assert GUIDE["bo"][0] not in html and GUIDE["vendor"][0] not in html


@pytest.mark.django_db
def test_guida_backoffice_nella_dashboard_bo(client):
    bo = User.objects.create_user(
        email="guida-bo@example.invalid", password=PASSWORD, role="bo_user"
    )
    client.force_login(bo)

    html = _html(client.get(reverse("portal:bo-dashboard")))

    guide_id, title = GUIDE["bo"]
    assert guide_id in html and title in html
    assert 'id="gb-documenti"' in html
    assert GUIDE["admin"][0] not in html


@pytest.mark.django_db
def test_guida_fornitore_prima_degli_alert(client):
    user = VendorUserFactory(password=PASSWORD)
    client.force_login(user)

    html = _html(client.get(reverse("portal:dashboard")))

    guide_id, title = GUIDE["vendor"]
    assert guide_id in html and title in html
    assert 'id="gv-alert"' in html
    # Nome fornitore -> guida -> alert/KPI.
    assert html.index(user.vendor.name) < html.index(guide_id)
    assert html.index(guide_id) < html.index("Documenti Contrattuali</h5>")


@pytest.mark.django_db
def test_guida_fornitore_non_espone_informazioni_interne(client):
    user = VendorUserFactory(password=PASSWORD)
    client.force_login(user)

    html = _html(client.get(reverse("portal:dashboard")))
    guida = html[html.index("data-guide-root") : html.index("guide.js")]

    for termine in ("Embyon", "Valutazione finale", "BO User", "/admin/"):
        assert termine not in guida
