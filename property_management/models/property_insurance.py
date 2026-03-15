# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PropertyInsurance(models.Model):
    _name = 'property.insurance'
    _description = 'Property Insurance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'

    name = fields.Char(string='Insurance Policy Name', required=True, tracking=True)
    reference = fields.Char(string='Policy Number', required=True, copy=False, readonly=True,
                           default=lambda self: _('New'))

    # Relations
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  ondelete='restrict', tracking=True)

    # Insurance Company
    insurance_company = fields.Many2one('res.partner', string='Insurance Company',
                                       required=True, tracking=True)
    agent_name = fields.Char(string='Agent Name')
    agent_phone = fields.Char(string='Agent Phone')
    agent_email = fields.Char(string='Agent Email')

    # Policy Details
    policy_type = fields.Selection([
        ('building', 'Building Insurance'),
        ('contents', 'Contents Insurance'),
        ('liability', 'Liability Insurance'),
        ('comprehensive', 'Comprehensive')
    ], string='Policy Type', required=True, tracking=True)

    # Coverage Period
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    duration_days = fields.Integer(string='Duration (Days)', compute='_compute_duration')

    # Financial
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    coverage_amount = fields.Monetary(string='Coverage Amount', required=True,
                                     currency_field='currency_id', tracking=True)
    premium_amount = fields.Monetary(string='Premium Amount', required=True,
                                    currency_field='currency_id', tracking=True)
    deductible = fields.Monetary(string='Deductible', currency_field='currency_id')

    payment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual')
    ], string='Payment Frequency', default='annual')

    # Auto Renewal
    auto_renew = fields.Boolean(string='Auto Renew', default=True)
    renewal_reminder_days = fields.Integer(string='Renewal Reminder (Days)', default=30)

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, compute='_compute_state', store=True)

    # Documents
    policy_document = fields.Binary(string='Policy Document', attachment=True)
    policy_filename = fields.Char(string='Policy Filename')

    # Coverage Details
    coverage_details = fields.Html(string='Coverage Details')
    exclusions = fields.Text(string='Exclusions')
    notes = fields.Text(string='Notes')

    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('property.insurance') or _('New')
        return super(PropertyInsurance, self).create(vals)

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for insurance in self:
            if insurance.start_date and insurance.end_date:
                delta = insurance.end_date - insurance.start_date
                insurance.duration_days = delta.days
            else:
                insurance.duration_days = 0

    @api.depends('start_date', 'end_date')
    def _compute_state(self):
        today = fields.Date.today()
        for insurance in self:
            if insurance.state == 'cancelled':
                continue
            elif insurance.start_date and insurance.end_date:
                if insurance.start_date <= today <= insurance.end_date:
                    insurance.state = 'active'
                elif today > insurance.end_date:
                    insurance.state = 'expired'
                else:
                    insurance.state = 'draft'

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for insurance in self:
            if insurance.start_date and insurance.end_date:
                if insurance.end_date <= insurance.start_date:
                    raise ValidationError(_('End date must be after start date.'))

    def action_activate(self):
        self.write({'state': 'active'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_renew(self):
        self.ensure_one()
        return {
            'name': _('Renew Insurance Policy'),
            'type': 'ir.actions.act_window',
            'res_model': 'property.insurance.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_insurance_id': self.id}
        }

    def cron_check_expiring_insurance(self):
        """Scheduled action to check and notify expiring insurance policies"""
        from datetime import timedelta
        today = fields.Date.today()

        for insurance in self.search([('state', '=', 'active')]):
            days_to_expire = (insurance.end_date - today).days
            if 0 < days_to_expire <= insurance.renewal_reminder_days:
                # Create activity for property manager
                insurance.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=f'Insurance Policy Expiring: {insurance.name}',
                    note=f'The insurance policy for {insurance.property_id.name} expires on {insurance.end_date}.',
                    user_id=insurance.property_id.user_id.id or self.env.user.id,
                )
