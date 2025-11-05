# Imports
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Avg, Q, Case, When
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, response, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.authtoken.views import ObtainAuthToken

from vendor_management_system.core.authentication import (
    QueryParameterTokenAuthentication,
)

from vendor_management_system.core.serializers import QueryParamAuthTokenSerializer
from vendor_management_system.vendors.models import Vendor, Address, Category
from vendor_management_system.vendors.serializers import (
    VendorCreateUpdateSerializer,
    VendorSerializer,
    VendorListSerializer,
    VendorQualificationSerializer,
    VendorAuditSerializer,
    VendorPerformanceSerializer,
    AddressSerializer,
    AddressManagementSerializer,
    CategorySerializer,
    CategoryManagementSerializer,
    CategoryCompactSerializer,
    CategoryTreeSerializer,
    CategoryStatsSerializer,
)


# ViewSet per Address
class AddressViewSet(viewsets.ViewSet):
    """ViewSet for managing addresses independently"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [QueryParameterTokenAuthentication]

    @swagger_auto_schema(
        operation_id="addresses--list",
        operation_description="List all addresses",
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
                name="country",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by country",
            ),
            openapi.Parameter(
                name="city",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by city",
            ),
            openapi.Parameter(
                name="address_type",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by address type",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "List of addresses", schema=AddressSerializer(many=True)
            ),
        },
        tags=["Addresses"],
    )
    def list(self, request):
        addresses = Address.objects.filter(is_active=True)
        
        # Apply filters
        country = request.query_params.get('country')
        if country:
            addresses = addresses.filter(country__icontains=country)
            
        city = request.query_params.get('city')
        if city:
            addresses = addresses.filter(city__icontains=city)
            
        address_type = request.query_params.get('address_type')
        if address_type:
            addresses = addresses.filter(address_type=address_type)

        serializer = AddressSerializer(addresses, many=True)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="addresses--create",
        operation_description="Create a new address",
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
        request_body=AddressManagementSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                "Created address", schema=AddressSerializer
            ),
        },
        tags=["Addresses"],
    )
    def create(self, request):
        serializer = AddressManagementSerializer(data=request.data)
        if serializer.is_valid():
            address = serializer.save()
            response_serializer = AddressSerializer(address)
            return response.Response(
                response_serializer.data, status=status.HTTP_201_CREATED
            )
        return response.Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_id="addresses--retrieve",
        operation_description="Retrieve a specific address",
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
                "Address details", schema=AddressSerializer
            ),
        },
        tags=["Addresses"],
    )
    def retrieve(self, request, address_id=None):
        address = get_object_or_404(Address, id=address_id)
        serializer = AddressSerializer(address)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="addresses--update",
        operation_description="Update a specific address",
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
        request_body=AddressManagementSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Updated address", schema=AddressSerializer
            ),
        },
        tags=["Addresses"],
    )
    def update(self, request, address_id=None):
        address = get_object_or_404(Address, id=address_id)
        serializer = AddressManagementSerializer(
            address, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            response_serializer = AddressSerializer(address)
            return response.Response(
                response_serializer.data, status=status.HTTP_200_OK
            )
        return response.Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_id="addresses--destroy",
        operation_description="Delete a specific address",
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
            status.HTTP_204_NO_CONTENT: "Address deleted",
        },
        tags=["Addresses"],
    )
    def destroy(self, request, address_id=None):
        address = get_object_or_404(Address, id=address_id)
        address.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)


# ViewSet per Category
class CategoryViewSet(viewsets.ViewSet):
    """ViewSet for managing categories"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [QueryParameterTokenAuthentication]

    @swagger_auto_schema(
        operation_id="categories--list",
        operation_description="List all categories",
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
                name="is_active",
                format="boolean",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description="Filter by active status",
            ),
            openapi.Parameter(
                name="parent",
                format="uuid",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by parent category ID",
            ),
            openapi.Parameter(
                name="requires_certification",
                format="boolean",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description="Filter by certification requirement",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "List of categories", schema=CategorySerializer(many=True)
            ),
        },
        tags=["Categories"],
    )
    def list(self, request):
        categories = Category.objects.all().order_by('sort_order', 'name')
        
        # Apply filters
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            categories = categories.filter(is_active=is_active.lower() == 'true')
            
        parent = request.query_params.get('parent')
        if parent:
            if parent.lower() == 'null':
                categories = categories.filter(parent__isnull=True)
            else:
                categories = categories.filter(parent__id=parent)
                
        requires_certification = request.query_params.get('requires_certification')
        if requires_certification is not None:
            categories = categories.filter(requires_certification=requires_certification.lower() == 'true')

        serializer = CategorySerializer(categories, many=True)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="categories--create",
        operation_description="Create a new category",
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
        request_body=CategoryManagementSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                "Created category", schema=CategorySerializer
            ),
        },
        tags=["Categories"],
    )
    def create(self, request):
        serializer = CategoryManagementSerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            response_serializer = CategorySerializer(category)
            return response.Response(
                response_serializer.data, status=status.HTTP_201_CREATED
            )
        return response.Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_id="categories--retrieve",
        operation_description="Retrieve a specific category",
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
                "Category details", schema=CategorySerializer
            ),
        },
        tags=["Categories"],
    )
    def retrieve(self, request, category_id=None):
        category = get_object_or_404(Category, id=category_id)
        serializer = CategorySerializer(category)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="categories--update",
        operation_description="Update a specific category",
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
        request_body=CategoryManagementSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Updated category", schema=CategorySerializer
            ),
        },
        tags=["Categories"],
    )
    def update(self, request, category_id=None):
        category = get_object_or_404(Category, id=category_id)
        serializer = CategoryManagementSerializer(
            category, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            response_serializer = CategorySerializer(category)
            return response.Response(
                response_serializer.data, status=status.HTTP_200_OK
            )
        return response.Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @swagger_auto_schema(
        operation_id="categories--destroy",
        operation_description="Delete a specific category",
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
            status.HTTP_204_NO_CONTENT: "Category deleted",
            status.HTTP_400_BAD_REQUEST: "Cannot delete category with vendors",
        },
        tags=["Categories"],
    )
    def destroy(self, request, category_id=None):
        category = get_object_or_404(Category, id=category_id)
        
        # Check if category has vendors
        if category.vendors.exists():
            return response.Response(
                {"detail": "Cannot delete category that has vendors assigned. Please reassign vendors first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if category has subcategories
        if category.subcategories.exists():
            return response.Response(
                {"detail": "Cannot delete category that has subcategories. Please delete subcategories first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        category.delete()
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_id="categories--tree",
        operation_description="Get category hierarchy tree",
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
                "Category tree", schema=CategoryTreeSerializer(many=True)
            ),
        },
        tags=["Categories"],
    )
    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
        # Get only root categories (without parent)
        root_categories = Category.objects.filter(
            parent__isnull=True, 
            is_active=True
        ).order_by('sort_order', 'name')
        
        serializer = CategoryTreeSerializer(root_categories, many=True)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="categories--stats",
        operation_description="Get category statistics",
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
                "Category statistics", schema=CategoryStatsSerializer(many=True)
            ),
        },
        tags=["Categories"],
    )
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
        serializer = CategoryStatsSerializer(categories, many=True)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_id="categories--vendors",
        operation_description="Get vendors in a specific category",
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
                name="include_subcategories",
                format="boolean",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description="Include vendors from subcategories",
            ),
        ],
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Vendors in category", schema=VendorListSerializer(many=True)
            ),
        },
        tags=["Categories"],
    )
    @action(detail=True, methods=['get'], url_path='vendors')
    def vendors(self, request, category_id=None):
        category = get_object_or_404(Category, id=category_id)
        include_subcategories = request.query_params.get('include_subcategories', 'false').lower() == 'true'
        
        if include_subcategories:
            # Get all descendant categories
            categories = [category] + category.get_descendants()
            vendors = Vendor.objects.filter(category__in=categories)
        else:
            vendors = category.vendors.all()
        
        vendors = vendors.order_by('name')
        serializer = VendorListSerializer(vendors, many=True)
        return response.Response(serializer.data, status=status.HTTP_200_OK)


