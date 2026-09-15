# Imports
from django.urls import path
from vendor_management_system.vendors.views import (
    VendorViewSet, 
    AddressViewSet, 
    CategoryViewSet,
    CountryViewSet,
    RegionViewSet,
    ProvinceViewSet,
    CompetenceZoneViewSet,
)
from vendor_management_system.vendors.dashboard_views import (
    vendor_dashboard_view,
    dashboard_stats_api,
    dashboard_vendors_list_api,
    export_vendors_excel,
)


# Define the URL patterns for the vendors app
urlpatterns = [
    # Dashboard views
    path(
        "dashboard/",
        vendor_dashboard_view,
        name="vendor-dashboard",
    ),
    # Dashboard API endpoints (BEFORE <vendor_code>/ catch-all)
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
    
    # =========================================================================
    # Geography endpoints (Nazione, Regione, Provincia)
    # =========================================================================
    path(
        "countries/",
        CountryViewSet.as_view({"get": "list"}),
        name="countries--list",
    ),
    path(
        "countries/tree/",
        CountryViewSet.as_view({"get": "tree"}),
        name="countries--tree",
    ),
    path(
        "regions/",
        RegionViewSet.as_view({"get": "list"}),
        name="regions--list",
    ),
    path(
        "provinces/",
        ProvinceViewSet.as_view({"get": "list"}),
        name="provinces--list",
    ),
    
    # =========================================================================
    # Competence Zone endpoints (Zone di Competenza)
    # =========================================================================
    path(
        "competence-zones/",
        CompetenceZoneViewSet.as_view({"get": "list", "post": "create"}),
        name="competence-zones--list-create",
    ),
    path(
        "competence-zones/<uuid:zone_id>/",
        CompetenceZoneViewSet.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="competence-zones--detail",
    ),
]
