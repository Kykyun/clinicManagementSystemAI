# Clinic Management System

## Overview

A comprehensive web-based clinic management system built with Django that handles patient registration, medical visits, consultations, invoicing, inventory management, and reporting. The system supports multiple user roles (Admin, Doctor, Nurse, Receptionist, Finance, HQ Staff) with role-based access control. Key features include patient medical records, appointment scheduling, prescription management, financial operations (invoicing, payments, panel claims), stock/inventory tracking, and end-of-day reporting.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Django 5.2.9** with Python as the primary backend framework
- **MVT (Model-View-Template)** architecture pattern
- Modular app-based design with clear separation of concerns

**Design Decision**: Django was chosen for its built-in admin interface, ORM capabilities, robust authentication system, and rapid development features. The framework provides excellent support for role-based access control and form handling, which are critical for a healthcare management system.

### Application Structure
The system is organized into six main Django apps:

1. **accounts** - User authentication, staff management, role-based permissions
2. **patients** - Patient records, visits, consultations, prescriptions, appointments
3. **finance** - Invoicing, payments, suppliers, stock orders, panel claims
4. **management_app** - Dashboard, settings, attendance, queue management, reporting
5. **setup_app** - Master data (medicines, lab tests, allergies, fees, panels)
6. **einvoice** - LHDN MyInvois e-invoicing integration for Malaysia tax compliance

**Design Decision**: Modular app structure allows for better code organization, easier maintenance, and potential for reusability. Each app handles a distinct domain area with minimal coupling.

### Authentication & Authorization
- Custom User model extending Django's AbstractUser
- Role-based access control with six user types: Admin, Doctor, Nurse, Receptionist, Finance, HQ Staff
- Custom decorators for role-based view restrictions (`@role_required`, `@admin_required`, etc.)
- Audit logging for tracking user actions and changes

**Design Decision**: Custom decorators provide reusable, declarative access control that's easier to maintain than inline permission checks. The audit log ensures accountability and compliance for sensitive healthcare data.

### Data Models

**Patient Management**:
- Patient: Core patient demographics and medical information
- Visit: Patient visit records with visit type (Medical/OTC)
- Consultation: Detailed medical consultations with vitals, diagnosis, treatment
- Prescription: Medication prescriptions linked to consultations
- Appointment: Appointment scheduling with status tracking
- LabResult, Immunization: Additional medical records

**Financial Operations**:
- Invoice: Patient billing with line items, taxes, discounts
- InvoiceItem: Individual invoice line items (consultation, medicine, lab tests)
- Payment: Payment tracking with multiple payment methods (cash, card, ewallet)
- Supplier: Vendor management for stock procurement
- StockOrder: Purchase orders with approval workflow
- PanelClaim: Insurance/panel claim management
- EODReport: Daily financial reconciliation

**Setup/Master Data**:
- Medicine: Drug inventory with pricing, stock levels, expiry tracking
- LabTest: Laboratory test catalog with pricing
- Allergy: Allergy master data
- Disposable: Medical supplies/consumables inventory
- Panel: Insurance panel/corporate client configuration
- Fee: Service fee structure

**Design Decision**: Normalized relational model ensures data integrity and reduces redundancy. Many-to-many relationships (e.g., Patient-Allergies) provide flexibility. Audit fields (created_at, updated_at) are standard across models for tracking.

### Frontend Architecture
- Server-side rendering with Django templates
- **Bootstrap 5.3.2** for responsive UI components
- **Bootstrap Icons** for iconography
- **DataTables** for enhanced table functionality
- Minimal JavaScript for interactivity (form handling, calendar events)

**Design Decision**: Server-side rendering simplifies deployment and reduces client-side complexity. Bootstrap provides professional, mobile-responsive UI with minimal custom CSS.

### Form Handling
- Django ModelForms for all CRUD operations
- Bootstrap-styled form widgets with CSS classes
- Form validation at model and view levels

**Design Decision**: ModelForms reduce code duplication and ensure consistency between models and forms. Bootstrap styling maintains UI consistency across the application.

### URL Routing
- Namespaced URL patterns for each app (`app_name = 'accounts'`, etc.)
- RESTful URL conventions where appropriate
- Clear, semantic URL paths

**Design Decision**: Namespaced URLs prevent naming conflicts and make reverse URL lookups more maintainable.

### Business Logic Patterns

**Invoice Processing**:
- Draft → Add Items → Finalize workflow
- Automatic balance calculation and status updates
- Support for partial payments

**Stock Management**:
- Low stock alerts based on minimum threshold
- Purchase order workflow with status tracking
- Automatic stock quantity updates on order delivery

**Attendance & Queue**:
- Staff check-in/check-out tracking
- Queue ticket system for patient flow management
- Real-time queue display

**Design Decision**: Multi-step workflows (like invoice creation) prevent incomplete or invalid data. Status-based state machines ensure data integrity throughout the process lifecycle.

## External Dependencies

### Core Framework
- **Django 5.2.9**: Web framework
- **Python 3.x**: Programming language

### Database
- Currently configured for **PostgreSQL or MySQL** (as indicated in requirements)
- Uses Django ORM for database abstraction
- Migration system for schema management

**Note**: The application uses Django's database-agnostic ORM. While PostgreSQL/MySQL are mentioned in requirements, the actual database configuration will be set through environment variables and Django settings.

### Frontend Libraries
- **Bootstrap 5.3.2**: UI framework (CDN)
- **Bootstrap Icons 1.11.1**: Icon library (CDN)
- **DataTables 1.13.6**: Enhanced table functionality (CDN)
- **ReportLab**: PDF generation for reports (Python package)

### File Storage
- Django's default file storage for user uploads (profile images, clinic logo)
- Upload directories: `profiles/`, `clinic/`
- **MEDIA_ROOT** and **STATIC_ROOT** configuration required

### Environment Configuration
- **SESSION_SECRET**: Required environment variable for Django secret key
- **DEBUG**: Optional debug mode flag
- **ALLOWED_HOSTS**: Optional comma-separated host list (defaults to Replit domains)

### Third-Party Services

**LHDN MyInvois Integration (E-Invoicing)**:
- Full integration with Malaysia's LHDN MyInvois API for e-invoicing compliance
- OAuth2 authentication with token caching
- Submit, validate, cancel, and query e-invoices
- TIN (Tax Identification Number) validation
- Sandbox and Production environment support
- Requires: MYINVOIS_CLIENT_ID, MYINVOIS_CLIENT_SECRET via configuration

Other integrations supported:
- Email services (for notifications, password reset)
- SMS gateways (for appointment reminders)
- Payment gateways (for online payments)
- Cloud storage (for medical document storage)

**Design Decision**: CDN-hosted frontend libraries reduce deployment complexity and improve load times. Environment-based configuration supports different deployment environments without code changes.