from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(
        selection_add=[('milk_standardization', 'Milk Standardization')],
        ondelete={'milk_standardization': 'set default'}
    )

    # Milk standardization specific fields
    is_milk_standardization = fields.Boolean(
        compute='_compute_is_milk_standardization',
        store=True,
    )
    target_fat_percent = fields.Float(
        string='Target Fat %',
        default=3.0,
        help='Target fat percentage for standardization (government standard: 3%)',
    )
    target_snf_percent = fields.Float(
        string='Target SNF %',
        default=9.5,
        help='Target SNF percentage for standardization (government standard: 9.5%)',
    )
    smp_snf_percent = fields.Float(
        string='SMP SNF %',
        default=96.0,
        help='SNF percentage of the Skimmed Milk Powder being used (typically ~96%)',
    )

    # Component product references for dynamic calculations
    water_component_id = fields.Many2one(
        'product.product',
        string='Water Component',
        help='Water product used in this BOM for fat standardization',
    )
    smp_component_id = fields.Many2one(
        'product.product',
        string='SMP Component',
        help='SMP product used in this BOM for SNF standardization',
    )
    raw_milk_component_id = fields.Many2one(
        'product.product',
        string='Raw Milk Component',
        help='Raw milk input product in this BOM',
    )

    @api.depends('type')
    def _compute_is_milk_standardization(self):
        for bom in self:
            bom.is_milk_standardization = bom.type == 'milk_standardization'

    @api.onchange('type')
    def _onchange_type_milk_standardization(self):
        """Set default component products from settings when type is milk_standardization."""
        if self.type == 'milk_standardization':
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            water_id = IrConfigParam.get_param('milk_standardization.water_product_id')
            smp_id = IrConfigParam.get_param('milk_standardization.smp_product_id')
            if water_id:
                self.water_component_id = int(water_id)
            if smp_id:
                self.smp_component_id = int(smp_id)

    def _get_milk_standardization_quantities(self, aggregate_qty, aggregate_fat,
                                              snf_after_water, target_fat=None,
                                              target_snf=None, smp_snf_percent=None):
        """
        Calculate dynamic water and SMP quantities for milk standardization.

        Args:
            aggregate_qty: Total milk quantity in liters
            aggregate_fat: Fat percentage of input milk
            snf_after_water: SNF percentage after water addition (0 if not yet measured)
            target_fat: Target fat % (defaults to BOM setting)
            target_snf: Target SNF % (defaults to BOM setting)
            smp_snf_percent: SNF % of SMP (defaults to BOM setting)

        Returns:
            dict with raw_milk_qty, water_qty, smp_qty, milk_after_water, final_qty
        """
        self.ensure_one()

        target_fat = target_fat or self.target_fat_percent or 3.0
        target_snf = target_snf or self.target_snf_percent or 9.5
        smp_snf_percent = smp_snf_percent or self.smp_snf_percent or 96.0

        result = {
            'raw_milk_qty': aggregate_qty,
            'water_qty': 0.0,
            'smp_qty': 0.0,
            'milk_after_water': aggregate_qty,
            'final_qty': aggregate_qty,
        }

        # Step 1: Calculate water for fat standardization
        # Formula: Water = Qty × (Fat% - TargetFat%) / TargetFat%
        if aggregate_fat > target_fat and aggregate_qty > 0:
            water = aggregate_qty * (aggregate_fat - target_fat) / target_fat
            result['water_qty'] = water
            result['milk_after_water'] = aggregate_qty + water
            result['final_qty'] = result['milk_after_water']

        # Step 2: Calculate SMP for SNF standardization
        # Formula: SMP = TotalMilk × (TargetSNF - CurrentSNF) / SMP_SNF%
        if snf_after_water > 0 and snf_after_water < target_snf and result['milk_after_water'] > 0:
            smp = (
                result['milk_after_water']
                * (target_snf - snf_after_water)
                / smp_snf_percent
            )
            result['smp_qty'] = smp
            # SMP adds approximately 1 litre per kg
            result['final_qty'] = result['milk_after_water'] + smp

        return result
