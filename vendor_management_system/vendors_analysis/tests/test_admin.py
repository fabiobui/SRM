"""Sezione admin "Vendors - Analysis and Classification" (AIDEV-46).

VendorAnalysisSection è un modello proxy su vendors.Vendor registrato solo
per far esistere la sezione in /admin (nascosto dal menu, vedi
JAZZMIN_SETTINGS["hide_models"] in config/settings.py): l'unica voce
visibile deve essere il custom_link "Dashboard" verso vendors/dashboard/,
sullo stesso pattern già usato per "Back office portal" (portal app). La
stessa etichetta rinomina anche la scorciatoia "Selezione" nella barra in
alto (topmenu_links), che punta alla stessa route.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()
PASSWORD = "test-pass-1234"


@pytest.fixture
def staff_user(db):
    # Utente BO "di staff" ma non superuser: create_user() vieta
    # is_staff=True direttamente (vedi users/managers.py), quindi lo
    # impostiamo dopo, come farebbe un admin dal pannello utenti.
    user = User.objects.create_user(
        email="staff@test.com", password=PASSWORD, role="bo_user"
    )
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        email="superadmin@test.com", password=PASSWORD
    )


@pytest.mark.django_db
class TestAdminIndexSection:
    def _login(self, user):
        client = Client()
        client.login(email=user.email, password=PASSWORD)
        return client

    def test_dashboard_link_visible_to_staff_user(self, staff_user):
        client = self._login(staff_user)

        response = client.get(reverse("admin:index"))

        assert response.status_code == 200
        assert b"Vendors - Analysis and Classification" in response.content
        assert b"/vendors/dashboard/" in response.content

    def test_dashboard_link_visible_to_superuser(self, superuser):
        client = self._login(superuser)

        response = client.get(reverse("admin:index"))

        assert response.status_code == 200
        assert b"Vendors - Analysis and Classification" in response.content

    def test_old_selezione_shortcut_no_longer_present(self, superuser):
        """Sia il custom_link laterale che il topmenu_links in alto sono
        stati rinominati: per il superuser, che vede tutte le sezioni,
        "Selezione" non deve più comparire da nessuna parte."""
        client = self._login(superuser)

        response = client.get(reverse("admin:index"))

        assert b"Selezione" not in response.content


@pytest.mark.django_db
class TestHiddenProxyModelHasNoRealCrud:
    """Il modello esiste solo per agganciare la sezione: non deve aprire
    una seconda interfaccia di modifica sui fornitori, ridondante con
    /admin/vendors/vendor/."""

    def test_add_is_blocked(self, superuser):
        client = Client()
        client.login(email=superuser.email, password=PASSWORD)

        response = client.get(
            reverse("admin:vendors_analysis_vendoranalysissection_add")
        )

        assert response.status_code == 403

    def test_changelist_is_view_only(self, superuser):
        client = Client()
        client.login(email=superuser.email, password=PASSWORD)

        response = client.get(
            reverse("admin:vendors_analysis_vendoranalysissection_changelist")
        )

        assert response.status_code == 200
        assert b"Add" not in response.content
