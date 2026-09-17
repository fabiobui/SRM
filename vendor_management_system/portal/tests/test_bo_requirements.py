"""Test dell'area back-office di validazione dei requisiti professionali.

Copre permessi (`BackOfficeRequiredMixin`), il filtro della lista
(`document_file` presente + `verified`) e l'esito della revisione
(`BoRequirementReviewView` imposta `verified`/`verified_by`/`verified_date`).
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from vendor_management_system.portal.tests.factories import (
    VendorCompetenceFactory,
    VendorUserFactory,
)

User = get_user_model()
PASSWORD = "test-pass-1234"


def _login_as_bo(client, email="bo-reviewer@example.invalid"):
    bo_user = User.objects.create_user(
        email=email, password=PASSWORD, role="bo_user"
    )
    client.login(email=bo_user.email, password=PASSWORD)
    return bo_user


@pytest.mark.django_db
class TestBoRequirementListPermissions:
    def test_vendor_user_cannot_access(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:bo-requirements"))
        assert response.status_code == 302

    def test_bo_user_can_access(self, client):
        _login_as_bo(client)
        response = client.get(reverse("portal:bo-requirements"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestBoRequirementListFiltering:
    def test_default_shows_only_uploaded_and_unverified(self, client):
        _login_as_bo(client)
        to_review = VendorCompetenceFactory(
            document_file="vendor_competences/2026/09/cert.pdf",
            verified=False,
        )
        already_verified = VendorCompetenceFactory(
            document_file="vendor_competences/2026/09/cert2.pdf",
            verified=True,
        )
        not_uploaded = VendorCompetenceFactory(verified=False)

        response = client.get(reverse("portal:bo-requirements"))

        requirements = list(response.context["requirements"])
        assert to_review in requirements
        assert already_verified not in requirements
        assert not_uploaded not in requirements

    def test_verified_filter_shows_verified_only(self, client):
        _login_as_bo(client)
        already_verified = VendorCompetenceFactory(
            document_file="vendor_competences/2026/09/cert3.pdf",
            verified=True,
        )
        to_review = VendorCompetenceFactory(
            document_file="vendor_competences/2026/09/cert4.pdf",
            verified=False,
        )

        response = client.get(
            reverse("portal:bo-requirements"), {"verified": "true"}
        )

        requirements = list(response.context["requirements"])
        assert already_verified in requirements
        assert to_review not in requirements

    def test_expired_filter_uses_expiry_date_not_verified_flag(self, client):
        _login_as_bo(client)
        yesterday = timezone.now().date() - timedelta(days=1)
        tomorrow = timezone.now().date() + timedelta(days=1)
        # Anche se `verified=True` in DB, se la data di scadenza è passata
        # deve comunque comparire nel filtro "scaduti".
        expired_but_verified = VendorCompetenceFactory(
            verified=True, expiry_date=yesterday
        )
        not_expired = VendorCompetenceFactory(
            verified=True, expiry_date=tomorrow
        )

        response = client.get(
            reverse("portal:bo-requirements"), {"verified": "expired"}
        )

        requirements = list(response.context["requirements"])
        assert expired_but_verified in requirements
        assert not_expired not in requirements


@pytest.mark.django_db
class TestBoRequirementReview:
    def test_approve_sets_verified_true(self, client):
        bo_user = _login_as_bo(client)
        requirement = VendorCompetenceFactory(
            document_file="vendor_competences/2026/09/cert.pdf",
            verified=False,
        )

        response = client.post(
            reverse(
                "portal:bo-requirement-review",
                kwargs={"pk": requirement.pk},
            ),
            data={"action": "approve", "review_notes": "ok"},
        )

        assert response.status_code == 302
        requirement.refresh_from_db()
        assert requirement.verified is True
        assert requirement.verified_by == (bo_user.name or bo_user.email)
        assert requirement.verified_date == timezone.now().date()
        assert requirement.notes == "ok"

    def test_reject_sets_verified_false_and_records_reviewer(self, client):
        bo_user = _login_as_bo(client)
        requirement = VendorCompetenceFactory(
            document_file="vendor_competences/2026/09/cert.pdf",
            verified=False,
        )

        response = client.post(
            reverse(
                "portal:bo-requirement-review",
                kwargs={"pk": requirement.pk},
            ),
            data={"action": "reject", "review_notes": "documento illeggibile"},
        )

        assert response.status_code == 302
        requirement.refresh_from_db()
        assert requirement.verified is False
        assert requirement.verified_by == (bo_user.name or bo_user.email)
        assert requirement.verified_date == timezone.now().date()
        assert requirement.notes == "documento illeggibile"

    def test_vendor_user_cannot_review(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        requirement = VendorCompetenceFactory(
            document_file="vendor_competences/2026/09/cert.pdf",
            verified=False,
        )

        response = client.post(
            reverse(
                "portal:bo-requirement-review",
                kwargs={"pk": requirement.pk},
            ),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        requirement.refresh_from_db()
        assert requirement.verified is False
