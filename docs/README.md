# Vendor Management System - Architecture Documentation

## 1. System Overview

### Business Purpose and Scope

The **Vendor Management System (VMS)** is a comprehensive Django-based application designed to streamline and automate the entire vendor lifecycle management process. The system serves as a centralized platform for managing vendor relationships, purchase orders, performance tracking, and compliance documentation.

**Core Business Objectives:**
- **Vendor Lifecycle Management**: Complete CRUD operations for vendor information and performance tracking
- **Purchase Order Workflow**: Automated status-driven workflow for order processing from creation to delivery
- **Performance Analytics**: Real-time and historical tracking of vendor performance metrics
- **Compliance Management**: Document tracking with expiry alerts and approval workflows
- **Role-Based Access**: Multi-tier user system supporting different organizational roles

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                           │
│  (Web Interface + API Consumers + Mobile Apps)                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                     API Gateway Layer                           │
│   (Django REST Framework + JWT Authentication)                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                   Business Logic Layer                          │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────┐  │
│  │   Vendors   │   Orders    │  Documents  │  Performance    │  │
│  │ Management  │ Workflow    │ Management  │   Analytics     │  │
│  └─────────────┴─────────────┴─────────────┴─────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────────┐
│                   Data Access Layer                             │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────┐  │
│  │ PostgreSQL  │    Redis    │   Celery    │   File Storage  │  │
│  │  Database   │   Cache     │    Queue    │    (Media)      │  │
│  └─────────────┴─────────────┴─────────────┴─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack

**Backend Framework:**
- **Django 4.x**: Main web framework providing ORM, admin interface, and middleware
- **Django REST Framework**: RESTful API development with serialization and authentication
- **PostgreSQL**: Primary relational database for data persistence
- **Redis**: In-memory data structure store for caching and message brokering

**Background Processing:**
- **Celery**: Distributed task queue for asynchronous processing
- **Celery Beat**: Periodic task scheduler for automated operations
- **Flower**: Real-time monitoring of Celery workers and tasks

**Security & Authentication:**
- **Custom JWT Authentication**: Token-based authentication system
- **Argon2**: Password hashing algorithm for enhanced security
- **Role-Based Access Control**: Multi-tier permission system

**Development & Deployment:**
- **Docker**: Containerization for consistent deployment
- **Docker Compose**: Multi-container application orchestration
- **pytest**: Testing framework for unit and integration tests

### Key Features Summary

- ✅ **Vendor Management**: Complete vendor lifecycle with performance metrics
- ✅ **Smart Purchase Orders**: State-driven workflow with automated transitions
- ✅ **Real-time Performance Tracking**: Automated metrics calculation and historical data
- ✅ **Document Compliance**: Expiry tracking and approval workflows
- ✅ **Multi-role Access**: Admin, Back Office, and Vendor user types
- ✅ **API-First Design**: RESTful APIs with comprehensive documentation
- ✅ **Background Processing**: Automated tasks for performance tracking
- ✅ **Audit Trail**: Complete tracking of order status changes and timestamps

## 2. Business Logic Architecture

### Core Business Processes

#### 2.1 Vendor Lifecycle Management

**Business Logic:**
The system manages vendors through a complete lifecycle from registration to performance evaluation. Each vendor is assigned a unique code and tracked across multiple performance dimensions.

**Key Business Rules:**
- Vendor codes must be uppercase alphanumeric (validated via regex)
- Performance metrics are automatically calculated based on purchase order data
- Historical performance is captured every 6 hours via automated tasks
- Vendors can be linked to user accounts for self-service portal access

**Performance Metrics:**
- **On-time Delivery Rate**: Percentage of orders delivered on or before expected date
- **Quality Rating Average**: Average rating across all completed orders (1-5 scale)
- **Average Response Time**: Time between order issuance and acknowledgment
- **Fulfillment Rate**: Percentage of orders successfully completed vs. cancelled

#### 2.2 Purchase Order Workflow

**State Machine Logic:**
Purchase orders follow a strict state machine with automated transitions and business rule enforcement:

```
PENDING → ISSUED → ACKNOWLEDGED → DELIVERED
    ↓         ↓         ↓
  CANCELLED CANCELLED CANCELLED
```

**State Transition Rules:**

1. **PENDING → ISSUED**
   - Requires vendor assignment
   - Sets `issue_date` automatically via Django signals
   - Only possible from PENDING status

2. **ISSUED → ACKNOWLEDGED**
   - Must be acknowledged by the same vendor that received the order
   - Sets `acknowledgment_date` automatically
   - Validates vendor authorization

