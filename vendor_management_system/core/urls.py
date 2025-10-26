# Imports
from django.urls import path
from vendor_management_system.core.views import QueryParamObtainAuthToken, dashboard_redirect
from vendor_management_system.core.test_views import TestUrlConfigView, SimpleTestView

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
    path(
        "test-config/",
        TestUrlConfigView.as_view(),
        name="test-url-config",
    ),
    path(
        "simple-test/",
        SimpleTestView.as_view(),
        name="simple-test",
    ),
]