# ViewSet per Vendor
class VendorViewSet(viewsets.ViewSet):
    """ViewSet for managing vendors"""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [QueryParameterTokenAuthentication]

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
                format="uuid",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by category ID",
            ),
            openapi.Parameter(
                name="category_code",
                format="string",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description="Filter by category code",
            ),
            openapi.Parameter(
                name="requires_certification",
                format="boolean",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description="Filter by certification requirement",
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
        # Get all vendors con select_related per ottimizzare
        vendors = Vendor.objects.select_related('category', 'address').all()
        
        # Apply existing filters
        qualification_status = request.query_params.get('qualification_status')
        if qualification_status:
            vendors = vendors.filter(qualification_status=qualification_status)
            
        risk_level = request.query_params.get('risk_level')
        if risk_level:
            vendors = vendors.filter(risk_level=risk_level)
        
        # New category filters
        category = request.query_params.get('category')
        if category:
            vendors = vendors.filter(category__id=category)
            
        category_code = request.query_params.get('category_code')
        if category_code:
            vendors = vendors.filter(category__code__iexact=category_code)
            
        requires_certification = request.query_params.get('requires_certification')
        if requires_certification is not None:
            vendors = vendors.filter(category__requires_certification=requires_certification.lower() == 'true')

        # Serialize the vendors using lightweight serializer
        serializer = VendorListSerializer(vendors, many=True)

        # Return the response
        return response.Response(serializer.data, status=status.HTTP_200_OK)

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
            vendor = vendor_create_serializer.save()

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
                        "missing_certification": openapi.Schema(
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
                        "no_category": openapi.Schema(
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
        overdue_audits = Vendor.objects.select_related('category', 'address').filter(
            next_audit_due__lt=today
        ).exclude(next_audit_due__isnull=True)
        
        # Get vendors with expired qualifications
        expired_qualifications = Vendor.objects.select_related('category', 'address').filter(
            qualification_expiry__lt=today,
            qualification_status='APPROVED'
        ).exclude(qualification_expiry__isnull=True)
        
        # Get high risk vendors
        high_risk_vendors = Vendor.objects.select_related('category', 'address').filter(risk_level='HIGH')
        
        # Get vendors in categories requiring certification but without proper status
        missing_certification = Vendor.objects.select_related('category', 'address').filter(
            category__requires_certification=True,
            qualification_status__in=['PENDING', 'REJECTED']
        )
        
        # Get vendors without category assigned
        no_category = Vendor.objects.select_related('address').filter(category__isnull=True)
        
        data = {
            'overdue_audits': VendorListSerializer(overdue_audits, many=True).data,
            'expired_qualifications': VendorListSerializer(expired_qualifications, many=True).data,
            'high_risk_vendors': VendorListSerializer(high_risk_vendors, many=True).data,
            'missing_certification': VendorListSerializer(missing_certification, many=True).data,
            'no_category': VendorListSerializer(no_category, many=True).data,
        }
        
        return response.Response(data, status=status.HTTP_200_OK)

    # Address management for vendors
    @swagger_auto_schema(
        methods=['get'],
        operation_id="vendors--get-address",
        operation_description="Get vendor address",
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
                "Vendor address", schema=AddressSerializer
            ),
            status.HTTP_404_NOT_FOUND: "Address not found",
        },
        tags=["Vendor Address"],
    )
    @swagger_auto_schema(
        methods=['post'],
        operation_id="vendors--create-address",
        operation_description="Create address for vendor",
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
        request_body=AddressManagementSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                "Created address", schema=AddressSerializer
            ),
        },
        tags=["Vendor Address"],
    )
    @swagger_auto_schema(
        methods=['put'],
        operation_id="vendors--update-address",
        operation_description="Update vendor address",
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
        request_body=AddressManagementSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                "Updated address", schema=AddressSerializer
            ),
        },
        tags=["Vendor Address"],
    )
    @swagger_auto_schema(
        methods=['delete'],
        operation_id="vendors--delete-address",
        operation_description="Delete vendor address",
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
            status.HTTP_204_NO_CONTENT: "Address deleted",
        },
        tags=["Vendor Address"],
    )
    @action(detail=True, methods=['get', 'post', 'put', 'delete'], url_path='address')
    def address_management(self, request, vendor_code=None):
        vendor = get_object_or_404(Vendor, vendor_code=vendor_code)
        
        if request.method == 'GET':
            if vendor.address:
                serializer = AddressSerializer(vendor.address)
                return response.Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return response.Response(
                    {"detail": "Vendor has no address"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif request.method == 'POST':
            if vendor.address:
                return response.Response(
                    {"detail": "Vendor already has an address. Use PUT to update."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = AddressManagementSerializer(data=request.data)
            if serializer.is_valid():
                address = serializer.save()
                vendor.address = address
                vendor.save()
                response_serializer = AddressSerializer(address)
                return response.Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        
        elif request.method == 'PUT':
            if not vendor.address:
                return response.Response(
                    {"detail": "Vendor has no address. Use POST to create."}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = AddressManagementSerializer(
                vendor.address, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                response_serializer = AddressSerializer(vendor.address)
                return response.Response(
                    response_serializer.data, status=status.HTTP_200_OK
                )
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        
        elif request.method == 'DELETE':
            if vendor.address:
                vendor.address.delete()
                vendor.address = None
                vendor.save()
                return response.Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return response.Response(
                    {"detail": "Vendor has no address"}, 
                    status=status.HTTP_404_NOT_FOUND
                )


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


@login_required
def vendor_dashboard_view(request):
    """Vista per la dashboard dei fornitori con statistiche aggregate"""
    from django.db.models import Count, Q
    from vendor_management_system.vendors.serializers import VendorListSerializer
    import json
    
    # Calcola statistiche di base
    total_vendors = Vendor.objects.count()
    active_vendors = Vendor.objects.filter(is_active=True).count()
    pending_qualification = Vendor.objects.filter(qualification_status='PENDING').count()
    high_risk_vendors = Vendor.objects.filter(risk_level='HIGH').count()
    
    # Prepara i dati per i grafici (stesso codice di dashboard_stats_api)
    # Statistiche per categoria
    by_category = list(
        Vendor.objects.values('category__name')
        .annotate(count=Count('vendor_code'))
        .order_by('-count')
    )
    for item in by_category:
        if not item['category__name']:
            item['category'] = 'Non Classificato'
        else:
            item['category'] = item['category__name']
        item.pop('category__name', None)
    
    # Statistiche per stato qualifica
    by_qualification = list(
        Vendor.objects.values('qualification_status')
        .annotate(count=Count('vendor_code'))
        .order_by('qualification_status')
    )
    for item in by_qualification:
        item['status'] = item.pop('qualification_status')
    
    # Statistiche per livello di rischio
    by_risk = list(
        Vendor.objects.values('risk_level')
        .annotate(count=Count('vendor_code'))
        .order_by('risk_level')
    )
    for item in by_risk:
        item['risk'] = item.pop('risk_level')
    
    # Statistiche per paese (top 10)
    by_country_query = Vendor.objects.values('country').annotate(count=Count('vendor_code')).order_by('-count')
    by_country = []
    for item in by_country_query[:10]:
        by_country.append({
            'country': item['country'] if item['country'] else 'Non Specificato',
            'count': item['count']
        })
    
    # Statistiche per qualità media (rating)
    quality_ranges = [
        {'range': '0-1', 'min': 0, 'max': 1},
        {'range': '1-2', 'min': 1, 'max': 2},
        {'range': '2-3', 'min': 2, 'max': 3},
        {'range': '3-4', 'min': 3, 'max': 4},
        {'range': '4-5', 'min': 4, 'max': 5},
        {'range': 'N/A', 'min': None, 'max': None},
    ]
    
    by_quality = []
    for r in quality_ranges:
        if r['min'] is None:
            count = Vendor.objects.filter(quality_rating_avg__isnull=True).count()
        else:
            count = Vendor.objects.filter(
                quality_rating_avg__gte=r['min'],
                quality_rating_avg__lt=r['max']
            ).count()
        by_quality.append({'range': r['range'], 'count': count})
    
    # Statistiche per tasso di adempimento
    fulfillment_ranges = [
        {'range': '0-20%', 'min': 0, 'max': 20},
        {'range': '20-40%', 'min': 20, 'max': 40},
        {'range': '40-60%', 'min': 40, 'max': 60},
        {'range': '60-80%', 'min': 60, 'max': 80},
        {'range': '80-100%', 'min': 80, 'max': 100},
        {'range': 'N/A', 'min': None, 'max': None},
    ]
    
    by_fulfillment = []
    for r in fulfillment_ranges:
        if r['min'] is None:
            count = Vendor.objects.filter(fulfillment_rate__isnull=True).count()
        else:
            count = Vendor.objects.filter(
                fulfillment_rate__gte=r['min'],
                fulfillment_rate__lt=r['max']
            ).count()
        by_fulfillment.append({'range': r['range'], 'count': count})
    
    # Prepara lista vendors
    vendors = Vendor.objects.select_related('category', 'address').all()
    vendors_data = VendorListSerializer(vendors, many=True).data
    
    context = {
        'total_vendors': total_vendors,
        'active_vendors': active_vendors,
        'pending_qualification': pending_qualification,
        'high_risk_vendors': high_risk_vendors,
        # Converti i dati in JSON per JavaScript
        'chart_data_json': json.dumps({
            'by_category': by_category,
            'by_qualification': by_qualification,
            'by_risk': by_risk,
            'by_country': by_country,
            'by_quality': by_quality,
            'by_fulfillment': by_fulfillment,
        }),
        'vendors_data_json': json.dumps(list(vendors_data)),
    }
    
    return render(request, 'vendors/vendor_dashboard.html', context)


from django.http import JsonResponse
from django.db.models import Count, Avg, Q, Case, When, IntegerField


@csrf_exempt
def dashboard_vendors_list_api(request):
    """API endpoint per ottenere la lista semplificata dei fornitori per la dashboard"""
    from vendor_management_system.vendors.serializers import VendorListSerializer
    
    print(f"[dashboard_vendors] User: {request.user}, Auth: {request.user.is_authenticated}")
    print(f"[dashboard_vendors] Session: {request.session.session_key}")
    print(f"[dashboard_vendors] Cookies: {list(request.COOKIES.keys())}")
    
    # L'utente deve essere autenticato - ma controlliamo manualmente
    # perché @login_required causa redirect invece di 401
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    vendors = Vendor.objects.select_related('category', 'address').all()
    serializer = VendorListSerializer(vendors, many=True)
    return JsonResponse(serializer.data, safe=False)


@csrf_exempt
def dashboard_stats_api(request):
    """API endpoint per fornire statistiche aggregate per i grafici della dashboard"""
    
    # Debug
    print(f"[dashboard_stats] User: {request.user}, Auth: {request.user.is_authenticated}")
    print(f"[dashboard_stats] Session: {request.session.session_key}")
    print(f"[dashboard_stats] Cookies: {list(request.COOKIES.keys())}")
    
    # Controllo manuale autenticazione
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    # Statistiche per categoria
    by_category = list(
        Vendor.objects.values('category__name')
        .annotate(
            count=Count('vendor_code'),
            category=Case(
                When(category__isnull=True, then='Non Classificato'),
                default='category__name'
            )
        )
        .values('category', 'count')
        .order_by('-count')
    )
    
    # Fix per categoria None
    for item in by_category:
        if not item['category']:
            item['category'] = 'Non Classificato'
    
    # Statistiche per stato qualifica
    by_qualification = list(
        Vendor.objects.values('qualification_status')
        .annotate(count=Count('vendor_code'))
        .order_by('qualification_status')
    )
    
    for item in by_qualification:
        item['status'] = item.pop('qualification_status')
    
    # Statistiche per livello di rischio
    by_risk = list(
        Vendor.objects.values('risk_level')
        .annotate(count=Count('vendor_code'))
        .order_by('risk_level')
    )
    
    for item in by_risk:
        item['risk'] = item.pop('risk_level')
    
    # Statistiche per paese (top 10)
    by_country_query = Vendor.objects.values('country').annotate(count=Count('vendor_code')).order_by('-count')
    by_country = []
    
    for item in by_country_query[:10]:
        by_country.append({
            'country': item['country'] if item['country'] else 'Non Specificato',
            'count': item['count']
        })
    
    # Statistiche per qualità media (rating)
    quality_ranges = [
        {'range': '0-1', 'min': 0, 'max': 1},
        {'range': '1-2', 'min': 1, 'max': 2},
        {'range': '2-3', 'min': 2, 'max': 3},
        {'range': '3-4', 'min': 3, 'max': 4},
        {'range': '4-5', 'min': 4, 'max': 5},
        {'range': 'N/A', 'min': None, 'max': None},
    ]
    
    by_quality = []
    for r in quality_ranges:
        if r['min'] is None:
            count = Vendor.objects.filter(quality_rating_avg__isnull=True).count()
        else:
            count = Vendor.objects.filter(
                quality_rating_avg__gte=r['min'],
                quality_rating_avg__lt=r['max']
            ).count()
        
        by_quality.append({
            'range': r['range'],
            'count': count
        })
    
    # Statistiche per tasso di adempimento
    fulfillment_ranges = [
        {'range': '0-20%', 'min': 0, 'max': 20},
        {'range': '20-40%', 'min': 20, 'max': 40},
        {'range': '40-60%', 'min': 40, 'max': 60},
        {'range': '60-80%', 'min': 60, 'max': 80},
        {'range': '80-100%', 'min': 80, 'max': 100},
        {'range': 'N/A', 'min': None, 'max': None},
    ]
    
    by_fulfillment = []
    for r in fulfillment_ranges:
        if r['min'] is None:
            count = Vendor.objects.filter(fulfillment_rate__isnull=True).count()
        else:
            count = Vendor.objects.filter(
                fulfillment_rate__gte=r['min'],
                fulfillment_rate__lt=r['max']
            ).count()
        
        by_fulfillment.append({
            'range': r['range'],
            'count': count
        })
    
    return JsonResponse({
        'by_category': by_category,
        'by_qualification': by_qualification,
        'by_risk': by_risk,
        'by_country': by_country,
        'by_quality': by_quality,
        'by_fulfillment': by_fulfillment,
    })


@csrf_exempt
def export_vendors_excel(request):
    """Esporta i fornitori filtrati in formato Excel"""
    
    # Controllo manuale autenticazione
    if not request.user.is_authenticated:
        return HttpResponse('Not authenticated', status=401)
    
    import io
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    from datetime import datetime
    
    # Recupera i parametri di filtro
    category = request.GET.get('category')
    qualification_status = request.GET.get('qualification_status')
    risk_level = request.GET.get('risk_level')
    country = request.GET.get('country')
    search = request.GET.get('search')
    
    # Costruisci la query
    vendors = Vendor.objects.select_related('category', 'address').all()
    
    if category:
        if category == 'Non Classificato':
            vendors = vendors.filter(category__isnull=True)
        else:
            vendors = vendors.filter(category__name=category)
    
    if qualification_status:
        vendors = vendors.filter(qualification_status=qualification_status)
    
    if risk_level:
        vendors = vendors.filter(risk_level=risk_level)
    
    if country:
        if country == 'Non Specificato':
            vendors = vendors.filter(Q(country__isnull=True) | Q(country=''))
        else:
            vendors = vendors.filter(country=country)
    
    if search:
        vendors = vendors.filter(
            Q(vendor_code__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Crea il workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Fornitori"
    
    # Definisci gli headers
    headers = [
        'Codice Fornitore',
        'Nome',
        'Email',
        'Telefono',
        'Categoria',
        'Stato Qualifica',
        'Livello Rischio',
        'Paese',
        'Città',
        'Indirizzo',
        'Partita IVA',
        'Codice Fiscale',
        'Rating Qualità',
        'Tasso Consegna Puntuale',
        'Tasso Adempimento',
        'Tempo Risposta Medio',
        'Data Qualifica',
        'Scadenza Qualifica',
        'Ultimo Audit',
        'Prossimo Audit',
        'Attivo',
        'Note Revisione'
    ]
    
    # Stili per l'header
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    # Scrivi gli headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
    
    # Scrivi i dati
    for row_num, vendor in enumerate(vendors, 2):
        ws.cell(row=row_num, column=1, value=vendor.vendor_code)
        ws.cell(row=row_num, column=2, value=vendor.name or '')
        ws.cell(row=row_num, column=3, value=vendor.email or '')
        ws.cell(row=row_num, column=4, value=vendor.phone or '')
        ws.cell(row=row_num, column=5, value=vendor.category.name if vendor.category else 'Non Classificato')
        
        # Stato qualifica con traduzione
        status_map = {
            'APPROVED': 'Approvato',
            'PENDING': 'In attesa',
            'REJECTED': 'Respinto'
        }
        ws.cell(row=row_num, column=6, value=status_map.get(vendor.qualification_status, vendor.qualification_status or ''))
        
        # Livello rischio con traduzione
        risk_map = {
            'LOW': 'Basso',
            'MEDIUM': 'Medio',
            'HIGH': 'Alto'
        }
        ws.cell(row=row_num, column=7, value=risk_map.get(vendor.risk_level, vendor.risk_level or ''))
        
        ws.cell(row=row_num, column=8, value=vendor.country or '')
        
        # Indirizzo
        if vendor.address:
            ws.cell(row=row_num, column=9, value=vendor.address.city or '')
            ws.cell(row=row_num, column=10, value=vendor.address.full_address or '')
        else:
            ws.cell(row=row_num, column=9, value='')
            ws.cell(row=row_num, column=10, value='')
        
        ws.cell(row=row_num, column=11, value=vendor.vat_number or '')
        ws.cell(row=row_num, column=12, value=vendor.fiscal_code or '')
        ws.cell(row=row_num, column=13, value=vendor.quality_rating_avg if vendor.quality_rating_avg else '')
        ws.cell(row=row_num, column=14, value=vendor.on_time_delivery_rate if vendor.on_time_delivery_rate else '')
        ws.cell(row=row_num, column=15, value=vendor.fulfillment_rate if vendor.fulfillment_rate else '')
        ws.cell(row=row_num, column=16, value=vendor.average_response_time if vendor.average_response_time else '')
        ws.cell(row=row_num, column=17, value=vendor.qualification_date.strftime('%d/%m/%Y') if vendor.qualification_date else '')
        ws.cell(row=row_num, column=18, value=vendor.qualification_expiry.strftime('%d/%m/%Y') if vendor.qualification_expiry else '')
        ws.cell(row=row_num, column=19, value=vendor.last_audit_date.strftime('%d/%m/%Y') if vendor.last_audit_date else '')
        ws.cell(row=row_num, column=20, value=vendor.next_audit_due.strftime('%d/%m/%Y') if vendor.next_audit_due else '')
        ws.cell(row=row_num, column=21, value='Sì' if vendor.is_active else 'No')
        ws.cell(row=row_num, column=22, value=vendor.review_notes or '')
    
    # Autosize columns
    for col_num in range(1, len(headers) + 1):
        column_letter = get_column_letter(col_num)
        max_length = 0
        for cell in ws[column_letter]:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Freeze header row
    ws.freeze_panes = 'A2'
    
    # Salva in memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Crea la response
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    # Nome file con timestamp
    filename = f'fornitori_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response