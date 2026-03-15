# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyValuation(models.Model):
    _name = 'property.valuation'
    _description = 'Property Valuation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'valuation_date desc'

    name = fields.Char(string='Valuation Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                           default=lambda self: _('New'))

    # Relations
    property_id = fields.Many2one('property.property', string='Property', required=True,
                                  ondelete='restrict', tracking=True)

    # Valuation Details
    valuation_date = fields.Date(string='Valuation Date', default=fields.Date.today,
                                 required=True, tracking=True)
    valuation_type = fields.Selection([
        ('market', 'Market Valuation'),
        ('insurance', 'Insurance Valuation'),
        ('rental', 'Rental Valuation'),
        ('investment', 'Investment Valuation'),
        ('tax', 'Tax Assessment')
    ], string='Valuation Type', required=True, tracking=True)

    # Valuator Information
    valuator = fields.Many2one('res.partner', string='Valuator/Appraiser',
                              help="Professional who conducted the valuation")
    valuator_license = fields.Char(string='Valuator License Number')

    # Amounts
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    valuation_amount = fields.Monetary(string='Valuation Amount', required=True,
                                      currency_field='currency_id', tracking=True)
    previous_valuation = fields.Monetary(string='Previous Valuation',
                                        currency_field='currency_id')
    appreciation = fields.Monetary(string='Appreciation', compute='_compute_appreciation',
                                  currency_field='currency_id', store=True)
    appreciation_percentage = fields.Float(string='Appreciation %',
                                          compute='_compute_appreciation', store=True)

    # Details
    description = fields.Html(string='Description')
    methodology = fields.Text(string='Valuation Methodology')
    notes = fields.Text(string='Notes')

    # Documents
    valuation_report = fields.Binary(string='Valuation Report', attachment=True)
    valuation_report_filename = fields.Char(string='Report Filename')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('verified', 'Verified')
    ], string='Status', default='draft', tracking=True)

    active = fields.Boolean(string='Active', default=True)

    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('property.valuation') or _('New')
        return super(PropertyValuation, self).create(vals)

    @api.depends('valuation_amount', 'previous_valuation')
    def _compute_appreciation(self):
        for valuation in self:
            if valuation.previous_valuation:
                valuation.appreciation = valuation.valuation_amount - valuation.previous_valuation
                valuation.appreciation_percentage = (valuation.appreciation / valuation.previous_valuation) * 100
            else:
                valuation.appreciation = 0
                valuation.appreciation_percentage = 0

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_verify(self):
        self.write({'state': 'verified'})
