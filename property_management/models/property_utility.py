# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyUtility(models.Model):
    _name = 'property.utility'
    _description = 'Property Utility Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'bill_date desc'

    name = fields.Char(string='Bill Reference', required=True, copy=False, readonly=True,
                      default=lambda self: _('New'))

    # Relations
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  ondelete='restrict', tracking=True)
    tenancy_id = fields.Many2one('property.tenancy', string='Tenancy', ondelete='set null')
    tenant_id = fields.Many2one('property.tenant', string='Tenant',
                               related='tenancy_id.tenant_id', store=True)

    # Utility Details
    utility_type = fields.Selection([
        ('electricity', 'Electricity'),
        ('water', 'Water'),
        ('gas', 'Gas'),
        ('internet', 'Internet'),
        ('cable_tv', 'Cable TV'),
        ('sewage', 'Sewage'),
        ('trash', 'Trash Collection'),
        ('other', 'Other')
    ], string='Utility Type', required=True, tracking=True)

    # Provider
    provider_name = fields.Many2one('res.partner', string='Service Provider')
    account_number = fields.Char(string='Account Number')

    # Billing Period
    bill_date = fields.Date(string='Bill Date', default=fields.Date.today, required=True)
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    period_start = fields.Date(string='Period Start')
    period_end = fields.Date(string='Period End')

    # Usage
    previous_reading = fields.Float(string='Previous Reading')
    current_reading = fields.Float(string='Current Reading')
    usage = fields.Float(string='Usage', compute='_compute_usage', store=True)
    unit_of_measure = fields.Char(string='Unit', default='kWh')

    # Financial
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Bill Amount', required=True,
                            currency_field='currency_id', tracking=True)
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id')
    amount_due = fields.Monetary(string='Amount Due', compute='_compute_amount_due',
                                 store=True, currency_field='currency_id')

    # Payment
    payment_date = fields.Date(string='Payment Date', tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('online', 'Online Payment'),
        ('auto_debit', 'Auto Debit'),
        ('other', 'Other')
    ], string='Payment Method')
    payment_reference = fields.Char(string='Payment Reference')

    # Responsibility
    paid_by = fields.Selection([
        ('landlord', 'Landlord'),
        ('tenant', 'Tenant'),
        ('shared', 'Shared')
    ], string='Paid By', required=True, default='landlord')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)

    # Documents
    bill_document = fields.Binary(string='Bill Document', attachment=True)
    bill_filename = fields.Char(string='Bill Filename')

    # Notes
    notes = fields.Text(string='Notes')

    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('property.utility') or _('New')
        return super(PropertyUtility, self).create(vals)

    @api.depends('previous_reading', 'current_reading')
    def _compute_usage(self):
        for utility in self:
            if utility.current_reading and utility.previous_reading:
                utility.usage = utility.current_reading - utility.previous_reading
            else:
                utility.usage = 0

    @api.depends('amount', 'amount_paid')
    def _compute_amount_due(self):
        for utility in self:
            utility.amount_due = utility.amount - utility.amount_paid

    @api.depends('amount_due', 'due_date', 'payment_date')
    def _compute_state(self):
        today = fields.Date.today()
        for utility in self:
            if utility.state == 'cancelled':
                continue
            elif utility.amount_due <= 0:
                utility.state = 'paid'
            elif utility.due_date and utility.due_date < today:
                utility.state = 'overdue'
            elif utility.state in ['pending', 'draft']:
                utility.state = utility.state
            else:
                utility.state = 'draft'

    def action_confirm(self):
        self.write({'state': 'pending'})

    def action_register_payment(self):
        self.ensure_one()
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.utility.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_utility_id': self.id,
                'default_amount': self.amount_due,
                'default_payment_date': fields.Date.today()
            }
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})
