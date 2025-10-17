# Imports
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, ValidationError

from vendor_management_system.vendors.models import Vendor, Address, Category

# Serializer per Category
class CategorySerializer(ModelSerializer):
    full_name = serializers.ReadOnlyField()
    level = serializers.ReadOnlyField()
    vendor_count = serializers.ReadOnlyField()
    total_vendor_count = serializers.ReadOnlyField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    subcategories = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id',
            'code',
            'name',
            'description',
            'parent',
            'parent_name',
            'is_active',
            'sort_order',
            'color_code',
            'requires_certification',
            'default_risk_level',
            'created_at',
            'updated_at',
            'full_name',
            'level',
            'vendor_count',
            'total_vendor_count',
            'subcategories',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name', 'level', 'vendor_count', 'total_vendor_count', 'parent_name', 'subcategories']

    def validate(self, data):
        # Validazione per evitare cicli nella gerarchia
        if 'parent' in data and data['parent']:
            parent = data['parent']
            instance = self.instance
            
            if instance and parent == instance:
                raise ValidationError({
                    'parent': 'Una categoria non può essere genitore di se stessa.'
                })
            
            # Controlla cicli più profondi
            if instance:
                ancestors = parent.get_ancestors(include_self=True)
                if instance in ancestors:
                    raise ValidationError({
                        'parent': 'Questa relazione creerebbe un ciclo nella gerarchia.'
                    })
        
        # Validazione codice colore
        if 'color_code' in data and data['color_code']:
            import re
            if not re.match(r'^#[0-9A-Fa-f]{6}$', data['color_code']):
                raise ValidationError({
                    'color_code': 'Il codice colore deve essere in formato esadecimale (es. #FF5733).'
                })

        return data


# Serializer per Category (versione compatta per nested use)
class CategoryCompactSerializer(ModelSerializer):
    full_name = serializers.ReadOnlyField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = [
            'id',
            'code',
            'name',
            'full_name',
            'parent_name',
            'color_code',
            'requires_certification',
            'default_risk_level',
        ]


# Serializer per gestione Category con validazioni specifiche
class CategoryManagementSerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'code',
            'name',
            'description',
            'parent',
            'is_active',
            'sort_order',
            'color_code',
            'requires_certification',
            'default_risk_level',
        ]

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

        # Validazione codice univoco
        if 'code' in data:
            code = data['code'].upper()
            if self.instance and self.instance.code != code:
                if Category.objects.filter(code=code).exists():
                    raise ValidationError({
                        'code': 'Una categoria con questo codice esiste già.'
                    })
            elif not self.instance:
                if Category.objects.filter(code=code).exists():
                    raise ValidationError({
                        'code': 'Una categoria con questo codice esiste già.'
                    })

        # Validazione gerarchia
        if 'parent' in data and data['parent']:
            parent = data['parent']
            instance = self.instance
            
            if instance and parent == instance:
                raise ValidationError({
                    'parent': 'Una categoria non può essere genitore di se stessa.'
                })

        return data


