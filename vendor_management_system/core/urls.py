# Imports
from django.urls import path
from vendor_management_system.core.views import QueryParamObtainAuthToken, dashboard_redirect

# Add the URL patterns for the core app
urlpatterns = [
    path(
        "obtain-auth-token/",
        QueryParamObtainAuthToken.as_view(),
        name="core--obtain-auth-token",
    ),
    path(
        "dashboard/",
        dashboard_redirect,
        name="dashboard-redirect",
    ),
]