3. **ACKNOWLEDGED → DELIVERED**
   - Sets `actual_delivery_date` automatically
   - Triggers vendor performance metric recalculation
   - Enables quality rating assignment

4. **Any State → CANCELLED**
   - Can be cancelled from any non-terminal state
   - Records cancellation timestamp
   - Affects vendor fulfillment rate calculation

**Business Logic Implementation:**
- **Django Signals**: Automatic timestamp setting on status changes
- **ViewSet Actions**: Custom endpoints for each state transition
- **Validation Layer**: Status transition validation in serializers
- **Audit Trail**: Complete tracking of status changes with timestamps

#### 2.3 Performance Analytics System

**Automated Calculation Logic:**
The system employs Celery background tasks to continuously monitor and calculate vendor performance metrics:

**Celery Task: `record_historical_performance`**
- **Frequency**: Every 6 hours (configurable via Celery Beat)
- **Scope**: All active vendors in the system
- **Data Captured**: Snapshot of current performance metrics
- **Storage**: Historical performance records for trend analysis

**Real-time Metrics Calculation:**
Performance metrics are recalculated automatically when purchase orders change status:

```python
# Triggered on order delivery
def calculate_on_time_delivery_rate(vendor):
    total_delivered = vendor.orders.filter(status='DELIVERED').count()
    on_time_delivered = vendor.orders.filter(
        status='DELIVERED',
        actual_delivery_date__lte=F('expected_delivery_date')
    ).count()
    return (on_time_delivered / total_delivered) * 100 if total_delivered > 0 else 0
```

#### 2.4 Document Management Workflow

**Document Lifecycle:**
- **Document Types**: Configurable document requirements (DURC, ISO certifications, etc.)
- **Upload Process**: Vendors upload documents through self-service portal
- **Approval Workflow**: Back office users review and approve/reject documents
- **Expiry Tracking**: Automated alerts for documents nearing expiration
- **Compliance Reporting**: Dashboard views for compliance status across vendors

### Application Architecture

#### 2.5 Django Apps Overview and Responsibilities

**Core App** (`vendor_management_system.core`)
- **Purpose**: Foundation layer providing authentication and common utilities
- **Key Components**:
  - Custom JWT token authentication system
  - Role-based permission classes
  - Common decorators and utilities
  - API authentication endpoints

**Users App** (`vendor_management_system.users`)
- **Purpose**: User management with role-based access control
- **Key Components**:
  - Custom User model extending AbstractUser
  - Three-tier role system: Admin, Back Office, Vendor
  - User-Vendor relationship management
  - Custom user managers for role-specific operations

**Vendors App** (`vendor_management_system.vendors`)
- **Purpose**: Vendor information and performance management
- **Key Components**:
  - Vendor model with performance metrics
  - CRUD operations via ViewSets
  - Performance calculation methods
  - Vendor dashboard routing

**Purchase Orders App** (`vendor_management_system.purchase_orders`)
- **Purpose**: Order lifecycle management with state machine logic
- **Key Components**:
  - Purchase Order model with status workflow
  - State transition actions (issue, acknowledge, deliver, cancel)
  - Django signals for automatic timestamp management
  - Quality rating system

**Historical Performance App** (`vendor_management_system.historical_performances`)
- **Purpose**: Long-term performance analytics and trending
- **Key Components**:
  - Historical performance data model
  - Celery tasks for automated data collection
  - Performance trend analysis
  - Historical reporting APIs

**Documents App** (`vendor_management_system.documents`)
- **Purpose**: Document compliance and lifecycle management
- **Key Components**:
  - Document type configuration
  - Vendor document upload and management
  - Approval workflow with status tracking
  - Expiry alerts and compliance reporting

### Data Model Relationships

#### 2.6 Entity Relationship Architecture

**Core Entities and Relationships:**

```
User (1) ←→ (0..1) Vendor
  ↓
  │ (role-based access)
  ↓
Vendor (1) ←→ (*) PurchaseOrder
  ↓                    ↓
  │ (performance)      │ (history)
  ↓                    ↓
HistoricalPerformance  OrderStatusHistory
  ↑
  │ (automated capture)
  ↑
Vendor (1) ←→ (*) VendorDocument
              ↓
              │ (compliance)
              ↓
            DocumentType
```

**Relationship Details:**

1. **User ↔ Vendor** (Optional One-to-One)
   - Vendors can have associated user accounts for portal access
   - Users with 'vendor' role must have a linked Vendor
   - Enables self-service document management and order tracking

