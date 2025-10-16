from django.urls import path
from vendor_management_system.documents.views import AdminDashboardView, VendorPortalView

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('portal/', VendorPortalView.as_view(), name='vendor-portal'),
]
