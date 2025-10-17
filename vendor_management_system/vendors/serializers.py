# Imports
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, ValidationError

from vendor_management_system.vendors.models import Vendor


# Serializer for Vendor (Complete Read)
class VendorSerializer(ModelSerializer):
    is_qualified = serializers.ReadOnlyField()
    audit_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Vendor
        fields = [
            # Core fields
            "vendor_code",
            "name",
            "contact_details",
            "address",
            # General information
            "vat_number",
            "fiscal_code",
            "email",
            "reference_contact",
            "phone",
            "website",
            # Performance metrics
            "on_time_delivery_rate",
            "quality_rating_avg",
            "average_response_time",
            "fulfillment_rate",
            # Qualification/Compliance
            "qualification_status",
            "qualification_score",
            "qualification_date",
            "qualification_expiry",
            # Evaluation and operational capacity
            "category",
            "risk_level",
            "country",
            "iso_certifications",
            # Audit and management
            "last_audit_date",
            "next_audit_due",
            "review_notes",
            # Computed properties
            "is_qualified",
            "audit_overdue",
        ]

    # Method to validate the data
    def validate(self, data):
        # Get the list of allowed fields from the Meta class
        allowed_fields = set(self.Meta.fields) - {'is_qualified', 'audit_overdue'}  # Exclude read-only fields

        # Get the list of fields provided in the input data
        received_fields = set(self.initial_data.keys())

        # Calculate the extra fields by subtracting allowed fields from received fields
        extra_fields = received_fields - allowed_fields

        # If there are extra fields, raise a validation error
        if extra_fields:
            raise ValidationError(
                {field: "This field is not allowed." for field in extra_fields}
            )

        # Return the validated data
        return data


# Serializer for Vendor Create/Update (Basic Information)
class VendorCreateUpdateSerializer(ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "name",
            "contact_details",
            "address",
            "vat_number",
            "fiscal_code",
            "email",
            "reference_contact",
            "phone",
            "website",
            "category",
            "country",
        ]

    # Method to validate the data
    def validate(self, data):
        # Get the list of allowed fields from the Meta class
        allowed_fields = set(self.Meta.fields)

        # Get the list of fields provided in the input data
        received_fields = set(self.initial_data.keys())

        # Calculate the extra fields by subtracting allowed fields from received fields
        extra_fields = received_fields - allowed_fields

        # If there are extra fields, raise a validation error
        if extra_fields:
            raise ValidationError(
                {field: "This field is not allowed." for field in extra_fields}
            )

        # Return the validated data
        return data


# Serializer for Vendor Qualification Management
class VendorQualificationSerializer(ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "qualification_status",
            "qualification_score",
            "qualification_date",
            "qualification_expiry",
            "risk_level",
            "iso_certifications",
        ]
        read_only_fields = ["vendor_code", "name"]

    # Method to validate the data
    def validate(self, data):
        # Get the list of allowed fields from the Meta class
        allowed_fields = set(self.Meta.fields) - set(self.Meta.read_only_fields)

        # Get the list of fields provided in the input data
        received_fields = set(self.initial_data.keys())

        # Calculate the extra fields by subtracting allowed fields from received fields
        extra_fields = received_fields - allowed_fields

        # If there are extra fields, raise a validation error
        if extra_fields:
            raise ValidationError(
                {field: "This field is not allowed." for field in extra_fields}
            )

        # Validate qualification dates
        if 'qualification_date' in data and 'qualification_expiry' in data:
            if data['qualification_date'] and data['qualification_expiry']:
                if data['qualification_date'] >= data['qualification_expiry']:
                    raise ValidationError({
                        'qualification_expiry': 'Qualification expiry must be after qualification date.'
                    })

        # Return the validated data
        return data


# Serializer for Vendor Audit Management
class VendorAuditSerializer(ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "last_audit_date",
            "next_audit_due",
            "review_notes",
            "qualification_status",
            "risk_level",
        ]
        read_only_fields = ["vendor_code", "name"]

    # Method to validate the data
    def validate(self, data):
        # Get the list of allowed fields from the Meta class
        allowed_fields = set(self.Meta.fields) - set(self.Meta.read_only_fields)

        # Get the list of fields provided in the input data
        received_fields = set(self.initial_data.keys())

        # Calculate the extra fields by subtracting allowed fields from received fields
        extra_fields = received_fields - allowed_fields

        # If there are extra fields, raise a validation error
        if extra_fields:
            raise ValidationError(
                {field: "This field is not allowed." for field in extra_fields}
            )

        # Validate audit dates
        if 'last_audit_date' in data and 'next_audit_due' in data:
            if data['last_audit_date'] and data['next_audit_due']:
                if data['last_audit_date'] >= data['next_audit_due']:
                    raise ValidationError({
                        'next_audit_due': 'Next audit due must be after last audit date.'
                    })

        # Return the validated data
        return data


# Serializer for Vendor Performance Update
class VendorPerformanceSerializer(ModelSerializer):
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "on_time_delivery_rate",
            "quality_rating_avg",
            "average_response_time",
            "fulfillment_rate",
        ]
        read_only_fields = ["vendor_code", "name"]

    # Method to validate the data
    def validate(self, data):
        # Get the list of allowed fields from the Meta class
        allowed_fields = set(self.Meta.fields) - set(self.Meta.read_only_fields)

        # Get the list of fields provided in the input data
        received_fields = set(self.initial_data.keys())

        # Calculate the extra fields by subtracting allowed fields from received fields
        extra_fields = received_fields - allowed_fields

        # If there are extra fields, raise a validation error
        if extra_fields:
            raise ValidationError(
                {field: "This field is not allowed." for field in extra_fields}
            )

        # Return the validated data
        return data


# Lightweight serializer for vendor listing
class VendorListSerializer(ModelSerializer):
    is_qualified = serializers.ReadOnlyField()
    audit_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "email",
            "phone",
            "category",
            "qualification_status",
            "risk_level",
            "is_qualified",
            "audit_overdue",
        ]