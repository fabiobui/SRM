# Imports
from django.urls import path

from vendor_management_system.vendors.views import VendorViewSet


# Define the URL patterns for the vendors app
urlpatterns = [
    # Main vendor CRUD operations
    path(
        "",
        VendorViewSet.as_view({"get": "list", "post": "create"}),
        name="vendors--list-create-vendor",
    ),
    path(
        "<vendor_code>/",
        VendorViewSet.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="vendors--detail-vendor",
    ),
    
    # Vendor management specific endpoints
    path(
        "<vendor_code>/qualification/",
        VendorViewSet.as_view({"get": "qualification", "patch": "qualification"}),
        name="vendors--qualification",
    ),
    path(
        "<vendor_code>/audit/",
        VendorViewSet.as_view({"get": "audit", "patch": "audit"}),
        name="vendors--audit",
    ),
    path(
        "<vendor_code>/performance/",
        VendorViewSet.as_view({"get": "performance", "patch": "performance"}),
        name="vendors--performance",
    ),
    
    # Alert and monitoring endpoints
    path(
        "alerts/",
        VendorViewSet.as_view({"get": "alerts"}),
        name="vendors--alerts",
    ),
]