2. **Vendor ↔ PurchaseOrder** (One-to-Many)
   - Each purchase order belongs to exactly one vendor
   - Vendors can have multiple orders across different time periods
   - Foreign key relationship with CASCADE deletion protection

3. **Vendor ↔ HistoricalPerformance** (One-to-Many)
   - Automated snapshots of vendor performance metrics
   - Time-series data for trend analysis
   - Captured every 6 hours via Celery tasks

4. **Vendor ↔ VendorDocument** (One-to-Many)
   - Vendors maintain multiple compliance documents
   - Documents have approval status and expiry tracking
   - Linked to DocumentType for requirement validation

**Business Rule Constraints:**

- **Vendor Code Uniqueness**: Primary key with regex validation (uppercase alphanumeric)
- **Purchase Order Number**: Unique identifier with similar validation
- **Status Transition Logic**: Database-level constraints ensure valid state changes
- **Date Consistency**: Check constraints ensure delivery dates are logical
- **Performance Bounds**: Validation ensures metrics stay within valid ranges (0-100% for rates, 1-5 for ratings)

### API Design Patterns

#### 2.7 RESTful Architecture Principles

**Resource-Based URLs:**
```
/api/vendors/                     # Vendor collection
/api/vendors/{vendor_code}/       # Individual vendor
/api/purchase-orders/             # Order collection  
/api/purchase-orders/{po_number}/ # Individual order
```

**State Transition Endpoints:**
```
POST /api/purchase-orders/{po_number}/issue/       # PENDING → ISSUED
POST /api/purchase-orders/{po_number}/acknowledge/ # ISSUED → ACKNOWLEDGED  
POST /api/purchase-orders/{po_number}/deliver/     # ACKNOWLEDGED → DELIVERED
POST /api/purchase-orders/{po_number}/cancel/      # Any → CANCELLED
```

**Authentication Flow:**
- JWT token-based authentication via query parameter
- Role-based access control enforced at ViewSet level
- Custom permission classes for granular access control

This architecture provides a robust foundation for vendor management with automated workflows, real-time performance tracking, and comprehensive audit trails.

## 3. Detailed Data Model Architecture

### 3.1 Core Entity Models

#### User Model (`vendor_management_system.users.models.User`)

**Purpose**: Extended Django User model with role-based access control and vendor association.

**Key Fields:**
```python
class User(AbstractUser):
    id = CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    name = CharField(max_length=255)  # Replaces first_name/last_name
    email = EmailField(unique=True)   # Primary authentication field
    role = CharField(max_length=20, choices=ROLE_CHOICES, default='bo_user')
    vendor = ForeignKey("vendors.Vendor", null=True, blank=True)
```

**Business Logic:**
- **Role Hierarchy**: Admin > Back Office User > Vendor User
- **Automatic Group Assignment**: Users automatically assigned to Django groups on creation
- **Vendor Association**: Vendor role users must be linked to a Vendor record
- **Permission Methods**: Built-in methods for role-based access control

**Key Methods:**
- `is_admin()`: Checks for admin privileges
- `can_manage_vendors()`: Permission to modify vendor data
- `can_view_all_documents()`: Access to cross-vendor document data
- `assign_to_group()`: Automatic group assignment based on role

#### Vendor Model (`vendor_management_system.vendors.models.Vendor`)

**Purpose**: Central entity representing vendor organizations with performance tracking.

**Key Fields:**
```python
class Vendor(models.Model):
    vendor_code = CharField(max_length=10, primary_key=True)  # Auto-generated
    name = CharField(max_length=255)
    contact_details = TextField()
    address = TextField()
    
    # Performance Metrics (auto-calculated)
    on_time_delivery_rate = FloatField(0-100, null=True)
    quality_rating_avg = FloatField(0-5, null=True)  
    average_response_time = FloatField(min=0, null=True)  # Hours
    fulfillment_rate = FloatField(0-100, null=True)
```

**Business Rules:**
- **Vendor Code Generation**: Automatic UUID-based code generation (10 chars, uppercase)
- **Performance Metrics**: Calculated automatically from purchase order data
- **Validation**: Regex validation for vendor codes (alphanumeric uppercase only)
- **Soft Dependencies**: Can exist without associated purchase orders

#### Purchase Order Model (`vendor_management_system.purchase_orders.models.PurchaseOrder`)

**Purpose**: Represents purchase orders with state machine workflow and automatic date tracking.

