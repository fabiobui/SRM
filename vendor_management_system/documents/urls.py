from django.urls import path
from vendor_management_system.documents.views import (
    AdminDashboardView, BackOfficeDashboardView, VendorPortalView,
    DocumentUploadView, DocumentReviewView
)
from vendor_management_system.portal.views import LegacyPortalRedirectView

urlpatterns = [
    # Dashboards per ruoli diversi
    path('admin/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('backoffice/', BackOfficeDashboardView.as_view(), name='backoffice-dashboard'),
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    # Vecchio portale fornitore → redirect 301 alla nuova area /portale/.
    # `vendor-portal` resta come name per compatibilità con i template e con
    # `core/auth_views.py` che redirige qui dopo il login.
    path('portal/', LegacyPortalRedirectView.as_view(), name='vendor-portal'),
    # Actions
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('review/<str:document_id>/', DocumentReviewView.as_view(), name='document-review'),
]