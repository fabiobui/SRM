# Imports
from django.urls import path
from vendor_management_system.vendors.views import (
    VendorViewSet, 
    AddressViewSet, 
    CategoryViewSet,
    vendor_dashboard_view,
    dashboard_stats_api,
    dashboard_vendors_list_api,
    export_vendors_excel
)


# Define the URL patterns for the vendors app
urlpatterns = [
    # Dashboard views
    path(
        "dashboard/",
        vendor_dashboard_view,
        name="vendor-dashboard",
    ),
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
    
    # Address management for vendors (mantieni dal precedente)
    path(
        "<vendor_code>/address/",
        VendorViewSet.as_view({"get": "get_address", "post": "create_address", "put": "update_address", "delete": "delete_address"}),
        name="vendors--address",
    ),
    
    # Alert and monitoring endpoints
    path(
        "alerts/",
        VendorViewSet.as_view({"get": "alerts"}),
        name="vendors--alerts",
    ),
    
    # Dashboard API endpoints
    path(
        "dashboard-stats/",
        dashboard_stats_api,
        name="dashboard-stats-api",
    ),
    path(
        "dashboard-vendors/",
        dashboard_vendors_list_api,
        name="dashboard-vendors-api",
    ),
    path(
        "export-excel/",
        export_vendors_excel,
        name="export-vendors-excel",
    ),
    
    # Address CRUD operations (standalone) (mantieni dal precedente)
    path(
        "addresses/",
        AddressViewSet.as_view({"get": "list", "post": "create"}),
        name="addresses--list-create",
    ),
    path(
        "addresses/<uuid:address_id>/",
        AddressViewSet.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="addresses--detail",
    ),
    
    # Category CRUD operations (NUOVO)
    path(
        "categories/",
        CategoryViewSet.as_view({"get": "list", "post": "create"}),
        name="categories--list-create",
    ),
    path(
        "categories/<uuid:category_id>/",
        CategoryViewSet.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="categories--detail",
    ),
    
    # Category management endpoints (NUOVO)
    path(
        "categories/tree/",
        CategoryViewSet.as_view({"get": "tree"}),
        name="categories--tree",
    ),
    path(
        "categories/stats/",
        CategoryViewSet.as_view({"get": "stats"}),
        name="categories--stats",
    ),
    path(
        "categories/<uuid:category_id>/vendors/",
        CategoryViewSet.as_view({"get": "vendors"}),
        name="categories--vendors",
    ),
]