**Key Fields:**
```python
class PurchaseOrder(models.Model):
    po_number = CharField(max_length=10, primary_key=True)  # Auto-generated
    vendor = ForeignKey("vendors.Vendor", null=True)
    order_date = DateTimeField(default=timezone.now)
    expected_delivery_date = DateTimeField(null=True)  # Auto-calculated
    actual_delivery_date = DateTimeField(null=True)    # Set on delivery
    
    items = JSONField()  # Product details and quantities
    quantity = IntegerField(min=1)  # Total quantity (auto-calculated)
    
    # Workflow fields
    status = CharField(choices=STATUS_CHOICES, default='PENDING')
    issue_date = DateTimeField(null=True)           # Set via signal
    acknowledgment_date = DateTimeField(null=True)  # Set via signal
    quality_rating = FloatField(choices=[(1,1)...(5,5)], null=True)
```

**Status Workflow:**
```
PENDING → ISSUED → ACKNOWLEDGED → DELIVERED
   ↓        ↓         ↓
CANCELLED CANCELLED CANCELLED
```

**Automatic Calculations:**
- **PO Number**: UUID-based generation (10 chars, uppercase)
- **Expected Delivery**: Default 21 days from order date
- **Total Quantity**: Sum of all item quantities in JSON field
- **Status Dates**: Automatically set via Django signals on status changes

#### Historical Performance Model (`vendor_management_system.historical_performances.models.HistoricalPerformance`)

**Purpose**: Time-series data capture for vendor performance analytics and trending.

**Key Fields:**
```python
class HistoricalPerformance(models.Model):
    id = CharField(max_length=10, primary_key=True)  # Auto-generated
    vendor = ForeignKey("vendors.Vendor", on_delete=CASCADE)
    date = DateTimeField(default=timezone.now)
    
    # Snapshot of vendor metrics at capture time
    on_time_delivery_rate = FloatField(0-100, null=True)
    quality_rating_avg = FloatField(0-5, null=True)
    average_response_time = FloatField(min=0, null=True)
    fulfillment_rate = FloatField(0-100, null=True)
```

**Automation:**
- **Data Capture**: Celery task runs every 6 hours
- **Complete Vendor Sweep**: All vendors captured in single transaction
- **Historical Trending**: Enables performance analysis over time
- **Data Integrity**: Atomic transactions ensure consistent snapshots

#### Document Management Models

**DocumentType Model** (`vendor_management_system.documents.models.DocumentType`):
```python
class DocumentType(models.Model):
    id = CharField(max_length=10, primary_key=True)
    name = CharField(max_length=100)  # e.g., "DURC", "ISO 9001"
    description = TextField()
    is_required = BooleanField(default=True)
    validity_period_days = IntegerField(null=True)  # Auto-expiry calculation
```

**VendorDocument Model** (`vendor_management_system.documents.models.VendorDocument`):
```python
class VendorDocument(models.Model):
    id = CharField(max_length=10, primary_key=True)
    vendor = ForeignKey("vendors.Vendor")
    document_type = ForeignKey("DocumentType")
    file = FileField(upload_to='vendor_documents/')
    
    # Workflow fields
    status = CharField(choices=STATUS_CHOICES, default='PENDING')
    uploaded_date = DateTimeField(auto_now_add=True)
    expiry_date = DateTimeField(null=True)
    approved_date = DateTimeField(null=True)
    approved_by = ForeignKey("users.User", null=True)
```

### 3.2 Database Relationships and Constraints

#### Primary Relationships

**1. User ↔ Vendor (Optional One-to-One)**
```python
# User model
vendor = ForeignKey("vendors.Vendor", null=True, blank=True, related_name="users")

# Business Logic:
- Vendor role users MUST have vendor association
- Multiple users can share the same vendor (team accounts)
- Non-vendor users have null vendor reference
```

**2. Vendor ↔ PurchaseOrder (One-to-Many)**
```python
# PurchaseOrder model  
vendor = ForeignKey("vendors.Vendor", on_delete=SET_NULL, null=True)

# Business Logic:
- SET_NULL on vendor deletion preserves order history
- Orders can exist without vendor (draft state)
- Vendor performance calculated from associated orders
```

**3. Vendor ↔ HistoricalPerformance (One-to-Many)**
```python
# HistoricalPerformance model
vendor = ForeignKey("vendors.Vendor", on_delete=CASCADE)

# Business Logic:
- CASCADE deletion removes all historical data
- Time-series relationship for performance trending
- Automated data population via Celery tasks
```

**4. Vendor ↔ VendorDocument (One-to-Many)**
```python
# VendorDocument model
vendor = ForeignKey("vendors.Vendor", on_delete=CASCADE)
document_type = ForeignKey("DocumentType", on_delete=PROTECT)

# Business Logic:
- PROTECT prevents deletion of referenced document types
- Multiple documents per type allowed (renewals)
- Compliance tracking per vendor
```

