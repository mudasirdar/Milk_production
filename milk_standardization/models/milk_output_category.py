# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MilkOutputCategory(models.Model):
    """
    Defines different milk output categories with specific SNF/Fat targets.
    Examples: Standard Milk (9.5 SNF), Curd Base (10.5 SNF), Paneer Base (11.0 SNF)
    """
    _name = 'milk.output.category'
    _description = 'Milk Output Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='Name of the milk output category (e.g., Standard Milk, Curd Base)'
    )
    code = fields.Char(
        string='Code',
        help='Short code for the category (e.g., STD, CRD)'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Used to order categories in lists'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Target Parameters
    target_fat = fields.Float(
        string='Target Fat %',
        digits=(5, 2),
        default=3.0,
        required=True,
        help='Target fat percentage for this milk category'
    )
    target_snf = fields.Float(
        string='Target SNF %',
        digits=(5, 2),
        default=9.5,
        required=True,
        help='Target SNF (Solid Not Fat) percentage for this milk category'
    )

    # Product Configuration
    output_product_id = fields.Many2one(
        'product.product',
        string='Output Product',
        required=True,
        help='The standardized milk product for this category'
    )

    # MRP Configuration
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        domain="[('product_tmpl_id', '=', output_product_id)]",
        help='Default BOM to use for manufacturing this product'
    )
    use_mrp = fields.Boolean(
        string='Use MRP by Default',
        default=False,
        help='If enabled, Manufacturing Orders will be created for this category'
    )

    # SMP Configuration (can override global settings)
    smp_snf_percent = fields.Float(
        string='SMP SNF %',
        digits=(5, 2),
        default=96.0,
        help='SNF percentage in SMP (Skimmed Milk Powder). Default is 96%'
    )
    use_custom_smp = fields.Boolean(
        string='Use Custom SMP Product',
        default=False,
        help='If enabled, use a different SMP product for this category'
    )
    smp_product_id = fields.Many2one(
        'product.product',
        string='SMP Product',
        help='Custom SMP product for this category (optional)'
    )

    # Usage Information
    description = fields.Text(
        string='Description',
        help='Description of usage and purpose for this category'
    )
    intended_products = fields.Char(
        string='Intended Products',
        help='Products that will be made from this milk (e.g., Curd, Paneer, Cheese)'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Category code must be unique per company!'),
        ('target_fat_positive', 'CHECK(target_fat > 0)', 'Target Fat must be positive!'),
        ('target_snf_positive', 'CHECK(target_snf > 0)', 'Target SNF must be positive!'),
    ]

    @api.constrains('target_fat', 'target_snf')
    def _check_targets(self):
        for record in self:
            if record.target_fat <= 0 or record.target_fat > 15:
                raise ValidationError(_('Target Fat must be between 0 and 15%'))
            if record.target_snf <= 0 or record.target_snf > 20:
                raise ValidationError(_('Target SNF must be between 0 and 20%'))

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f'[{record.code}] {name}'
            name = f'{name} (Fat: {record.target_fat}%, SNF: {record.target_snf}%)'
            result.append((record.id, name))
        return result
