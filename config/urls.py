from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.shortcuts import redirect
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from vendor_management_system.documents.views import HomeRedirectView

# Schema per API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Vendor Management System API",
        default_version='v1',
        description="Sistema di Gestione Fornitori con Documenti",
        contact=openapi.Contact(email="fabio-bui@fulgard.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=[
        path('vendors/', include('vendor_management_system.vendors.urls')),
        path('users/', include('vendor_management_system.users.urls')),
        path('purchase-orders/', include('vendor_management_system.purchase_orders.urls')),
        path('documents/', include('vendor_management_system.documents.urls')),
    ],
)

# Homepage con redirect automatico
def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard-redirect')
    else:
        # Redirect to login page if not authenticated
        return redirect('login')

urlpatterns = [
    # Homepage con redirect automatico
    path('', home_view, name='home'),
    
    # Admin
    path(settings.ADMIN_URL, admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    
    # Core (include dashboard redirect)
    path('core/', include('vendor_management_system.core.urls')),
    
    # Apps
    path('vendors/', include('vendor_management_system.vendors.urls')),
    path('users/', include('vendor_management_system.users.urls')),
    path('purchase-orders/', include('vendor_management_system.purchase_orders.urls')),
    path('auth/', include('vendor_management_system.core.auth_urls')),
    path('documents/', include('vendor_management_system.documents.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
