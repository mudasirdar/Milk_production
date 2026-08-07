# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RfafReturnLeakage(models.Model):
    _name = 'rfaf.return.leakage'
    _description = 'Return & Leakage Tracking'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    invoice_id = fields.Many2one(
        'account.move', string='Invoice', required=True, ondelete='cascade',
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        compute='_compute_sale_order', store=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        related='invoice_id.partner_id', store=True,
    )
    date = fields.Date(
        string='Date', related='invoice_id.invoice_date', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='invoice_id.currency_id',
    )
    line_ids = fields.One2many(
        'rfaf.return.leakage.line', 'return_leakage_id', string='Lines',
    )
    total_return_amount = fields.Monetary(
        string='Total Return Amount', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    total_leakage_amount = fields.Monetary(
        string='Total Leakage Amount', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )
    total_deduction = fields.Monetary(
        string='Total Deduction', compute='_compute_totals', store=True,
        currency_field='currency_id',
    )

    @api.depends('line_ids.sale_order_id')
    def _compute_sale_order(self):
        for rec in self:
            sale_orders = rec.line_ids.mapped('sale_order_id')
            rec.sale_order_id = sale_orders[:1].id if sale_orders else False

    @api.depends('line_ids.return_amount', 'line_ids.leakage_amount', 'line_ids.total_deduction')
    def _compute_totals(self):
        for rec in self:
            rec.total_return_amount = sum(rec.line_ids.mapped('return_amount'))
            rec.total_leakage_amount = sum(rec.line_ids.mapped('leakage_amount'))
            rec.total_deduction = sum(rec.line_ids.mapped('total_deduction'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'rfaf.return.leakage'
                ) or 'New'
        return super().create(vals_list)


class RfafReturnLeakageLine(models.Model):
    _name = 'rfaf.return.leakage.line'
    _description = 'Return & Leakage Line'
    _order = 'id'

    return_leakage_id = fields.Many2one(
        'rfaf.return.leakage', string='Return & Leakage',
        required=True, ondelete='cascade',
    )
    invoice_line_id = fields.Many2one(
        'account.move.line', string='Invoice Line', ondelete='cascade',
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        compute='_compute_sale_order', store=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Product',
        related='invoice_line_id.product_id', store=True,
    )
    dispatched_qty = fields.Float(
        string='Dispatched Qty', digits='Product Unit of Measure',
    )
    return_qty = fields.Float(
        string='Return Qty', digits='Product Unit of Measure',
    )
    leakage_qty = fields.Float(
        string='Leakage Qty', digits='Product Unit of Measure',
    )
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    currency_id = fields.Many2one(
        'res.currency', related='return_leakage_id.currency_id',
    )
    return_amount = fields.Monetary(
        string='Return Amount', compute='_compute_amounts', store=True,
        currency_field='currency_id',
    )
    leakage_amount = fields.Monetary(
        string='Leakage Amount', compute='_compute_amounts', store=True,
        currency_field='currency_id',
    )
    total_deduction = fields.Monetary(
        string='Total Deduction', compute='_compute_amounts', store=True,
        currency_field='currency_id',
    )

    @api.depends('invoice_line_id.sale_line_ids')
    def _compute_sale_order(self):
        for rec in self:
            sale_orders = rec.invoice_line_id.sale_line_ids.mapped('order_id')
            rec.sale_order_id = sale_orders[:1].id if sale_orders else False

    @api.depends('return_qty', 'leakage_qty', 'price_unit')
    def _compute_amounts(self):
        for rec in self:
            rec.return_amount = rec.return_qty * rec.price_unit
            rec.leakage_amount = rec.leakage_qty * rec.price_unit
            rec.total_deduction = rec.return_amount + rec.leakage_amount
