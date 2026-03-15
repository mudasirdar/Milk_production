# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyMaintenance(models.Model):
    _name = 'property.maintenance'
    _description = 'Property Maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True, tracking=True)
    reference = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                           default=lambda self: _('New'))

    # Relations
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  ondelete='restrict', tracking=True)
    tenancy_id = fields.Many2one('property.tenancy', string='Tenancy', ondelete='set null')
    tenant_id = fields.Many2one('property.tenant', string='Reported By Tenant')

    # Request Details
    category = fields.Selection([
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('hvac', 'HVAC'),
        ('appliance', 'Appliance'),
        ('structural', 'Structural'),
        ('painting', 'Painting'),
        ('cleaning', 'Cleaning'),
        ('pest_control', 'Pest Control'),
        ('landscaping', 'Landscaping'),
        ('other', 'Other')
    ], string='Category', required=True, tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Priority', default='medium', required=True, tracking=True)

    description = fields.Html(string='Description', required=True)

    # Scheduling
    request_date = fields.Date(string='Request Date', default=fields.Date.today, required=True)
    scheduled_date = fields.Date(string='Scheduled Date', tracking=True)
    completion_date = fields.Date(string='Completion Date', tracking=True)

    # Assignment
    assigned_to = fields.Many2one('res.partner', string='Assigned To', tracking=True,
                                 help="Service provider or maintenance person")
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)

    # Cost
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id', tracking=True)
    billable_to_tenant = fields.Boolean(string='Billable to Tenant')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Documents
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    before_images = fields.Many2many('ir.attachment', 'maintenance_before_images_rel',
                                    string='Before Images')
    after_images = fields.Many2many('ir.attachment', 'maintenance_after_images_rel',
                                   string='After Images')

    # Notes
    resolution_notes = fields.Html(string='Resolution Notes')
    internal_notes = fields.Text(string='Internal Notes')

    # Rating
    tenant_rating = fields.Selection([
        ('1', 'Very Poor'),
        ('2', 'Poor'),
        ('3', 'Average'),
        ('4', 'Good'),
        ('5', 'Excellent')
    ], string='Tenant Rating')
    tenant_feedback = fields.Text(string='Tenant Feedback')

    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('property.maintenance') or _('New')
        return super(PropertyMaintenance, self).create(vals)

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({
            'state': 'completed',
            'completion_date': fields.Date.today()
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})
