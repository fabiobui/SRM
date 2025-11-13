from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.urls import reverse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken

from vendor_management_system.core.serializers import QueryParamAuthTokenSerializer


# Custom view to obtain an auth token
class QueryParamObtainAuthToken(ObtainAuthToken):
    serializer_class = QueryParamAuthTokenSerializer

    @swagger_auto_schema(
        operation_id="core--obtain-auth-token",
        operation_description="Obtain an auth token for a user",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Email address of the user",
                    format="email",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Password of the user",
                    format="password",
                ),
            },
        ),
        responses={
            status.HTTP_200_OK: openapi.Response(
                "The auth token",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"token": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            status.HTTP_400_BAD_REQUEST: "Bad request",
        },
        tags=["Rest API Authentication"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@login_required
def dashboard_redirect(request):
    """Reindirizza l'utente alla dashboard appropriata in base al ruolo"""
    user = request.user
    # Controlla se l'utente ha il campo role (per compatibilità)
    if hasattr(user, 'role'):
        if user.role == 'admin' or user.is_superuser:
            return redirect('/admin/')
        elif user.role == 'bo_user':
            return redirect('/vendors/dashboard/')
        elif user.role == 'vendor' and hasattr(user, 'vendor') and user.vendor:
            return redirect('/documents/portal/')
    
    # Fallback per utenti senza ruolo definito
    if user.is_superuser or user.is_staff:
        return redirect('/admin/')
    else:
        messages.warning(request, "Il tuo account non ha un ruolo assegnato. Contatta l'amministratore.")
        logout_url = reverse('admin:logout')
        admin_url = reverse('admin:index')
        return HttpResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ruolo non assegnato</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="bg-light">
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header bg-warning text-dark">
                                <h4>⚠️ Ruolo non assegnato</h4>
                            </div>
                            <div class="card-body">
                                <p>Il tuo account <strong>{user.email}</strong> non ha un ruolo configurato.</p>
                                <p>Contatta l'amministratore del sistema per assegnare un ruolo.</p>
                                <div class="mt-3">
                                    <a href="{logout_url}" class="btn btn-secondary">Logout</a>
                                    <a href="{admin_url}" class="btn btn-primary">Pannello Admin</a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)