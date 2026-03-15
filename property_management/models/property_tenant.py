# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyTenant(models.Model):
    _name = 'property.tenant'
    _description = 'Property Tenant'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Tenant Name', required=True, tracking=True)
    reference = fields.Char(string='Tenant ID', required=True, copy=False, readonly=True,
                           default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Contact', ondelete='restrict',
                                 help="Link to existing contact or create new")

    # Personal Information
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)

    # Identification
    identification_type = fields.Selection([
        ('national_id', 'National ID'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('other', 'Other')
    ], string='ID Type')
    identification_number = fields.Char(string='ID Number')
    identification_document = fields.Binary(string='ID Document', attachment=True)
    identification_filename = fields.Char(string='ID Filename')

    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='Zip')
    country_id = fields.Many2one('res.country', string='Country')

    # Emergency Contact
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Relation')

    # Employment Information
    employer_name = fields.Char(string='Employer Name')
    employer_phone = fields.Char(string='Employer Phone')
    occupation = fields.Char(string='Occupation')
    monthly_income = fields.Monetary(string='Monthly Income', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Tenant Status
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection([
        ('prospect', 'Prospect'),
        ('current', 'Current Tenant'),
        ('past', 'Past Tenant'),
        ('blacklisted', 'Blacklisted')
    ], string='Status', default='prospect', tracking=True)

    # Additional Information
    notes = fields.Html(string='Notes')
    image = fields.Image(string='Photo', max_width=128, max_height=128)

    # Relations
    tenancy_ids = fields.One2many('property.tenancy', 'tenant_id', string='Tenancies')
    tenancy_count = fields.Integer(string='Tenancy Count', compute='_compute_tenancy_count')
    current_tenancy_id = fields.Many2one('property.tenancy', string='Current Tenancy',
                                         compute='_compute_current_tenancy', store=True)
    current_property_id = fields.Many2one('property.property', string='Current Property',
                                          related='current_tenancy_id.property_id', store=True)

    # Ratings & Reviews
    rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Good'),
        ('4', 'Very Good'),
        ('5', 'Excellent')
    ], string='Tenant Rating')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('property.tenant') or _('New')
        return super(PropertyTenant, self).create(vals_list)

    @api.depends('tenancy_ids', 'tenancy_ids.state')
    def _compute_tenancy_count(self):
        for tenant in self:
            tenant.tenancy_count = len(tenant.tenancy_ids)

    @api.depends('tenancy_ids', 'tenancy_ids.state')
    def _compute_current_tenancy(self):
        for tenant in self:
            current = tenant.tenancy_ids.filtered(lambda t: t.state == 'active')
            tenant.current_tenancy_id = current[0] if current else False

    def action_view_tenancies(self):
        self.ensure_one()
        return {
            'name': _('Tenancies'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.tenancy',
            'view_mode': 'list,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id}
        }

    def action_set_current(self):
        self.write({'state': 'current'})

    def action_set_past(self):
        self.write({'state': 'past'})

    def action_blacklist(self):
        self.write({'state': 'blacklisted'})

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.name = self.partner_id.name
            self.email = self.partner_id.email
            self.phone = self.partner_id.phone
            self.mobile = self.partner_id.mobile
            self.street = self.partner_id.street
            self.street2 = self.partner_id.street2
            self.city = self.partner_id.city
            self.state_id = self.partner_id.state_id
            self.zip = self.partner_id.zip
            self.country_id = self.partner_id.country_id
