# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyRentInvoice(models.Model):
    _name = 'property.rent.invoice'
    _description = 'Property Rent Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'invoice_date desc'

    name = fields.Char(string='Invoice Number', required=True, copy=False, readonly=True,
                      default=lambda self: _('New'))

    # Relations
    tenancy_id = fields.Many2one('property.tenancy', string='Tenancy', required=True,
                                 ondelete='restrict', tracking=True)
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  ondelete='restrict', tracking=True)
    tenant_id = fields.Many2one('property.tenant', string='Tenant', required=True,
                               ondelete='restrict', tracking=True)

    # Invoice Details
    invoice_date = fields.Date(string='Invoice Date', required=True, default=fields.Date.today,
                              tracking=True)
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    period_start = fields.Date(string='Period Start')
    period_end = fields.Date(string='Period End')

    # Amounts
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    rent_amount = fields.Monetary(string='Rent Amount', currency_field='currency_id')
    maintenance_fee = fields.Monetary(string='Maintenance Fee', currency_field='currency_id')
    parking_fee = fields.Monetary(string='Parking Fee', currency_field='currency_id')
    utility_charges = fields.Monetary(string='Utility Charges', currency_field='currency_id')
    other_charges = fields.Monetary(string='Other Charges', currency_field='currency_id')
    amount = fields.Monetary(string='Total Amount', compute='_compute_amount', store=True,
                            currency_field='currency_id', tracking=True)

    # Payment Tracking
    amount_paid = fields.Monetary(string='Amount Paid', currency_field='currency_id',
                                  tracking=True)
    amount_due = fields.Monetary(string='Amount Due', compute='_compute_amount_due', store=True,
                                currency_field='currency_id')
    payment_date = fields.Date(string='Payment Date', tracking=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('online', 'Online Payment'),
        ('other', 'Other')
    ], string='Payment Method')
    payment_reference = fields.Char(string='Payment Reference')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)

    # Additional Info
    description = fields.Text(string='Description')
    notes = fields.Html(string='Notes')

    # Late Payment
    late_fee = fields.Monetary(string='Late Fee', currency_field='currency_id')
    days_overdue = fields.Integer(string='Days Overdue', compute='_compute_days_overdue')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('property.rent.invoice') or _('New')

        # Auto-populate amounts from tenancy if not provided
        if 'tenancy_id' in vals and vals.get('tenancy_id'):
            tenancy = self.env['property.tenancy'].browse(vals['tenancy_id'])
            if 'rent_amount' not in vals:
                vals['rent_amount'] = tenancy.rent_amount
            if 'maintenance_fee' not in vals:
                vals['maintenance_fee'] = tenancy.maintenance_fee
            if 'parking_fee' not in vals:
                vals['parking_fee'] = tenancy.parking_fee

        return super(PropertyRentInvoice, self).create(vals)

    @api.depends('rent_amount', 'maintenance_fee', 'parking_fee', 'utility_charges',
                 'other_charges', 'late_fee')
    def _compute_amount(self):
        for invoice in self:
            invoice.amount = (invoice.rent_amount + invoice.maintenance_fee +
                            invoice.parking_fee + invoice.utility_charges +
                            invoice.other_charges + invoice.late_fee)

    @api.depends('amount', 'amount_paid')
    def _compute_amount_due(self):
        for invoice in self:
            invoice.amount_due = invoice.amount - invoice.amount_paid

    @api.depends('amount', 'amount_paid', 'due_date')
    def _compute_state(self):
        today = fields.Date.today()
        for invoice in self:
            if invoice.state == 'cancelled':
                continue
            elif invoice.amount_due <= 0:
                invoice.state = 'paid'
            elif invoice.amount_paid > 0:
                invoice.state = 'partial'
            elif invoice.due_date and invoice.due_date < today:
                invoice.state = 'overdue'
            elif invoice.state in ['sent', 'draft']:
                invoice.state = invoice.state
            else:
                invoice.state = 'draft'

    @api.depends('due_date')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for invoice in self:
            if invoice.due_date and invoice.due_date < today and invoice.state != 'paid':
                delta = today - invoice.due_date
                invoice.days_overdue = delta.days
            else:
                invoice.days_overdue = 0

    def action_send_invoice(self):
        self.write({'state': 'sent'})

    def action_register_payment(self):
        self.ensure_one()
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.rent.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_id': self.id,
                'default_amount': self.amount_due,
                'default_payment_date': fields.Date.today()
            }
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def cron_send_payment_reminders(self):
        """Scheduled action to send payment reminders for upcoming due dates"""
        from datetime import timedelta
        today = fields.Date.today()
        reminder_date = today + timedelta(days=3)

        invoices = self.search([
            ('state', 'in', ['draft', 'sent']),
            ('due_date', '=', reminder_date)
        ])

        for invoice in invoices:
            # Create activity for tenant
            invoice.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Rent Payment Due: {invoice.name}',
                note=f'Your rent payment of {invoice.amount} is due on {invoice.due_date}.',
                user_id=invoice.tenancy_id.property_id.user_id.id or self.env.user.id,
            )

    def cron_calculate_late_fees(self):
        """Scheduled action to calculate late fees for overdue invoices"""
        today = fields.Date.today()
        overdue = self.search([
            ('state', '=', 'overdue'),
            ('late_fee', '=', 0)
        ])

        for invoice in overdue:
            if invoice.days_overdue > 0:
                # Calculate 5% late fee after 5 days overdue
                if invoice.days_overdue >= 5:
                    late_fee = invoice.amount * 0.05
                    invoice.write({'late_fee': late_fee})