# Serializer per Address (COMPLETO)
class AddressSerializer(ModelSerializer):
    full_address = serializers.ReadOnlyField()
    short_address = serializers.ReadOnlyField()
    
    class Meta:
        model = Address
        fields = [
            'id',
            'street_address',
            'street_address_2',
            'city',
            'state_province',
            'postal_code',
            'country',
            'latitude',
            'longitude',
            'address_type',
            'is_active',
            'notes',
            'full_address',
            'short_address',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_address', 'short_address']

    def validate(self, data):
        # Validazioni personalizzate per l'indirizzo
        if 'postal_code' in data:
            postal_code = data['postal_code']
            country = data.get('country', 'Italia')
            
            # Validazione CAP italiano
            if country == 'Italia':
                if not postal_code.isdigit() or len(postal_code) != 5:
                    raise ValidationError({
                        'postal_code': 'Il CAP italiano deve essere di 5 cifre.'
                    })
        
        return data


# Serializer per Address (versione compatta per nested use)
class AddressCompactSerializer(ModelSerializer):
    full_address = serializers.ReadOnlyField()
    
    class Meta:
        model = Address
        fields = [
            'id',
            'street_address',
            'city',
            'postal_code',
            'country',
            'address_type',
            'full_address',
        ]


# Serializer per Address Management (per le API di gestione indirizzi)
class AddressManagementSerializer(ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'street_address',
            'street_address_2',
            'city',
            'state_province',
            'postal_code',
            'country',
            'latitude',
            'longitude',
            'address_type',
            'is_active',
            'notes',
        ]

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

        # Validazioni personalizzate per l'indirizzo
        if 'postal_code' in data:
            postal_code = data['postal_code']
            country = data.get('country', 'Italia')
            
            # Validazione CAP italiano
            if country == 'Italia':
                if not postal_code.isdigit() or len(postal_code) != 5:
                    raise ValidationError({
                        'postal_code': 'Il CAP italiano deve essere di 5 cifre.'
                    })
        
        return data


# Serializer per Vendor AGGIORNATO (sostituisce quello esistente)
class VendorSerializer(ModelSerializer):
    is_qualified = serializers.ReadOnlyField()
    audit_overdue = serializers.ReadOnlyField()
    address = AddressSerializer(required=False, allow_null=True)
    category = CategoryCompactSerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
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
            "category_id",
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

    def create(self, validated_data):
        # Gestisce la creazione dell'indirizzo se fornito
        address_data = validated_data.pop('address', None)
        category_id = validated_data.pop('category_id', None)
        
        # Imposta la categoria se fornita
        if category_id:
            try:
                category = Category.objects.get(id=category_id, is_active=True)
                validated_data['category'] = category
            except Category.DoesNotExist:
                raise ValidationError({'category_id': 'Categoria non trovata o non attiva.'})
        
        vendor = Vendor.objects.create(**validated_data)
        
        if address_data:
            address = Address.objects.create(**address_data)
            vendor.address = address
            vendor.save()
            
        return vendor

    def update(self, instance, validated_data):
        # Gestisce l'aggiornamento dell'indirizzo e categoria
        address_data = validated_data.pop('address', None)
        category_id = validated_data.pop('category_id', None)
        
        # Gestisce la categoria
        if category_id is not None:
            if category_id:
                try:
                    category = Category.objects.get(id=category_id, is_active=True)
                    validated_data['category'] = category
                except Category.DoesNotExist:
                    raise ValidationError({'category_id': 'Categoria non trovata o non attiva.'})
            else:
                validated_data['category'] = None
        
        # Aggiorna i campi del vendor
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Gestisce l'indirizzo
        if address_data is not None:
            if instance.address:
                # Aggiorna l'indirizzo esistente
                address_serializer = AddressSerializer(
                    instance.address, 
                    data=address_data, 
                    partial=True
                )
                if address_serializer.is_valid():
                    address_serializer.save()
            else:
                # Crea un nuovo indirizzo
                address = Address.objects.create(**address_data)
                instance.address = address
        
        instance.save()
        return instance


# Serializer per Vendor Create/Update aggiornato
class VendorCreateUpdateSerializer(ModelSerializer):
    address = AddressSerializer(required=False, allow_null=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    
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
            "category_id",
            "country",
        ]

    def validate_category_id(self, value):
        if value:
            try:
                category = Category.objects.get(id=value, is_active=True)
                return value
            except Category.DoesNotExist:
                raise ValidationError('Categoria non trovata o non attiva.')
        return value

    def create(self, validated_data):
        address_data = validated_data.pop('address', None)
        category_id = validated_data.pop('category_id', None)
        
        # Imposta la categoria
        if category_id:
            validated_data['category'] = Category.objects.get(id=category_id)
        
        vendor = Vendor.objects.create(**validated_data)
        
        if address_data:
            address = Address.objects.create(**address_data)
            vendor.address = address
            vendor.save()
            
        return vendor

    def update(self, instance, validated_data):
        address_data = validated_data.pop('address', None)
        category_id = validated_data.pop('category_id', None)
        
        # Gestisce la categoria
        if category_id is not None:
            if category_id:
                instance.category = Category.objects.get(id=category_id)
            else:
                instance.category = None
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if address_data is not None:
            if instance.address:
                address_serializer = AddressSerializer(
                    instance.address, 
                    data=address_data, 
                    partial=True
                )
                if address_serializer.is_valid():
                    address_serializer.save()
            else:
                address = Address.objects.create(**address_data)
                instance.address = address
        
        instance.save()
        return instance


# Serializer lightweight per vendor listing aggiornato
class VendorListSerializer(ModelSerializer):
    is_qualified = serializers.ReadOnlyField()
    audit_overdue = serializers.ReadOnlyField()
    address = AddressCompactSerializer(read_only=True)
    category = CategoryCompactSerializer(read_only=True)
    
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
            "address",
        ]


