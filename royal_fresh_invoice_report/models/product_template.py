# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rfaf_use_crates = fields.Boolean(
        string='Use Crates',
        default=False,
        help='Enable this for products sold in crates.',
    )
    rfaf_units_per_crate = fields.Float(
        string='Units per Crate',
        default=12.0,
        digits='Product Unit of Measure',
        help='Number of units (based on product UoM) in one crate.',
    )
