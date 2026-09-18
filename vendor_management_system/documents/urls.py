from django.urls import path
from django.views.generic import RedirectView

from vendor_management_system.documents.views import (
    AdminDashboardView,
    DocumentReviewView,
    DocumentUploadView,
)
from vendor_management_system.portal.views import LegacyPortalRedirectView

urlpatterns = [
    # Dashboards per ruoli diversi
    path("admin/", AdminDashboardView.as_view(), name="admin-dashboard"),
    # Vecchia dashboard back-office (contenuto rimosso) → redirect alla
    # nuova dashboard consolidata /portale/backoffice/dashboard/. Il nome
    # URL resta 'backoffice-dashboard' per non rompere i redirect già
    # presenti in views.py (DocumentReviewView, HomeRedirectView).
    path(
        "backoffice/",
        RedirectView.as_view(
            pattern_name="portal:bo-dashboard", permanent=False
        ),
        name="backoffice-dashboard",
    ),
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    # Vecchio portale fornitore → redirect 301 alla nuova area /portale/.
    # `vendor-portal` resta come name per compatibilità con i template e con
    # `core/auth_views.py` che redirige qui dopo il login.
    path("portal/", LegacyPortalRedirectView.as_view(), name="vendor-portal"),
    # Actions
    path("upload/", DocumentUploadView.as_view(), name="document-upload"),
    path(
        "review/<str:document_id>/",
        DocumentReviewView.as_view(),
        name="document-review",
    ),
]
