# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # ── Per-line dairy fields ─────────────────────────────────────────────
    rfaf_crates = fields.Integer(
        string='Crates',
        default=0,
        help='Number of crates dispatched for this product',
    )
    rfaf_return_qty = fields.Float(
        string='Return',
        digits='Product Unit of Measure',
        default=0.0,
        help='Quantity returned by the customer',
    )
    rfaf_leakage_qty = fields.Float(
        string='Leakage',
        digits='Product Unit of Measure',
        default=0.0,
        help='Quantity lost due to leakage / damage',
    )
    rfaf_sold_qty = fields.Float(
        string='Sold',
        digits='Product Unit of Measure',
        compute='_compute_sold_qty',
        store=True,
        help='Actual quantity sold = Dispatched − Return − Leakage',
    )

    @api.depends('quantity', 'rfaf_return_qty', 'rfaf_leakage_qty')
    def _compute_sold_qty(self):
        for line in self:
            line.rfaf_sold_qty = (
                (line.quantity or 0.0)
                - (line.rfaf_return_qty or 0.0)
                - (line.rfaf_leakage_qty or 0.0)
            )

    @api.onchange('rfaf_crates')
    def _onchange_rfaf_crates(self):
        """Compute quantity from crates for products with crates enabled.
        Uses the product's configured units per crate.
        """
        for line in self:
            if line.product_id and line.product_id.rfaf_use_crates and line.rfaf_crates:
                units_per_crate = line.product_id.rfaf_units_per_crate or 12.0
                line.quantity = line.rfaf_crates * units_per_crate
