# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class PropertyTenancy(models.Model):
    _name = 'property.tenancy'
    _description = 'Property Tenancy/Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(string='Contract Name', required=True, tracking=True)
    reference = fields.Char(string='Contract Reference', required=True, copy=False, readonly=True,
                           default=lambda self: _('New'))

    # Parties
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  tracking=True, ondelete='restrict')
    tenant_id = fields.Many2one('property.tenant', string='Tenant', required=True,
                               tracking=True, ondelete='restrict')
    landlord_id = fields.Many2one('res.partner', string='Landlord',
                                  related='property_id.owner_id', store=True, readonly=True)

    # Contract Period
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', tracking=True)
    duration_months = fields.Integer(string='Duration (Months)', compute='_compute_duration', store=True)
    is_renewable = fields.Boolean(string='Renewable', default=True)
    auto_renew = fields.Boolean(string='Auto Renew')
    renewal_period_months = fields.Integer(string='Renewal Period (Months)', default=12)

    # Rent Details
    rent_amount = fields.Monetary(string='Monthly Rent', required=True, tracking=True,
                                  currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    rent_payment_day = fields.Integer(string='Payment Day of Month', default=1,
                                     help="Day of the month when rent is due (1-31)")
    rent_payment_term = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual')
    ], string='Payment Term', default='monthly', required=True)

    # Deposit
    security_deposit = fields.Monetary(string='Security Deposit', currency_field='currency_id',
                                       tracking=True)
    deposit_paid = fields.Boolean(string='Deposit Paid', tracking=True)
    deposit_paid_date = fields.Date(string='Deposit Paid Date')
    deposit_refunded = fields.Boolean(string='Deposit Refunded', readonly=True)
    deposit_refund_date = fields.Date(string='Deposit Refund Date', readonly=True)
    deposit_refund_amount = fields.Monetary(string='Deposit Refund Amount',
                                           currency_field='currency_id', readonly=True)

    # Additional Costs
    maintenance_fee = fields.Monetary(string='Monthly Maintenance Fee',
                                     currency_field='currency_id')
    utility_included = fields.Boolean(string='Utilities Included')
    parking_included = fields.Boolean(string='Parking Included')
    parking_fee = fields.Monetary(string='Parking Fee', currency_field='currency_id')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # Documents
    contract_document = fields.Binary(string='Contract Document', attachment=True)
    contract_filename = fields.Char(string='Contract Filename')

    # Relations
    rent_invoice_ids = fields.One2many('property.rent.invoice', 'tenancy_id',
                                       string='Rent Invoices')
    rent_invoice_count = fields.Integer(string='Invoice Count',
                                        compute='_compute_rent_invoice_count')
    maintenance_ids = fields.One2many('property.maintenance', 'tenancy_id',
                                     string='Maintenance Requests')
    maintenance_count = fields.Integer(string='Maintenance Count',
                                      compute='_compute_maintenance_count')

    # Payment Tracking
    total_rent_due = fields.Monetary(string='Total Rent Due',
                                     compute='_compute_payment_summary',
                                     currency_field='currency_id')
    total_rent_paid = fields.Monetary(string='Total Rent Paid',
                                      compute='_compute_payment_summary',
                                      currency_field='currency_id')
    total_rent_outstanding = fields.Monetary(string='Outstanding Rent',
                                            compute='_compute_payment_summary',
                                            currency_field='currency_id')

    # Additional Terms
    terms_and_conditions = fields.Html(string='Terms and Conditions')
    special_clauses = fields.Text(string='Special Clauses')
    notes = fields.Html(string='Internal Notes')

    # Occupants
    number_of_occupants = fields.Integer(string='Number of Occupants', default=1)
    occupant_names = fields.Text(string='Occupant Names')

    # Notice Period
    notice_period_days = fields.Integer(string='Notice Period (Days)', default=30)
    termination_notice_date = fields.Date(string='Termination Notice Date', tracking=True)
    termination_reason = fields.Text(string='Termination Reason')

    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('property.tenancy') or _('New')
        return super(PropertyTenancy, self).create(vals)

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for tenancy in self:
            if tenancy.date_start and tenancy.date_end:
                delta = relativedelta(tenancy.date_end, tenancy.date_start)
                tenancy.duration_months = delta.years * 12 + delta.months
            else:
                tenancy.duration_months = 0

    @api.depends('rent_invoice_ids', 'rent_invoice_ids.state', 'rent_invoice_ids.amount',
                 'rent_invoice_ids.amount_paid')
    def _compute_payment_summary(self):
        for tenancy in self:
            invoices = tenancy.rent_invoice_ids.filtered(lambda i: i.state != 'cancelled')
            tenancy.total_rent_due = sum(invoices.mapped('amount'))
            tenancy.total_rent_paid = sum(invoices.mapped('amount_paid'))
            tenancy.total_rent_outstanding = tenancy.total_rent_due - tenancy.total_rent_paid

    @api.depends('rent_invoice_ids')
    def _compute_rent_invoice_count(self):
        for tenancy in self:
            tenancy.rent_invoice_count = len(tenancy.rent_invoice_ids)

    @api.depends('maintenance_ids')
    def _compute_maintenance_count(self):
        for tenancy in self:
            tenancy.maintenance_count = len(tenancy.maintenance_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for tenancy in self:
            if tenancy.date_start and tenancy.date_end:
                if tenancy.date_end <= tenancy.date_start:
                    raise ValidationError(_('End date must be after start date.'))

    @api.constrains('rent_payment_day')
    def _check_payment_day(self):
        for tenancy in self:
            if tenancy.rent_payment_day < 1 or tenancy.rent_payment_day > 31:
                raise ValidationError(_('Payment day must be between 1 and 31.'))

    def action_submit_approval(self):
        self.write({'state': 'pending'})

    def action_approve(self):
        self.write({'state': 'active'})
        # Update tenant status
        self.tenant_id.write({'state': 'current'})
        # Update property status
        self.property_id.write({'state': 'rented'})
        # Generate first rent invoice
        self.action_generate_rent_invoices()

    def action_terminate(self):
        self.ensure_one()
        return {
            'name': _('Terminate Tenancy'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.tenancy.termination.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_tenancy_id': self.id}
        }

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_renew(self):
        self.ensure_one()
        return {
            'name': _('Renew Tenancy'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.tenancy.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_tenancy_id': self.id}
        }

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_view_rent_invoices(self):
        self.ensure_one()
        return {
            'name': _('Rent Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.rent.invoice',
            'view_mode': 'list,form',
            'domain': [('tenancy_id', '=', self.id)],
            'context': {'default_tenancy_id': self.id}
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            'name': _('Maintenance Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.maintenance',
            'view_mode': 'list,form',
            'domain': [('tenancy_id', '=', self.id)],
            'context': {'default_tenancy_id': self.id, 'default_property_id': self.property_id.id}
        }

    def action_generate_rent_invoices(self):
        """Generate rent invoices for the tenancy period"""
        for tenancy in self:
            if tenancy.state != 'active':
                continue

            # Determine invoice generation period
            start_date = tenancy.date_start
            end_date = tenancy.date_end or fields.Date.today() + relativedelta(years=1)

            current_date = start_date
            invoice_obj = self.env['property.rent.invoice']

            while current_date <= end_date:
                # Check if invoice already exists for this period
                invoice_date = current_date.replace(day=min(tenancy.rent_payment_day, 28))

                existing = invoice_obj.search([
                    ('tenancy_id', '=', tenancy.id),
                    ('invoice_date', '=', invoice_date)
                ], limit=1)

                if not existing:
                    # Create invoice
                    invoice_obj.create({
                        'tenancy_id': tenancy.id,
                        'property_id': tenancy.property_id.id,
                        'tenant_id': tenancy.tenant_id.id,
                        'invoice_date': invoice_date,
                        'due_date': invoice_date,
                        'amount': tenancy.rent_amount + tenancy.maintenance_fee + tenancy.parking_fee,
                        'description': f'Rent for {invoice_date.strftime("%B %Y")}',
                    })

                # Move to next period based on payment term
                if tenancy.rent_payment_term == 'monthly':
                    current_date = current_date + relativedelta(months=1)
                elif tenancy.rent_payment_term == 'quarterly':
                    current_date = current_date + relativedelta(months=3)
                elif tenancy.rent_payment_term == 'semi_annual':
                    current_date = current_date + relativedelta(months=6)
                elif tenancy.rent_payment_term == 'annual':
                    current_date = current_date + relativedelta(years=1)

    def action_refund_deposit(self):
        self.ensure_one()
        return {
            'name': _('Refund Security Deposit'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.deposit.refund.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_tenancy_id': self.id}
        }

    def cron_check_expiring_tenancies(self):
        """Scheduled action to check and notify expiring tenancies"""
        today = fields.Date.today()
        expiring_soon = today + timedelta(days=30)

        tenancies = self.search([
            ('state', '=', 'active'),
            ('date_end', '<=', expiring_soon),
            ('date_end', '>=', today)
        ])

        for tenancy in tenancies:
            # Create activity for property manager
            tenancy.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Tenancy Expiring Soon: {tenancy.name}',
                note=f'The tenancy contract for {tenancy.property_id.name} expires on {tenancy.date_end}.',
                user_id=tenancy.property_id.user_id.id or self.env.user.id,
            )

    def cron_expire_tenancies(self):
        """Scheduled action to expire tenancies that have passed their end date"""
        today = fields.Date.today()
        expired = self.search([
            ('state', '=', 'active'),
            ('date_end', '<', today)
        ])
        expired.write({'state': 'expired'})
        # Update property status
        for tenancy in expired:
            tenancy.property_id.write({'state': 'published'})
            tenancy.tenant_id.write({'state': 'past'})
