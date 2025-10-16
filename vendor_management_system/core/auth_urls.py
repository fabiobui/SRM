# vendor_management_system/core/auth_urls.py

from django.urls import path
from vendor_management_system.core.auth_views import CustomLoginView, CustomLogoutView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]