#### Database Constraints and Validation

**Field-Level Constraints:**
```sql
-- Vendor performance metrics bounds
CHECK (on_time_delivery_rate >= 0 AND on_time_delivery_rate <= 100)
CHECK (quality_rating_avg >= 0 AND quality_rating_avg <= 5)
CHECK (average_response_time >= 0)
CHECK (fulfillment_rate >= 0 AND fulfillment_rate <= 100)

-- Purchase order quantity validation  
CHECK (quantity >= 1)

-- Date consistency
CHECK (actual_delivery_date IS NULL OR actual_delivery_date >= order_date)
CHECK (expected_delivery_date IS NULL OR expected_delivery_date >= order_date)
```

**Business Rule Constraints:**
```python
# Custom validation in models and serializers
def clean(self):
    # Purchase Order validation
    if self.status == 'DELIVERED' and not self.quality_rating:
        raise ValidationError("Quality rating required for delivered orders")
    
    # User-Vendor consistency
    if self.role == 'vendor' and not self.vendor:
        raise ValidationError("Vendor role requires vendor association")
    
    # Document expiry logic
    if self.expiry_date and self.expiry_date < timezone.now().date():
        raise ValidationError("Document has expired")
```

### 3.3 Data Integrity and Performance

#### Indexing Strategy

**Primary Indices:**
- `vendor_code` (Primary Key, unique, B-tree)
- `po_number` (Primary Key, unique, B-tree)  
- `user.email` (Unique, B-tree)

**Performance Indices:**
```sql
-- Query optimization for common lookups
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);
CREATE INDEX idx_purchase_orders_vendor_date ON purchase_orders(vendor_id, order_date);
CREATE INDEX idx_historical_performance_vendor_date ON historical_performance(vendor_id, date);
CREATE INDEX idx_vendor_documents_expiry ON vendor_documents(expiry_date) WHERE expiry_date IS NOT NULL;
```

#### Data Consistency Mechanisms

**Django Signals for Automatic Data Management:**
```python
@receiver(pre_save, sender=PurchaseOrder)
def set_status_dates(sender, instance, **kwargs):
    """Automatically set timestamps on status changes"""
    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            if instance.status == 'ISSUED':
                instance.issue_date = timezone.now()
            elif instance.status == 'ACKNOWLEDGED':  
                instance.acknowledgment_date = timezone.now()
            elif instance.status == 'DELIVERED':
                instance.actual_delivery_date = timezone.now()
    except sender.DoesNotExist:
        pass  # New instance, no action needed
```

**Atomic Transactions for Data Consistency:**
```python
@transaction.atomic
def record_historical_performance():
    """Ensure all vendor performance records are captured consistently"""
    vendors = Vendor.objects.all()
    for vendor in vendors:
        HistoricalPerformance.objects.create(
            vendor=vendor,
            date=timezone.now(),
            on_time_delivery_rate=vendor.on_time_delivery_rate,
            # ... other metrics
        )
```

This data model architecture ensures data integrity, supports complex business workflows, and provides the foundation for scalable vendor management operations.

## 4. Business Workflows and State Diagrams

### 4.1 Purchase Order Lifecycle Workflow

**Complete Purchase Order State Machine:**

```mermaid
stateDiagram-v2
    [*] --> PENDING : Order Created
    
    PENDING --> ISSUED : Issue to Vendor
    PENDING --> CANCELLED : Cancel Order
    
    ISSUED --> ACKNOWLEDGED : Vendor Acknowledges
    ISSUED --> CANCELLED : Cancel Order
    
    ACKNOWLEDGED --> DELIVERED : Mark as Delivered
    ACKNOWLEDGED --> CANCELLED : Cancel Order
    
    DELIVERED --> [*] : Workflow Complete
    CANCELLED --> [*] : Workflow Complete
    
    note right of ISSUED : issue_date auto-set
    note right of ACKNOWLEDGED : acknowledgment_date auto-set
    note right of DELIVERED : actual_delivery_date auto-set
    note right of DELIVERED : quality_rating assignable
```

**Workflow Business Rules:**

1. **Order Creation (→ PENDING)**
   - System generates unique PO number
   - Expected delivery date set to +21 days
   - Order can be created without vendor assignment
   - Total quantity calculated from items JSON

2. **Issue to Vendor (PENDING → ISSUED)**
   - Requires vendor assignment
   - Sets `issue_date` automatically via Django signal
   - Sends notification to vendor (if configured)
   - Only admin/back office users can issue orders

