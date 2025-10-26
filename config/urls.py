from django.contrib import admin
from django.urls import include, path, reverse
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
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Homepage con redirect automatico
def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard-redirect')
    
    # Generate dynamic URLs
    admin_url = reverse('admin:index')
    swagger_url = reverse('schema-swagger-ui')
    
    html = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sistema Gestione Fornitori</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card shadow">
                        <div class="card-header bg-primary text-white text-center">
                            <h1><i class="fas fa-building"></i> Sistema Gestione Fornitori</h1>
                        </div>
                        <div class="card-body text-center">
                            <p class="lead">Accedi al sistema con le tue credenziali</p>
                            
                            <div class="mb-4">
                                <h5>🔐 Ruoli Disponibili:</h5>
                                <div class="row text-start">
                                    <div class="col-md-4">
                                        <div class="border rounded p-2 mb-2">
                                            <strong>👑 Admin</strong><br>
                                            <small>Accesso completo</small>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="border rounded p-2 mb-2">
                                            <strong>👥 BO User</strong><br>
                                            <small>Gestione fornitori</small>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="border rounded p-2 mb-2">
                                            <strong>🏢 Vendor</strong><br>
                                            <small>Propri documenti</small>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <a href="{admin_url}" class="btn btn-primary btn-lg">
                                <i class="fas fa-sign-in-alt"></i> Accedi al Sistema
                            </a>
                            
                            <div class="mt-4">
                                <small class="text-muted">
                                    <a href="{swagger_url}">📘 API Documentation</a>
                                </small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

urlpatterns = [
    # Homepage con redirect automatico
    path('', HomeRedirectView.as_view(), name='home'),
    
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


# Swagger settings
schema_view = get_schema_view(
    openapi.Info(
        title="Vendor Management System API",
        default_version="v1",
        description="**Vendor Management System: Django / Django Rest Framework based Vendor Management System.**",
        contact=openapi.Contact(email="rohit.vilas.ingole@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


# Swagger URL pattern
urlpatterns += [
    path(
        "swagger<format>/",
        schema_view.without_ui(cache_timeout=0),
        name="swagger--schema",
    ),
    path(
        "",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="swagger--playground",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="swagger--redoc",
    ),
]
