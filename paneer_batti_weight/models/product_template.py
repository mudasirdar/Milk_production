from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tare_weight_per_batti = fields.Float(
        string='Tare Weight per Batti (kg)',
        default=0.4,
        digits=(10, 3),
        help=(
            'Weight of one batti (container) in kg. '
            'This is auto-filled on sale order lines when Paneer Batti is selected. '
            'The salesperson can override it per order if a different batti size is used.'
        )
    )