3. **Vendor Acknowledgment (ISSUED → ACKNOWLEDGED)**
   - Must be acknowledged by assigned vendor
   - Sets `acknowledgment_date` automatically
   - Vendor users can only acknowledge their own orders
   - Response time calculated for vendor metrics

4. **Order Delivery (ACKNOWLEDGED → DELIVERED)**
   - Sets `actual_delivery_date` automatically
   - Enables quality rating assignment (1-5 scale)
   - Triggers vendor performance recalculation
   - Updates on-time delivery statistics

5. **Order Cancellation (Any State → CANCELLED)**
   - Can be cancelled from any non-terminal state
   - Affects vendor fulfillment rate calculation
   - Preserves audit trail of cancellation reason

### 4.2 Document Management Workflow

**Document Approval Process:**

```mermaid
stateDiagram-v2
    [*] --> PENDING : Document Uploaded
    
    PENDING --> APPROVED : BO User Approves
    PENDING --> REJECTED : BO User Rejects
    PENDING --> EXPIRED : Auto-Expiry Check
    
    APPROVED --> EXPIRED : Expiry Date Reached
    APPROVED --> RENEWED : New Version Uploaded
    
    REJECTED --> PENDING : Resubmission
    EXPIRED --> PENDING : Document Renewed
    
    RENEWED --> PENDING : Awaiting Approval
    
    note right of APPROVED : approved_date set
    note right of EXPIRED : Automated via Celery
    note right of RENEWED : Previous version archived
```

**Document Workflow Business Rules:**

1. **Document Upload (→ PENDING)**
   - Vendor users upload to their assigned vendor
   - Document type must be from approved list
   - File validation and virus scanning
   - Automatic expiry calculation based on document type

2. **Approval Process (PENDING → APPROVED/REJECTED)**
   - Only admin/back office users can approve
   - Approval sets `approved_date` and `approved_by`
   - Rejection requires reason/comments
   - Email notifications sent to vendor

3. **Expiry Management (APPROVED → EXPIRED)**
   - Automated expiry checking via Celery tasks
   - Warning notifications sent before expiry
   - Grace period handling for renewals
   - Compliance reporting for expired documents

### 4.3 Performance Tracking Workflow

**Automated Performance Calculation:**

```mermaid
sequenceDiagram
    participant PO as Purchase Order
    participant Signal as Django Signal
    participant Vendor as Vendor Model
    participant Celery as Background Task
    participant HP as Historical Performance
    
    PO->>Signal: Status Change to DELIVERED
    Signal->>Vendor: Trigger Performance Recalculation
    Vendor->>Vendor: Update Metrics (On-time, Quality, etc.)
    
    Note over Celery: Every 6 Hours
    Celery->>Vendor: Fetch All Vendors
    Vendor->>HP: Create Historical Snapshot
    HP->>HP: Store Performance Data
```

**Performance Metrics Calculation:**

1. **On-Time Delivery Rate**
   ```python
   delivered_orders = vendor.purchase_orders.filter(status='DELIVERED')
   on_time = delivered_orders.filter(
       actual_delivery_date__lte=F('expected_delivery_date')
   ).count()
   rate = (on_time / delivered_orders.count()) * 100 if delivered_orders.count() > 0 else 0
   ```

2. **Quality Rating Average**
   ```python
   rated_orders = vendor.purchase_orders.filter(
       status='DELIVERED', 
       quality_rating__isnull=False
   )
   avg_rating = rated_orders.aggregate(Avg('quality_rating'))['quality_rating__avg'] or 0
   ```

3. **Average Response Time**
   ```python
   acknowledged_orders = vendor.purchase_orders.filter(
       status__in=['ACKNOWLEDGED', 'DELIVERED'],
       issue_date__isnull=False,
       acknowledgment_date__isnull=False
   )
   response_times = [
       (order.acknowledgment_date - order.issue_date).total_seconds() / 3600
       for order in acknowledged_orders
   ]
   avg_response = sum(response_times) / len(response_times) if response_times else 0
   ```

4. **Fulfillment Rate**
   ```python
   total_orders = vendor.purchase_orders.exclude(status='PENDING').count()
   delivered_orders = vendor.purchase_orders.filter(status='DELIVERED').count()
   rate = (delivered_orders / total_orders) * 100 if total_orders > 0 else 0
   ```

## 5. API Architecture and Patterns

### 5.1 RESTful API Design