# Serializer specifico per category tree/hierarchy
class CategoryTreeSerializer(ModelSerializer):
    """Serializer per visualizzare la struttura gerarchica delle categorie"""
    subcategories = serializers.SerializerMethodField()
    vendor_count = serializers.ReadOnlyField()
    total_vendor_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Category
        fields = [
            'id',
            'code',
            'name',
            'description',
            'color_code',
            'sort_order',
            'vendor_count',
            'total_vendor_count',
            'subcategories',
        ]
    
    def get_subcategories(self, obj):
        """Ricorsivamente ottiene le sottocategorie"""
        subcategories = obj.subcategories.filter(is_active=True).order_by('sort_order', 'name')
        return CategoryTreeSerializer(subcategories, many=True).data


# Serializer per statistiche categoria
class CategoryStatsSerializer(ModelSerializer):
    vendor_count = serializers.ReadOnlyField()
    total_vendor_count = serializers.ReadOnlyField()
    approved_vendors = serializers.SerializerMethodField()
    pending_vendors = serializers.SerializerMethodField()
    rejected_vendors = serializers.SerializerMethodField()
    high_risk_vendors = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id',
            'code',
            'name',
            'vendor_count',
            'total_vendor_count',
            'approved_vendors',
            'pending_vendors',
            'rejected_vendors',
            'high_risk_vendors',
        ]
    
    def get_approved_vendors(self, obj):
        return obj.vendors.filter(qualification_status='APPROVED').count()
    
    def get_pending_vendors(self, obj):
        return obj.vendors.filter(qualification_status='PENDING').count()
    
    def get_rejected_vendors(self, obj):
        return obj.vendors.filter(qualification_status='REJECTED').count()
    
    def get_high_risk_vendors(self, obj):
        return obj.vendors.filter(risk_level='HIGH').count()


# Serializer per vendor qualification
class VendorQualificationSerializer(ModelSerializer):
    category = CategoryCompactSerializer(read_only=True)
    
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "category",
            "qualification_status",
            "qualification_score",
            "qualification_date",
            "qualification_expiry",
            "risk_level",
            "iso_certifications",
        ]
        read_only_fields = ["vendor_code", "name", "category"]

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

        return data


# Serializer per vendor audit
class VendorAuditSerializer(ModelSerializer):
    category = CategoryCompactSerializer(read_only=True)
    
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "category",
            "last_audit_date",
            "next_audit_due",
            "review_notes",
            "qualification_status",
            "risk_level",
        ]
        read_only_fields = ["vendor_code", "name", "category"]

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

        return data


# Serializer per vendor performance
class VendorPerformanceSerializer(ModelSerializer):
    category = CategoryCompactSerializer(read_only=True)
    
    class Meta:
        model = Vendor
        fields = [
            "vendor_code",
            "name",
            "category",
            "on_time_delivery_rate",
            "quality_rating_avg",
            "average_response_time",
            "fulfillment_rate",
        ]
        read_only_fields = ["vendor_code", "name", "category"]

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

        return data