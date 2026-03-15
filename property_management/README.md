# Property Management System

A comprehensive property management and real estate listing system for Odoo 19.

## Features

### Core Functionality
- **Property Listing Management**: Create, edit, and manage property listings
- **Multiple Transaction Types**: Support for Sale, Rent, and Lease
- **Property Types**: Residential, Commercial, Land, Apartment, Villa, Office, Warehouse
- **Workflow Management**: Draft → Pending → Approved → Published
- **Website Integration**: Public property catalog with advanced filters
- **Customer Portal**: Property owners can manage their listings
- **Inquiry System**: Customers can contact property owners

### Property Information
- Basic Details: Title, Description, Type, Transaction Type
- Location: Full address with city, state, country
- Pricing: Flexible pricing for sale, rent, or lease
- Characteristics:
  - Bedrooms and Bathrooms
  - Building Area and Land Area
  - Parking Spaces
  - Number of Floors and Apartments
  - Year Built
  - Property Condition
- Amenities: 15+ predefined amenities (customizable)
- Media: Multiple images, main image, floor plans

### Website Features
- Public property catalog
- Advanced search and filtering:
  - Property Type
  - Transaction Type
  - Location (City, Country)
  - Price Range
  - Bedrooms/Bathrooms
  - Building Area
  - Amenities
  - Parking Spaces
- Property detail pages with:
  - Image gallery
  - Full property information
  - Contact form for inquiries
  - Similar properties section
- Sorting options (Newest, Price, Name)
- Pagination
- Responsive design

### Customer Portal
- My Properties dashboard
- Add new property listings
- Edit draft properties
- View property inquiries
- Track property status
- View published properties on website

### Administrative Features
- Approval workflow
- Property status management
- Inquiry management
- Configuration:
  - Property Types
  - Amenities
- User roles:
  - Property User: Can manage own properties
  - Property Manager: Can manage all properties and approve listings

## Installation

1. Copy the `property_management` folder to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Property Management System" module
4. Configure:
   - Property Types (pre-loaded with default types)
   - Amenities (pre-loaded with 15+ amenities)
   - User permissions

## Configuration

### Property Types
Go to: Properties → Configuration → Property Types

Default types included:
- Residential
- Commercial
- Land
- Apartment
- Villa
- Office
- Warehouse

### Amenities
Go to: Properties → Configuration → Amenities

Default amenities included:
- Swimming Pool
- Elevator
- 24/7 Security
- Gym
- Garden
- Central Air Conditioning
- CCTV
- Balcony
- Covered Parking
- Playground
- WiFi
- Fully Furnished
- Laundry Room
- Pet Friendly
- Sauna
- Storage Room

### User Permissions
Assign users to appropriate groups:
- **Property Management / User**: Can create and manage own properties
- **Property Management / Manager**: Can manage all properties and approve listings

## Usage

### For Property Owners

1. **Create a Property**:
   - Go to Properties → My Properties → New
   - Or use the Customer Portal: My Account → Properties → Add New Property
   - Fill in property details
   - Upload images
   - Submit for approval

2. **Manage Properties**:
   - View all your properties in My Properties
   - Edit draft properties
   - Submit properties for approval
   - Track property status
   - View and respond to inquiries

3. **Track Inquiries**:
   - Go to Properties → Inquiries
   - Or use Customer Portal: My Account → Property Inquiries
   - View all inquiries for your properties
   - Respond to customer questions

### For Property Managers

1. **Review Properties**:
   - Go to Properties → All Properties
   - Review pending properties
   - Approve or reject listings

2. **Publish Properties**:
   - Approve properties first
   - Click "Publish on Website" to make them public
   - Properties will appear on the website catalog

3. **Manage Inquiries**:
   - Go to Properties → Inquiries
   - Assign inquiries to team members
   - Track inquiry status
   - Respond to customer questions

### For Customers (Website)

1. **Browse Properties**:
   - Visit /properties on your website
   - Use filters to find properties
   - Sort by price, date, or name

2. **View Property Details**:
   - Click on any property card
   - View full details, images, and amenities
   - See similar properties

3. **Contact Property Owner**:
   - Fill in the inquiry form
   - Submit your question or interest
   - Property owner will be notified

## Technical Details

### Models
- `property.property`: Main property model
- `property.type`: Property types
- `property.amenity`: Property amenities
- `property.inquiry`: Customer inquiries
- `property.image`: Property images

### Views
- Form, Tree, Kanban views for backend
- Website templates for property listing and details
- Portal templates for customer management

### Security
- Record rules for data access
- User groups for permissions
- Public access for published properties

### Controllers
- `/properties`: Property listing page
- `/property/<id>`: Property detail page
- `/property/<id>/inquiry`: Submit inquiry
- `/my/properties`: Customer portal properties
- `/my/inquiries`: Customer portal inquiries

## Dependencies
- base
- web
- website
- portal
- mail

## Version
- Version: 19.0.1.0.0
- Odoo Version: 19.0
- License: LGPL-3

## Support
For issues, questions, or contributions, please contact your system administrator.

## Changelog

### Version 19.0.1.0.0
- Initial release
- Property listing management
- Website integration
- Customer portal
- Inquiry system
- Approval workflow
- 7 property types
- 16 amenities
- Advanced filtering
