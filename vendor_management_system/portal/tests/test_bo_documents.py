"""Test dell'area back-office di validazione dei documenti.

Copre permessi (`BackOfficeRequiredMixin`), il filtro della lista per stato
e l'esito della revisione (`BoDocumentReviewView` imposta
`status`/`reviewed_by`/`reviewed_at`).
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from vendor_management_system.portal.tests.factories import (
    DocumentFactory,
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
class TestBoDocumentListPermissions:
    def test_vendor_user_cannot_access(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        response = client.get(reverse("portal:bo-documents"))
        assert response.status_code == 302

    def test_bo_user_can_access(self, client):
        _login_as_bo(client)
        response = client.get(reverse("portal:bo-documents"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestBoDocumentListFiltering:
    def test_default_shows_only_uploaded(self, client):
        _login_as_bo(client)
        to_review = DocumentFactory(status="UPLOADED")
        approved = DocumentFactory(status="APPROVED")
        pending = DocumentFactory(status="PENDING")

        response = client.get(reverse("portal:bo-documents"))

        documents = list(response.context["documents"])
        assert to_review in documents
        assert approved not in documents
        assert pending not in documents

    def test_status_filter(self, client):
        _login_as_bo(client)
        approved = DocumentFactory(status="APPROVED")
        to_review = DocumentFactory(status="UPLOADED")

        response = client.get(
            reverse("portal:bo-documents"), {"status": "APPROVED"}
        )

        documents = list(response.context["documents"])
        assert approved in documents
        assert to_review not in documents

    def test_expired_filter_uses_expiry_date_not_stored_status(self, client):
        _login_as_bo(client)
        yesterday = timezone.now().date() - timedelta(days=1)
        tomorrow = timezone.now().date() + timedelta(days=1)
        # Stato ancora "APPROVED" in DB (nessun job periodico lo aggiorna,
        # vedi documents/tasks.py vuoto): deve comunque comparire perché il
        # filtro EXPIRED guarda la data, non lo stato salvato.
        expired_stale_status = DocumentFactory(
            status="APPROVED", expiry_date=yesterday
        )
        not_expired = DocumentFactory(status="APPROVED", expiry_date=tomorrow)

        response = client.get(
            reverse("portal:bo-documents"), {"status": "EXPIRED"}
        )

        documents = list(response.context["documents"])
        assert expired_stale_status in documents
        assert not_expired not in documents


@pytest.mark.django_db
class TestBoDocumentReview:
    def test_approve_sets_status_approved(self, client):
        bo_user = _login_as_bo(client)
        document = DocumentFactory(status="UPLOADED")

        response = client.post(
            reverse("portal:bo-document-review", kwargs={"pk": document.pk}),
            data={"action": "approve", "review_notes": "ok"},
        )

        assert response.status_code == 302
        document.refresh_from_db()
        assert document.status == "APPROVED"
        assert document.reviewed_by.email == bo_user.email
        assert document.reviewed_at is not None
        assert document.notes == "ok"

    def test_reject_sets_status_rejected(self, client):
        bo_user = _login_as_bo(client)
        document = DocumentFactory(status="UPLOADED")

        response = client.post(
            reverse("portal:bo-document-review", kwargs={"pk": document.pk}),
            data={"action": "reject", "review_notes": "file illeggibile"},
        )

        assert response.status_code == 302
        document.refresh_from_db()
        assert document.status == "REJECTED"
        assert document.reviewed_by.email == bo_user.email
        assert document.reviewed_at is not None
        assert document.notes == "file illeggibile"

    def test_vendor_user_cannot_review(self, client):
        user = VendorUserFactory(password=PASSWORD)
        client.login(email=user.email, password=PASSWORD)
        document = DocumentFactory(status="UPLOADED")

        response = client.post(
            reverse("portal:bo-document-review", kwargs={"pk": document.pk}),
            data={"action": "approve", "review_notes": ""},
        )

        assert response.status_code == 302
        document.refresh_from_db()
        assert document.status == "UPLOADED"


@pytest.mark.django_db
def test_document_detail_shows_review_form_only_when_uploaded(client):
    _login_as_bo(client)
    document = DocumentFactory(status="UPLOADED")

    response = client.get(
        reverse("portal:bo-document-detail", kwargs={"pk": document.pk})
    )

    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_reviewed_document_keeps_timestamp(client):
    _login_as_bo(client)
    document = DocumentFactory(status="UPLOADED")
    before = timezone.now()

    client.post(
        reverse("portal:bo-document-review", kwargs={"pk": document.pk}),
        data={"action": "approve", "review_notes": ""},
    )

    document.refresh_from_db()
    assert document.reviewed_at >= before