**Resource-Based URL Structure:**
```
# Vendor Management
GET    /api/vendors/                 # List all vendors
POST   /api/vendors/                 # Create new vendor
GET    /api/vendors/{vendor_code}/   # Retrieve specific vendor
PUT    /api/vendors/{vendor_code}/   # Update vendor
DELETE /api/vendors/{vendor_code}/   # Delete vendor

# Purchase Order Management  
GET    /api/purchase-orders/         # List all orders
POST   /api/purchase-orders/         # Create new order
GET    /api/purchase-orders/{po_number}/  # Retrieve specific order
PUT    /api/purchase-orders/{po_number}/  # Update order
DELETE /api/purchase-orders/{po_number}/  # Delete order

# Purchase Order Workflow Actions
POST   /api/purchase-orders/{po_number}/issue/       # Issue order
POST   /api/purchase-orders/{po_number}/acknowledge/ # Acknowledge order
POST   /api/purchase-orders/{po_number}/deliver/     # Mark delivered
POST   /api/purchase-orders/{po_number}/cancel/      # Cancel order
POST   /api/purchase-orders/{po_number}/rate-quality/ # Rate quality

# User Management
GET    /api/users/                   # List users (admin only)
GET    /api/users/{email}/           # Retrieve user details

# Authentication
POST   /api/obtain-auth-token/       # Get JWT token
```

### 5.2 Authentication and Authorization Flow

**JWT Token-Based Authentication:**

```mermaid
sequenceDiagram
    participant Client
    participant API as API Gateway
    participant Auth as Auth Service
    participant DB as Database
    
    Client->>API: POST /obtain-auth-token/ {email, password}
    API->>Auth: Validate Credentials
    Auth->>DB: Query User Model
    DB->>Auth: User Data + Role
    Auth->>API: Generate JWT Token
    API->>Client: Return Token
    
    Note over Client: Store Token for Subsequent Requests
    
    Client->>API: API Request + ?token=jwt_token
    API->>Auth: Validate Token
    Auth->>API: User Context + Permissions
    API->>Client: Protected Resource Data
```

**Role-Based Access Control:**

```python
# Permission Matrix
PERMISSIONS = {
    'admin': {
        'vendors': ['create', 'read', 'update', 'delete'],
        'purchase_orders': ['create', 'read', 'update', 'delete', 'issue', 'cancel'],
        'documents': ['read', 'approve', 'reject'],
        'users': ['create', 'read', 'update', 'delete']
    },
    'bo_user': {
        'vendors': ['create', 'read', 'update'],
        'purchase_orders': ['create', 'read', 'update', 'issue'],
        'documents': ['read', 'approve', 'reject'],
        'users': ['read']
    },
    'vendor': {
        'vendors': ['read'],  # Own vendor only
        'purchase_orders': ['read', 'acknowledge', 'deliver'],  # Own orders only
        'documents': ['create', 'read', 'update'],  # Own documents only
        'users': []
    }
}
```

### 5.3 Error Handling and Response Patterns

**Standardized Error Responses:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid data provided",
    "details": {
      "field_name": ["This field is required."],
      "vendor_code": ["Vendor with this code already exists."]
    },
    "timestamp": "2025-10-17T10:30:00Z"
  }
}
```

**HTTP Status Code Usage:**
- `200 OK`: Successful GET, PUT operations
- `201 Created`: Successful POST operations
- `204 No Content`: Successful DELETE operations
- `400 Bad Request`: Validation errors, business rule violations
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource does not exist
- `409 Conflict`: State conflicts (e.g., invalid status transition)
- `500 Internal Server Error`: Unexpected server errors

## 6. Background Tasks and Automation

### 6.1 Celery Configuration

**Task Queue Architecture:**
```python
# Celery Settings (config/settings.py)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Europe/Rome"

