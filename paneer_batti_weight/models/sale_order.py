from odoo import models, fields, api

PANEER_BATTI_INTERNAL_REF = 'paneer_batti'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_paneer_batti = fields.Boolean(
        string='Has Paneer Batti Line',
        compute='_compute_has_paneer_batti',
        store=True,
    )

    @api.depends('order_line.product_id')
    def _compute_has_paneer_batti(self):
        for order in self:
            order.has_paneer_batti = any(
                line.product_id.default_code == PANEER_BATTI_INTERNAL_REF
                for line in order.order_line
                if line.product_id
            )