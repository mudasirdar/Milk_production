# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Property(models.Model):
    _name = 'property.property'
    _description = 'Property'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'website.published.mixin']
    _order = 'create_date desc, id desc'

    # Basic Information
    name = fields.Char(string='Property Title', required=True, tracking=True)
    description = fields.Html(string='Description')
    reference = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('published', 'Published'),
        ('sold', 'Sold'),
        ('rented', 'Rented'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Property Type & Transaction
    property_type_id = fields.Many2one(
        'property.type',
        string='Property Type',
        required=True,
        tracking=True
    )
    transaction_type = fields.Selection([
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
        ('lease', 'For Lease'),
    ], string='Transaction Type', required=True, tracking=True)

    # Owner Information
    owner_id = fields.Many2one(
        'res.partner',
        string='Property Owner',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.partner_id
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True
    )

    # Pricing
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    price = fields.Monetary(
        string='Price',
        currency_field='currency_id',
        required=True,
        tracking=True
    )
    monthly_rent = fields.Monetary(
        string='Monthly Rent',
        currency_field='currency_id',
        tracking=True
    )

    # Location
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City', required=True)
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP Code')
    country_id = fields.Many2one('res.country', string='Country', required=True)
    location = fields.Char(string='Location', compute='_compute_location', store=True)
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))

    # Property Characteristics
    parking_spaces = fields.Integer(string='Parking Spaces', default=0)
    number_of_floors = fields.Integer(string='Number of Floors', default=1)
    number_of_apartments = fields.Integer(string='Number of Apartments', default=0)
    bedrooms = fields.Integer(string='Bedrooms', default=0)
    bathrooms = fields.Integer(string='Bathrooms', default=0)
    property_per_rooms = fields.Integer(string='Number of Rooms', default=0)
    building_area = fields.Float(string='Building Area (sqm)', digits=(10, 2))
    land_area = fields.Float(string='Land Area (sqm)', digits=(10, 2))
    year_built = fields.Integer(string='Year Built')
    property_condition = fields.Selection([
        ('new', 'New'),
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('needs_renovation', 'Needs Renovation'),
    ], string='Property Condition', default='good')

    # Additional Property Details
    furnishing = fields.Selection([
        ('unfurnished', 'Unfurnished'),
        ('semi_furnished', 'Semi Furnished'),
        ('full_furnished', 'Full Furnished')
    ], string='Furnishing', default='unfurnished', tracking=True)

    facing = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West'),
        ('north_east', 'North-East'),
        ('north_west', 'North-West'),
        ('south_east', 'South-East'),
        ('south_west', 'South-West')
    ], string='Facing')

    property_category = fields.Many2one('property.category', string='Property Category')
    parent_property_id = fields.Many2one('property.property', string='Parent Property',
                                         help='For sub-properties or units within a larger property')
    child_property_ids = fields.One2many('property.property', 'parent_property_id',
                                         string='Sub Properties')
    child_property_count = fields.Integer(string='Sub Property Count',
                                          compute='_compute_child_property_count')

    # Management
    property_manager_id = fields.Many2one('res.users', string='Property Manager',
                                          tracking=True)
    management_company_id = fields.Many2one('res.partner', string='Property Management Company')

    # Media & Documents
    video_url = fields.Char(string='Video URL', help='YouTube or other video link')

    # Depreciation & Valuation
    gross_value = fields.Monetary(string='Gross Value', currency_field='currency_id',
                                  help='Original purchase or construction value')
    salvage_value = fields.Monetary(string='Salvage Value', currency_field='currency_id',
                                    help='Expected value at end of useful life')
    residual_value = fields.Monetary(string='Residual Value', currency_field='currency_id',
                                     help='Current residual/book value')

    depreciation_method = fields.Selection([
        ('linear', 'Linear'),
        ('degressive', 'Degressive'),
        ('accelerated', 'Accelerated')
    ], string='Computation Method')

    depressive_factor = fields.Float(string='Depressive Factor', digits=(12, 2))
    time_method = fields.Selection([
        ('number', 'Number of Entries'),
        ('end', 'Ending Date'),
        ('percentage', 'Percentage')
    ], string='Time Method')

    number_of_depreciations = fields.Integer(string='Number of Depreciations')
    period_temporis = fields.Integer(string='Periods Temporis')

    # Purchase & Sale Details
    purchase_date = fields.Date(string='Purchase Date')
    purchase_price = fields.Monetary(string='Purchase Price', currency_field='currency_id')
    sale_date = fields.Date(string='Sale Date')
    sale_price = fields.Monetary(string='Sale Price', currency_field='currency_id')

    # Safety & Certificates
    safety_certificate_ids = fields.One2many('property.safety.certificate', 'property_id',
                                            string='Safety Certificates')

    # Nearest Places
    nearest_place_ids = fields.One2many('property.nearest.place', 'property_id',
                                       string='Nearest Places')

    # Occupancy
    occupancy_rate = fields.Float(string='Occupancy Rate (%)', compute='_compute_occupancy_rate')
    total_units = fields.Integer(string='Total Units', default=1,
                                 help='Total rentable units in this property')
    occupied_units = fields.Integer(string='Occupied Units',
                                    compute='_compute_occupied_units')

    # Amenities
    amenity_ids = fields.Many2many(
        'property.amenity',
        'property_amenity_rel',
        'property_id',
        'amenity_id',
        string='Amenities'
    )

    # Media
    image_main = fields.Image(string='Main Image', max_width=1920, max_height=1920)
    image_ids = fields.One2many(
        'property.image',
        'property_id',
        string='Property Images'
    )
    floor_plan = fields.Binary(string='Floor Plan')
    floor_plan_filename = fields.Char(string='Floor Plan Filename')

    # Website
    website_published = fields.Boolean(string='Published on Website', copy=False)
    website_url = fields.Char(
        string='Website URL',
        compute='_compute_website_url',
        help='The full URL to access the property on the website'
    )
    is_featured = fields.Boolean(string='Featured Property', default=False)
    views_count = fields.Integer(string='Views Count', default=0, readonly=True)

    # Inquiries
    inquiry_ids = fields.One2many(
        'property.inquiry',
        'property_id',
        string='Inquiries'
    )
    inquiry_count = fields.Integer(
        string='Inquiry Count',
        compute='_compute_inquiry_count',
        store=False
    )

    # Tenancy Management
    tenancy_ids = fields.One2many(
        'property.tenancy',
        'property_id',
        string='Tenancies'
    )
    tenancy_count = fields.Integer(
        string='Tenancy Count',
        compute='_compute_tenancy_count'
    )
    current_tenancy_id = fields.Many2one(
        'property.tenancy',
        string='Current Tenancy',
        compute='_compute_current_tenancy',
        store=True
    )
    current_tenant_id = fields.Many2one(
        'property.tenant',
        string='Current Tenant',
        related='current_tenancy_id.tenant_id',
        store=True
    )

    # Maintenance
    maintenance_ids = fields.One2many(
        'property.maintenance',
        'property_id',
        string='Maintenance Requests'
    )
    maintenance_count = fields.Integer(
        string='Maintenance Count',
        compute='_compute_maintenance_count'
    )

    # Valuation
    valuation_ids = fields.One2many(
        'property.valuation',
        'property_id',
        string='Valuations'
    )
    valuation_count = fields.Integer(
        string='Valuation Count',
        compute='_compute_valuation_count'
    )
    latest_valuation = fields.Monetary(
        string='Latest Valuation',
        compute='_compute_latest_valuation',
        currency_field='currency_id'
    )

    # Insurance
    insurance_ids = fields.One2many(
        'property.insurance',
        'property_id',
        string='Insurance Policies'
    )
    insurance_count = fields.Integer(
        string='Insurance Count',
        compute='_compute_insurance_count'
    )
    active_insurance_id = fields.Many2one(
        'property.insurance',
        string='Active Insurance',
        compute='_compute_active_insurance'
    )

    # Utilities
    utility_ids = fields.One2many(
        'property.utility',
        'property_id',
        string='Utility Bills'
    )
    utility_count = fields.Integer(
        string='Utility Count',
        compute='_compute_utility_count'
    )

    # Computed Fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    _sql_constraints = [
        ('reference_unique', 'UNIQUE(reference)', 'Property reference must be unique!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('property.property') or _('New')
        return super(Property, self).create(vals_list)

    @api.depends('name', 'reference')
    def _compute_display_name(self):
        for record in self:
            if record.reference and record.reference != _('New'):
                record.display_name = f"[{record.reference}] {record.name}"
            else:
                record.display_name = record.name

    @api.depends('street', 'city', 'state_id', 'country_id')
    def _compute_location(self):
        for record in self:
            location_parts = []
            if record.street:
                location_parts.append(record.street)
            if record.city:
                location_parts.append(record.city)
            if record.state_id:
                location_parts.append(record.state_id.name)
            if record.country_id:
                location_parts.append(record.country_id.name)
            record.location = ', '.join(location_parts)

    def _compute_website_url(self):
        for record in self:
            if record.id:
                record.website_url = f'/property/{record.id}'
            else:
                record.website_url = False

    @api.depends('inquiry_ids')
    def _compute_inquiry_count(self):
        for record in self:
            record.inquiry_count = len(record.inquiry_ids)

    @api.depends('tenancy_ids')
    def _compute_tenancy_count(self):
        for record in self:
            record.tenancy_count = len(record.tenancy_ids)

    @api.depends('tenancy_ids', 'tenancy_ids.state')
    def _compute_current_tenancy(self):
        for record in self:
            active_tenancies = record.tenancy_ids.filtered(lambda t: t.state == 'active')
            record.current_tenancy_id = active_tenancies[0] if active_tenancies else False

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for record in self:
            record.maintenance_count = len(record.maintenance_ids)

    @api.depends('valuation_ids')
    def _compute_valuation_count(self):
        for record in self:
            record.valuation_count = len(record.valuation_ids)

    @api.depends('valuation_ids', 'valuation_ids.valuation_amount')
    def _compute_latest_valuation(self):
        for record in self:
            if record.valuation_ids:
                latest = record.valuation_ids.sorted('valuation_date', reverse=True)[0]
                record.latest_valuation = latest.valuation_amount
            else:
                record.latest_valuation = 0

    @api.depends('insurance_ids')
    def _compute_insurance_count(self):
        for record in self:
            record.insurance_count = len(record.insurance_ids)

    @api.depends('insurance_ids', 'insurance_ids.state')
    def _compute_active_insurance(self):
        for record in self:
            active = record.insurance_ids.filtered(lambda i: i.state == 'active')
            record.active_insurance_id = active[0] if active else False

    @api.depends('utility_ids')
    def _compute_utility_count(self):
        for record in self:
            record.utility_count = len(record.utility_ids)

    @api.depends('child_property_ids')
    def _compute_child_property_count(self):
        for record in self:
            record.child_property_count = len(record.child_property_ids)

    @api.depends('tenancy_ids', 'tenancy_ids.state', 'total_units')
    def _compute_occupied_units(self):
        for record in self:
            active_tenancies = record.tenancy_ids.filtered(lambda t: t.state == 'active')
            record.occupied_units = len(active_tenancies)

    @api.depends('total_units', 'occupied_units')
    def _compute_occupancy_rate(self):
        for record in self:
            if record.total_units > 0:
                record.occupancy_rate = (record.occupied_units / record.total_units) * 100
            else:
                record.occupancy_rate = 0

    @api.constrains('year_built')
    def _check_year_built(self):
        current_year = fields.Date.today().year
        for record in self:
            if record.year_built and (record.year_built < 1800 or record.year_built > current_year + 2):
                raise ValidationError(_('Year built must be between 1800 and %s') % (current_year + 2))

    @api.constrains('price', 'monthly_rent')
    def _check_price(self):
        for record in self:
            if record.price and record.price < 0:
                raise ValidationError(_('Price must be positive'))
            if record.monthly_rent and record.monthly_rent < 0:
                raise ValidationError(_('Monthly rent must be positive'))

    @api.constrains('building_area', 'land_area')
    def _check_area(self):
        for record in self:
            if record.building_area and record.building_area < 0:
                raise ValidationError(_('Building area must be positive'))
            if record.land_area and record.land_area < 0:
                raise ValidationError(_('Land area must be positive'))

    def action_submit_approval(self):
        self.write({'state': 'pending'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_publish(self):
        self.write({
            'state': 'published',
            'website_published': True
        })

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_mark_sold(self):
        self.write({'state': 'sold', 'website_published': False})

    def action_mark_rented(self):
        self.write({'state': 'rented', 'website_published': False})

    def action_view_inquiries(self):
        return {
            'name': _('Inquiries'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.inquiry',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }

    def action_view_tenancies(self):
        return {
            'name': _('Tenancies'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.tenancy',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }

    def action_view_maintenance(self):
        return {
            'name': _('Maintenance Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.maintenance',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }

    def action_view_valuations(self):
        return {
            'name': _('Valuations'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.valuation',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }

    def action_view_insurance(self):
        return {
            'name': _('Insurance Policies'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.insurance',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }

    def action_view_utilities(self):
        return {
            'name': _('Utility Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.utility',
            'view_mode': 'list,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id}
        }

    def action_view_sub_properties(self):
        return {
            'name': _('Sub Properties'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.property',
            'view_mode': 'list,form',
            'domain': [('parent_property_id', '=', self.id)],
            'context': {'default_parent_property_id': self.id}
        }

    def increment_views(self):
        """Increment the views counter for the property"""
        self.sudo().write({'views_count': self.views_count + 1})


class PropertyImage(models.Model):
    _name = 'property.image'
    _description = 'Property Image'
    _order = 'sequence, id'

    name = fields.Char(string='Image Name')
    sequence = fields.Integer(string='Sequence', default=10)
    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        ondelete='cascade'
    )
    image = fields.Image(string='Image', required=True, max_width=1920, max_height=1920)
    image_medium = fields.Image(string='Medium Image', related='image', max_width=512, max_height=512, store=True)
    image_small = fields.Image(string='Small Image', related='image', max_width=256, max_height=256, store=True)