# Periodic Task Schedule
CELERY_BEAT_SCHEDULE = {
    'record-historical-performance': {
        'task': 'vendor_management_system.historical_performances.tasks.record_historical_performance',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    'check-document-expiry': {
        'task': 'vendor_management_system.documents.tasks.check_expiring_documents',
        'schedule': crontab(minute=0, hour=9),  # Daily at 9 AM
    },
}
```

### 6.2 Automated Tasks

**1. Historical Performance Recording:**
```python
@shared_task
def record_historical_performance():
    """Capture performance snapshots for all vendors every 6 hours"""
    with transaction.atomic():
        vendors = Vendor.objects.all()
        for vendor in vendors:
            HistoricalPerformance.objects.create(
                vendor=vendor,
                date=timezone.now(),
                on_time_delivery_rate=vendor.on_time_delivery_rate,
                quality_rating_avg=vendor.quality_rating_avg,
                average_response_time=vendor.average_response_time,
                fulfillment_rate=vendor.fulfillment_rate,
            )
```

**2. Document Expiry Monitoring:**
```python
@shared_task  
def check_expiring_documents():
    """Check for documents expiring within warning period"""
    warning_date = timezone.now().date() + timedelta(days=30)
    expiring_docs = VendorDocument.objects.filter(
        status='APPROVED',
        expiry_date__lte=warning_date,
        expiry_date__gte=timezone.now().date()
    )
    
    for doc in expiring_docs:
        send_expiry_warning_email.delay(doc.id)
```

### 6.3 Task Monitoring

**Flower Dashboard:**
- Real-time task monitoring at `http://localhost:5555`
- Task execution statistics and performance metrics
- Worker health monitoring and management
- Failed task investigation and retry management

## 7. Security and Data Protection

### 7.1 Authentication Security

**Password Security:**
- **Argon2 Hashing**: Industry-standard password hashing algorithm
- **Password Validation**: Complexity requirements and common password checking
- **Token Expiration**: JWT tokens with configurable expiration times
- **Rate Limiting**: API endpoint protection against brute force attacks

**Session Management:**
- **Secure Token Storage**: Client-side token management best practices
- **Token Refresh**: Automatic token renewal for extended sessions
- **Session Invalidation**: Immediate token revocation on security events

### 7.2 Authorization Framework

**Role-Based Access Control (RBAC):**
```python
class IsVendorUser(BasePermission):
    """Permission class for vendor users - access only to own data"""
    def has_permission(self, request, view):
        return request.user.role == 'vendor' and request.user.vendor is not None
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'vendor'):
            return obj.vendor == request.user.vendor
        return False

class IsBackOfficeOrAdmin(BasePermission):
    """Permission class for back office and admin users"""
    def has_permission(self, request, view):
        return request.user.role in ['admin', 'bo_user']
```

### 7.3 Data Protection Measures

**Data Validation:**
- **Input Sanitization**: XSS prevention through proper serializer validation
- **SQL Injection Protection**: Django ORM automatic query parameterization
- **File Upload Security**: File type validation and virus scanning
- **Field Validation**: Business rule enforcement at model and API levels

**Audit Trail:**
- **Status Change Tracking**: Automatic timestamp recording for all state transitions
- **User Action Logging**: Complete audit trail of user actions and data modifications
- **Data Retention**: Configurable retention periods for historical data

## 8. Deployment Architecture

### 8.1 Docker-Based Deployment

**Multi-Container Architecture:**
```yaml
# docker-compose.yml structure
services:
  web:          # Django application server
  postgres:     # PostgreSQL database
  redis:        # Redis cache and message broker
  celery:       # Celery worker processes
  celerybeat:   # Celery periodic task scheduler
  flower:       # Celery monitoring dashboard
  nginx:        # Reverse proxy and static file serving
```

**Container Responsibilities:**
- **Web Container**: Django application with gunicorn WSGI server
- **Database Container**: PostgreSQL with persistent volume storage
- **Cache Container**: Redis for session storage and Celery message brokering
- **Worker Container**: Celery workers for background task processing
- **Scheduler Container**: Celery Beat for periodic task automation
- **Monitor Container**: Flower dashboard for task monitoring

### 8.2 Environment Configuration

**Environment Variables:**
```bash
# Core Django Settings
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost

# Database Configuration
DATABASE_URL=postgres://user:pass@postgres:5432/vendordb
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=vendordb
POSTGRES_USER=vendor_user
POSTGRES_PASSWORD=secure_password

# Cache and Message Broker
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# Celery Monitoring
CELERY_FLOWER_USER=admin
CELERY_FLOWER_PASSWORD=secure_password
```

### 8.3 Scalability Considerations

**Horizontal Scaling:**
- **Load Balancing**: Multiple Django application instances behind nginx
- **Database Scaling**: Read replicas for performance analytics queries
- **Cache Distribution**: Redis clustering for high-availability caching
- **Worker Scaling**: Dynamic Celery worker scaling based on queue depth

**Performance Optimization:**
- **Database Indexing**: Optimized indices for common query patterns
- **Query Optimization**: Select_related and prefetch_related for N+1 prevention
- **Caching Strategy**: Redis caching for frequently accessed vendor data
- **Static File Optimization**: CDN integration for static asset delivery

**Monitoring and Logging:**
- **Application Monitoring**: Health checks and performance metrics
- **Error Tracking**: Centralized error logging and alerting
- **Performance Monitoring**: Database query performance analysis
- **Security Monitoring**: Authentication failure detection and alerting

This comprehensive architecture documentation provides a complete blueprint for understanding, maintaining, and extending the Vendor Management System.