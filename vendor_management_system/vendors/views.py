# Imports
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, response, status, viewsets
from rest_framework.decorators import action
from rest_framework.authtoken.views import ObtainAuthToken

from vendor_management_system.core.authentication import (
    QueryParameterTokenAuthentication,
)

from vendor_management_system.vendors.models import Vendor
from vendor_management_system.vendors.serializers import (
    VendorCreateUpdateSerializer,
    VendorSerializer,
    VendorListSerializer,
    VendorQualificationSerializer,
    VendorAuditSerializer,
    VendorPerformanceSerializer,
)

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
    
    if user.is_admin():
        return redirect('admin-dashboard')
    elif user.is_bo_user():
        return redirect('backoffice-dashboard')
    elif user.is_vendor_user():
        return redirect('vendor-portal')
    else:
        messages.warning(request, "Il tuo account non ha un ruolo assegnato. Contatta l'amministratore.")
        return HttpResponse("""
        <div style="padding: 20px; font-family: Arial;">
            <h2>⚠️ Ruolo non assegnato</h2>
            <p>Il tuo account non ha un ruolo configurato.</p>
            <p>Contatta l'amministratore del sistema.</p>
            <a href="/admin/logout/">Logout</a>
        </div>
        """)


# Class based ViewSet for Vendor
class VendorViewSet(viewsets.ViewSet):
    # Set the permission and authentication classes
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [QueryParameterTokenAuthentication]

    # Method to handle listing all vendors
    @swagger_auto_schema(
        operation_id="vendors--list-vendors",
        operation_description="List all vendors with basic information",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
            openapi.Parameter(
                name="qualification_status",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by qualification status (PENDING, APPROVED, REJECTED)",
            ),
            openapi.Parameter(
                name="risk_level",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by risk level (LOW, MEDIUM, HIGH)",
            ),
            openapi.Parameter(
                name="category",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by category",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "List of all vendors", schema=VendorListSerializer(many=True)
            ),
            status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        },
        tags=["Vendors"],
    )
    def list(self, request):
        # Get all vendors
        vendors = Vendor.objects.all()
        
        # Apply filters
        qualification_status = request.query_params.get('qualification_status')
        if qualification_status:
            vendors = vendors.filter(qualification_status=qualification_status)
            
        risk_level = request.query_params.get('risk_level')
        if risk_level:
            vendors = vendors.filter(risk_level=risk_level)
            
        category = request.query_params.get('category')
        if category:
            vendors = vendors.filter(category__icontains=category)

        # Serialize the vendors using lightweight serializer
        serializer = VendorListSerializer(vendors, many=True)

        # Return the response
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    # Method to handle new vendor creation
    @swagger_auto_schema(
        operation_id="vendors--create-vendor",
        operation_description="Create a new vendor",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            )
        ],
        request_body=VendorCreateUpdateSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                "The created vendor", schema=VendorSerializer
            ),
            status.HTTP_400_BAD_REQUEST: "Bad request",
            status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        },
        tags=["Vendors"],
    )
    def create(self, request):
        # Deserialize and validate the request data
        vendor_create_serializer = VendorCreateUpdateSerializer(data=request.data)

        # If the provided data is valid
        if vendor_create_serializer.is_valid():
            # Create a new Vendor object
            vendor = Vendor.objects.create(**vendor_create_serializer.validated_data)

            # Serialize the vendor with full details
            vendor_serializer = VendorSerializer(vendor)

            # Return the response
            return response.Response(
                vendor_serializer.data, status=status.HTTP_201_CREATED
            )

        # Return the error response
        return response.Response(
            vendor_create_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    # Method to handle retrieving a single vendor
    @swagger_auto_schema(
        operation_id="vendors--retrieve-vendor",
        operation_description="Retrieve a specific vendor's complete details",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
            openapi.Parameter(
                name="vendor_code",
                format="string",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="The vendor_code for the vendor to retrieve",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "The retrieved vendor", schema=VendorSerializer
            ),
            status.HTTP_404_NOT_FOUND: "Vendor not found",
            status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        },
        tags=["Vendors"],
    )
    def retrieve(self, request, vendor_code=None):
        # Get the vendor by vendor_code
        vendor = get_object_or_404(Vendor, vendor_code=vendor_code)

        # Serialize the vendor with full details
        serializer = VendorSerializer(vendor)

        # Return the response
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    # Method to handle updating a vendor
    @swagger_auto_schema(
        operation_id="vendors--update-vendor",
        operation_description="Update a specific vendor's basic information",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
            openapi.Parameter(
                name="vendor_code",
                format="string",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="The vendor_code for the vendor to update",
            ),
        ],
        request_body=VendorCreateUpdateSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "The updated vendor", schema=VendorSerializer
            ),
            status.HTTP_400_BAD_REQUEST: "Bad request",
            status.HTTP_404_NOT_FOUND: "Vendor not found",
            status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        },
        tags=["Vendors"],
    )
    def update(self, request, vendor_code=None):
        # Get the vendor by vendor_code
        vendor = get_object_or_404(Vendor, vendor_code=vendor_code)

        # Deserialize and validate the data
        vendor_update_serializer = VendorCreateUpdateSerializer(
            vendor, data=request.data, partial=True
        )

        # If the provided data is valid
        if vendor_update_serializer.is_valid():
            # Save the vendor
            vendor_update_serializer.save()

            # Fetch the updated vendor
            vendor = Vendor.objects.get(vendor_code=vendor_code)

            # Serialize the vendor
            serializer = VendorSerializer(vendor)

            # Return the response
            return response.Response(serializer.data, status=status.HTTP_200_OK)

        # Return the error response
        return response.Response(
            vendor_update_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    # Method to handle deleting a vendor
    @swagger_auto_schema(
        operation_id="vendors--destroy-vendor",
        operation_description="Delete a specific vendor",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
            openapi.Parameter(
                name="vendor_code",
                format="string",
                in_=openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                required=True,
                description="The vendor_code for the vendor to delete",
            ),
        ],
        responses={
            status.HTTP_204_NO_CONTENT: "Vendor deleted",
            status.HTTP_404_NOT_FOUND: "Vendor not found",
            status.HTTP_401_UNAUTHORIZED: "Unauthorized",
        },
        tags=["Vendors"],
    )
    def destroy(self, request, vendor_code=None):
        # Get the vendor by vendor_code
        vendor = get_object_or_404(Vendor, vendor_code=vendor_code)

        # Delete the vendor
        vendor.delete()

        # Return the response
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    # Custom action for qualification management
    @swagger_auto_schema(
        methods=['get'],
        operation_id="vendors--get-qualification",
        operation_description="Get vendor qualification details",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Vendor qualification details", schema=VendorQualificationSerializer
            ),
        },
        tags=["Vendor Qualification"],
    )
    @swagger_auto_schema(
        methods=['patch'],
        operation_id="vendors--update-qualification",
        operation_description="Update vendor qualification",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
        ],
        request_body=VendorQualificationSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Updated qualification", schema=VendorQualificationSerializer
            ),
        },
        tags=["Vendor Qualification"],
    )
    @action(detail=True, methods=['get', 'patch'], url_path='qualification')
    def qualification(self, request, vendor_code=None):
        vendor = get_object_or_404(Vendor, vendor_code=vendor_code)
        
        if request.method == 'GET':
            serializer = VendorQualificationSerializer(vendor)
            return response.Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'PATCH':
            serializer = VendorQualificationSerializer(
                vendor, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return response.Response(serializer.data, status=status.HTTP_200_OK)
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

    # Custom action for audit management
    @swagger_auto_schema(
        methods=['get'],
        operation_id="vendors--get-audit",
        operation_description="Get vendor audit details",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Vendor audit details", schema=VendorAuditSerializer
            ),
        },
        tags=["Vendor Audit"],
    )
    @swagger_auto_schema(
        methods=['patch'],
        operation_id="vendors--update-audit",
        operation_description="Update vendor audit information",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
        ],
        request_body=VendorAuditSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Updated audit info", schema=VendorAuditSerializer
            ),
        },
        tags=["Vendor Audit"],
    )
    @action(detail=True, methods=['get', 'patch'], url_path='audit')
    def audit(self, request, vendor_code=None):
        vendor = get_object_or_404(Vendor, vendor_code=vendor_code)
        
        if request.method == 'GET':
            serializer = VendorAuditSerializer(vendor)
            return response.Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'PATCH':
            serializer = VendorAuditSerializer(
                vendor, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return response.Response(serializer.data, status=status.HTTP_200_OK)
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

    # Custom action for performance management
    @swagger_auto_schema(
        methods=['get'],
        operation_id="vendors--get-performance",
        operation_description="Get vendor performance metrics",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Vendor performance metrics", schema=VendorPerformanceSerializer
            ),
        },
        tags=["Vendor Performance"],
    )
    @swagger_auto_schema(
        methods=['patch'],
        operation_id="vendors--update-performance",
        operation_description="Update vendor performance metrics",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
        ],
        request_body=VendorPerformanceSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Updated performance metrics", schema=VendorPerformanceSerializer
            ),
        },
        tags=["Vendor Performance"],
    )
    @action(detail=True, methods=['get', 'patch'], url_path='performance')
    def performance(self, request, vendor_code=None):
        vendor = get_object_or_404(Vendor, vendor_code=vendor_code)
        
        if request.method == 'GET':
            serializer = VendorPerformanceSerializer(vendor)
            return response.Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'PATCH':
            serializer = VendorPerformanceSerializer(
                vendor, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return response.Response(serializer.data, status=status.HTTP_200_OK)
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

    # Custom action to get vendors requiring attention
    @swagger_auto_schema(
        operation_id="vendors--get-alerts",
        operation_description="Get vendors requiring attention (overdue audits, expired qualifications, etc.)",
        manual_parameters=[
            openapi.Parameter(
                name="token",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="The token to authenticate the user",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Vendors requiring attention", 
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "overdue_audits": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "vendor_code": openapi.Schema(type=openapi.TYPE_STRING),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "email": openapi.Schema(type=openapi.TYPE_STRING),
                                    "phone": openapi.Schema(type=openapi.TYPE_STRING),
                                    "category": openapi.Schema(type=openapi.TYPE_STRING),
                                    "qualification_status": openapi.Schema(type=openapi.TYPE_STRING),
                                    "risk_level": openapi.Schema(type=openapi.TYPE_STRING),
                                    "is_qualified": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    "audit_overdue": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        ),
                        "expired_qualifications": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "vendor_code": openapi.Schema(type=openapi.TYPE_STRING),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "email": openapi.Schema(type=openapi.TYPE_STRING),
                                    "phone": openapi.Schema(type=openapi.TYPE_STRING),
                                    "category": openapi.Schema(type=openapi.TYPE_STRING),
                                    "qualification_status": openapi.Schema(type=openapi.TYPE_STRING),
                                    "risk_level": openapi.Schema(type=openapi.TYPE_STRING),
                                    "is_qualified": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    "audit_overdue": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        ),
                        "high_risk_vendors": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "vendor_code": openapi.Schema(type=openapi.TYPE_STRING),
                                    "name": openapi.Schema(type=openapi.TYPE_STRING),
                                    "email": openapi.Schema(type=openapi.TYPE_STRING),
                                    "phone": openapi.Schema(type=openapi.TYPE_STRING),
                                    "category": openapi.Schema(type=openapi.TYPE_STRING),
                                    "qualification_status": openapi.Schema(type=openapi.TYPE_STRING),
                                    "risk_level": openapi.Schema(type=openapi.TYPE_STRING),
                                    "is_qualified": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    "audit_overdue": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                }
                            )
                        ),
                    }
                )
            ),
        },
        tags=["Vendor Alerts"],
    )
    @action(detail=False, methods=['get'], url_path='alerts')
    def alerts(self, request):
        from django.utils import timezone
        today = timezone.now().date()
        
        # Get vendors with overdue audits
        overdue_audits = Vendor.objects.filter(
            next_audit_due__lt=today
        ).exclude(next_audit_due__isnull=True)
        
        # Get vendors with expired qualifications
        expired_qualifications = Vendor.objects.filter(
            qualification_expiry__lt=today,
            qualification_status='APPROVED'
        ).exclude(qualification_expiry__isnull=True)
        
        # Get high risk vendors
        high_risk_vendors = Vendor.objects.filter(risk_level='HIGH')
        
        data = {
            'overdue_audits': VendorListSerializer(overdue_audits, many=True).data,
            'expired_qualifications': VendorListSerializer(expired_qualifications, many=True).data,
            'high_risk_vendors': VendorListSerializer(high_risk_vendors, many=True).data,
        }
        
        return response.Response(data, status=status.HTTP_200_OK)