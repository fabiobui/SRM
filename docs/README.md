# docs/README.md Structure:

## 1. System Overview
- Business purpose and scope
- High-level architecture diagram
- Technology stack details
- Key features summary

## 2. Application Architecture
- Django apps overview and responsibilities
- Data model relationships
- Authentication & authorization flow
- API design patterns

## 3. Core Applications
### 3.1 Core App
- Custom authentication system
- JWT token management
- Permissions framework

### 3.2 Users App  
- Custom User model with roles
- Role-based access control
- User management workflows

### 3.3 Vendors App
- Vendor lifecycle management
- Performance tracking
- CRUD operations

### 3.4 Purchase Orders App
- Order workflow states
- Status transitions
- Signal handling

### 3.5 Historical Performance App
- Automated performance tracking
- Celery task scheduling
- Metrics calculation

### 3.6 Documents App
- Document type management
- Expiry tracking
- Role-based dashboards

## 4. Data Model Relationships
- Entity Relationship Diagram
- Foreign key relationships
- Business rule constraints

## 5. API Architecture
- REST API design principles
- Authentication flow
- Error handling patterns
- Response formats

## 6. Background Tasks
- Celery configuration
- Periodic tasks (Beat)
- Task monitoring (Flower)

## 7. Security & Permissions
- Authentication methods
- Role-based permissions
- Data access patterns

## 8. Deployment Architecture
- Docker setup
- Environment configuration
- Database setup
- Caching strategy