# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    rfaf_crates = fields.Integer(
        string='Crates',
        default=0,
        help='Number of crates. Quantity is calculated based on product liters per crate.',
    )

    @api.onchange('rfaf_crates')
    def _onchange_rfaf_crates(self):
        """Compute quantity from crates for products with crates enabled.
        Uses the product's configured units per crate.
        """
        for line in self:
            if line.product_id and line.product_id.rfaf_use_crates and line.rfaf_crates:
                units_per_crate = line.product_id.rfaf_units_per_crate or 12.0
                line.product_uom_qty = line.rfaf_crates * units_per_crate

    def _prepare_invoice_line(self, **optional_values):
        """Pass crates value to the invoice line."""
        res = super()._prepare_invoice_line(**optional_values)
        res['rfaf_crates'] = self.rfaf_crates
        return res
