from django.urls import path
from vendor_management_system.documents.views import (
    AdminDashboardView, BackOfficeDashboardView, VendorPortalView, 
    DocumentUploadView, DocumentReviewView
)

urlpatterns = [
    # Dashboards per ruoli diversi
    path('admin/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('backoffice/', BackOfficeDashboardView.as_view(), name='backoffice-dashboard'),
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('portal/', VendorPortalView.as_view(), name='vendor-portal'),
    # Actions
    path('upload/', DocumentUploadView.as_view(), name='document-upload'),
    path('review/<str:document_id>/', DocumentReviewView.as_view(), name='document-review'),
    
    # Backward compatibility
    #path('dashboard/', AdminDashboardView.as_view(), name='old-admin-dashboard'),
]