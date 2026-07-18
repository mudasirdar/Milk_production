from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    milk_category_id = fields.Many2one(
        'product.category',
        string='Milk Product Category',
        config_parameter='milk_standardization.milk_category_id',
        help='Products in this category will be auto-sent for standardization when received',
    )
    milk_raw_product_id = fields.Many2one(
        'product.product',
        string='Raw Milk Product',
        config_parameter='milk_standardization.raw_milk_product_id',
        help='Default raw milk product (input)',
    )
    milk_standardized_product_id = fields.Many2one(
        'product.product',
        string='Standardized Milk Product',
        config_parameter='milk_standardization.standardized_product_id',
        help='Default standardized milk product (output)',
    )
    milk_water_product_id = fields.Many2one(
        'product.product',
        string='Water Product',
        config_parameter='milk_standardization.water_product_id',
        help='Default product used for water in milk standardization',
    )
    milk_smp_product_id = fields.Many2one(
        'product.product',
        string='SMP Product',
        config_parameter='milk_standardization.smp_product_id',
        help='Default Skimmed Milk Powder product for standardization',
    )
    milk_processing_location_id = fields.Many2one(
        'stock.location',
        string='Processing Location',
        config_parameter='milk_standardization.processing_location_id',
        help='Stock location where milk standardization takes place',
    )

    # MRP Integration Settings
    milk_default_bom_id = fields.Many2one(
        'mrp.bom',
        string='Default Milk Standardization BOM',
        config_parameter='milk_standardization.default_bom_id',
        domain="[('type', '=', 'milk_standardization')]",
        help='Default BOM to use when creating Manufacturing Orders for milk standardization',
    )
    milk_workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Processing Work Center',
        config_parameter='milk_standardization.workcenter_id',
        help='Work center where milk standardization operations are performed',
    )
    milk_auto_create_mo = fields.Boolean(
        string='Auto-create Manufacturing Order',
        config_parameter='milk_standardization.auto_create_mo',
        help='Automatically create Manufacturing Order when starting standardization process',
    )
    milk_use_mrp_default = fields.Boolean(
        string='Use MRP Mode by Default',
        config_parameter='milk_standardization.use_mrp_default',
        help='Enable MRP mode by default for new standardization records',
    )
