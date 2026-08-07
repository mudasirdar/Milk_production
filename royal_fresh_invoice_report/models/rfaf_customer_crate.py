# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RfafCustomerCrate(models.Model):
    _name = 'rfaf.customer.crate'
    _description = 'Customer Crate Tracking'
    _order = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade',
    )
    line_ids = fields.One2many(
        'rfaf.customer.crate.line', 'customer_crate_id', string='Crate Lines',
    )
    total_issued = fields.Integer(
        string='Total Issued', compute='_compute_totals', store=True,
    )
    total_returned = fields.Integer(
        string='Total Returned', compute='_compute_totals', store=True,
    )
    total_balance = fields.Integer(
        string='Balance', compute='_compute_totals', store=True,
    )

    return_history_count = fields.Integer(
        string='Return History', compute='_compute_return_history_count',
    )

    _sql_constraints = [
        ('partner_uniq', 'unique(partner_id)', 'A crate tracking record already exists for this customer.'),
    ]

    def _compute_return_history_count(self):
        ReturnLine = self.env['rfaf.invoice.crate.return']
        for rec in self:
            rec.return_history_count = ReturnLine.search_count([
                ('partner_id', '=', rec.partner_id.id),
                ('crates_returned', '>', 0),
            ])

    def action_view_return_history(self):
        self.ensure_one()
        return {
            'name': 'Crate Return History',
            'type': 'ir.actions.act_window',
            'res_model': 'rfaf.invoice.crate.return',
            'view_mode': 'list',
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                ('crates_returned', '>', 0),
            ],
            'context': {'create': False},
        }

    @api.depends('line_ids.crates_issued', 'line_ids.crates_returned')
    def _compute_totals(self):
        for rec in self:
            rec.total_issued = sum(rec.line_ids.mapped('crates_issued'))
            rec.total_returned = sum(rec.line_ids.mapped('crates_returned'))
            rec.total_balance = rec.total_issued - rec.total_returned


class RfafCustomerCrateLine(models.Model):
    _name = 'rfaf.customer.crate.line'
    _description = 'Customer Crate Line'
    _order = 'date desc, id desc'

    customer_crate_id = fields.Many2one(
        'rfaf.customer.crate', string='Customer Crate',
        required=True, ondelete='cascade',
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        related='customer_crate_id.partner_id', store=True,
    )
    line_type = fields.Selection([
        ('so', 'Sale Order'),
        ('previous', 'Previous Balance'),
    ], string='Type', default='so')
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order',
    )
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='SO Line', ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product', string='Product',
        related='sale_order_line_id.product_id', store=True,
    )
    crate_size = fields.Float(
        string='Units per Crate',
        digits='Product Unit of Measure',
        help='Crate size (units per crate) as defined on the product.',
    )
    date = fields.Date(string='Date')
    crates_issued = fields.Integer(string='Issued')
    crates_returned = fields.Integer(string='Returned')
    balance = fields.Integer(
        string='Balance', compute='_compute_balance', store=True,
    )

    @api.depends('crates_issued', 'crates_returned')
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.crates_issued - rec.crates_returned
