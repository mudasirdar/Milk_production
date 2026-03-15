# -*- coding: utf-8 -*-
{
    'name': 'Property Management System',
    'version': '19.0.2.0.0',
    'category': 'Real Estate',
    'summary': 'Complete Property Management with Tenant, Tenancy, Rent & Maintenance',
    'description': """
        Property Management System
        ===========================

        A comprehensive property management and real estate listing system that includes:

        **Property Management:**
        * Property listing for sale, rent, and lease
        * Multiple property types and categories
        * Advanced property characteristics (furnishing, facing, etc.)
        * Property valuation tracking with appreciation analysis
        * Parent-child property relationships (buildings & units)
        * Occupancy rate tracking
        * Safety certificates management
        * Nearest places/amenities tracking

        **Tenant Management:**
        * Complete tenant profiles with personal & employment details
        * Identification document management
        * Emergency contact information
        * Tenant rating and status tracking
        * Tenant history and relationship management

        **Tenancy & Contract Management:**
        * Full contract lifecycle (Draft → Active → Expired)
        * Flexible payment terms (Monthly, Quarterly, Semi-Annual, Annual)
        * Security deposit tracking and refund management
        * Auto-renewal options with reminders
        * Contract document storage
        * Notice period and termination management

        **Rent & Invoice Management:**
        * Automated rent invoice generation
        * Multiple payment method support
        * Payment tracking and reconciliation
        * Late fee calculation
        * Overdue payment alerts
        * Payment history

        **Maintenance Management:**
        * 10+ maintenance categories (Electrical, Plumbing, HVAC, etc.)
        * Priority levels and assignment tracking
        * Cost estimation and actual cost tracking
        * Billable to tenant options
        * Before/after image attachments
        * Tenant feedback and ratings

        **Insurance Management:**
        * Multiple policy types (Building, Contents, Liability)
        * Coverage amount and premium tracking
        * Auto-renewal with expiry reminders
        * Insurance company and agent details
        * Policy document management

        **Utility Management:**
        * Track 8+ utility types (Electricity, Water, Gas, Internet, etc.)
        * Meter reading and usage tracking
        * Bill payment management
        * Responsibility assignment (Landlord/Tenant/Shared)
        * Service provider information

        **Website Features:**
        * Public property catalog with advanced filters
        * Property detail pages with galleries
        * Customer inquiry system with CRM integration
        * Similar property recommendations
        * Customer portal for property owners

        **CRM Integration (Optional - requires CRM module):**
        * Automatic lead generation from property inquiries
        * Smart lead assignment to property managers
        * Expected revenue calculation
        * Inquiry tracking and follow-up
        * Manual lead creation option

        **Reporting & Analytics:**
        * Property valuation trends
        * Occupancy rates
        * Rent collection tracking
        * Maintenance cost analysis
        * Insurance coverage overview
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'web',
        'website',
        'portal',
        'mail',
    ],
    'data': [
        # Security
        'security/property_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/property_data.xml',

        # Views - Configuration
        'views/property_type_views.xml',
        'views/property_amenity_views.xml',

        # Views - Core
        'views/property_property_views.xml',
        'views/property_inquiry_views.xml',

        # Views - Tenancy Management
        'views/property_tenant_views.xml',
        'views/property_tenancy_views.xml',
        'views/property_rent_invoice_views.xml',

        # Views - Property Management
        'views/property_management_views.xml',

        # Menus
        'views/property_menus.xml',

        # Website Templates
        'templates/property_templates.xml',
        'templates/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'property_management/static/src/scss/property.scss',
            'property_management/static/src/js/property_filter.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
