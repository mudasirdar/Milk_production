# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MilkStandardizationLine(models.Model):
    """
    Represents a portion of raw milk allocated to a specific output category.
    Each line has its own SNF target and calculates water/SMP independently.
    """
    _name = 'milk.standardization.line'
    _description = 'Milk Standardization Line'
    _order = 'sequence, id'

    # Parent Reference
    standardization_id = fields.Many2one(
        'milk.standardization',
        string='Standardization',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    # Category Configuration
    output_category_id = fields.Many2one(
        'milk.output.category',
        string='Output Category',
        required=True,
        help='The milk output category with specific SNF/Fat targets'
    )

    # Allocation
    allocated_qty = fields.Float(
        string='Allocated Qty (L)',
        digits=(12, 2),
        required=True,
        help='Quantity of raw milk allocated to this output category'
    )
    allocation_percentage = fields.Float(
        string='Allocation %',
        digits=(5, 2),
        compute='_compute_allocation_percentage',
        store=True,
        help='Percentage of total raw milk allocated to this category'
    )

    # Input Values (inherited from parent or entered)
    input_fat = fields.Float(
        string='Input Fat %',
        digits=(5, 2),
        related='standardization_id.aggregate_fat',
        store=True,
        readonly=True,
        help='Fat percentage of raw milk (from parent standardization)'
    )
    input_snf = fields.Float(
        string='Input SNF %',
        digits=(5, 2),
        related='standardization_id.aggregate_snf',
        store=True,
        readonly=True,
        help='SNF percentage of raw milk (from parent standardization)'
    )

    # Target Values (from category or custom - editable)
    target_fat = fields.Float(
        string='Target Fat %',
        digits=(5, 2),
        default=3.0,
        help='Target fat percentage for this line'
    )
    target_snf = fields.Float(
        string='Target SNF %',
        digits=(5, 2),
        default=9.5,
        help='Target SNF percentage for this line'
    )
    smp_snf_percent = fields.Float(
        string='SMP SNF %',
        digits=(5, 2),
        default=96.0,
        help='SNF percentage in SMP'
    )

    # Output Product
    output_product_id = fields.Many2one(
        'product.product',
        string='Output Product',
        help='The output product for this category'
    )

    # ============ STEP 1: Water Calculation (Fat Standardization) ============
    water_manual_override = fields.Boolean(
        string='Water Manually Set',
        default=False,
        help='Indicates if water was manually entered instead of auto-calculated'
    )
    water_to_add = fields.Float(
        string='Water to Add (L)',
        digits=(12, 2),
        compute='_compute_water',
        inverse='_inverse_water_to_add',
        store=True,
        readonly=False,
        help='Calculated water quantity for fat standardization (editable for manual override)'
    )
    milk_after_water = fields.Float(
        string='Milk After Water (L)',
        digits=(12, 2),
        compute='_compute_water',
        store=True,
        help='Total volume after water addition'
    )
    water_consumed = fields.Float(
        string='Water Consumed (L)',
        digits=(12, 2),
        help='Actual water consumed (editable, defaults to calculated)'
    )

    # Estimated values after water (calculated from dilution)
    snf_after_water_estimated = fields.Float(
        string='Est. SNF After Water %',
        digits=(5, 2),
        compute='_compute_estimated_snf',
        store=True,
        help='Estimated SNF after water addition (based on dilution calculation)'
    )

    # After Water Values (measured)
    fat_after_water = fields.Float(
        string='Fat % After Water',
        digits=(5, 2),
        help='Measured fat percentage after water addition'
    )
    snf_after_water = fields.Float(
        string='SNF % After Water',
        digits=(5, 2),
        help='Measured SNF percentage after water addition'
    )

    # Progress indicators
    snf_deficit = fields.Float(
        string='SNF Deficit %',
        compute='_compute_snf_progress',
        digits=(5, 2),
        help='SNF deficit from target'
    )
    snf_status = fields.Selection([
        ('pending', 'Pending'),
        ('deficit', 'Below Target'),
        ('ok', 'Meets Target'),
    ], compute='_compute_snf_progress', string='SNF Status')

    # ============ STEP 2: SMP Calculation (SNF Standardization) ============
    smp_to_add = fields.Float(
        string='SMP to Add (Kg)',
        digits=(12, 3),
        compute='_compute_smp',
        store=True,
        help='Calculated SMP quantity for SNF standardization'
    )
    smp_consumed = fields.Float(
        string='SMP Consumed (Kg)',
        digits=(12, 3),
        help='Actual SMP consumed (editable, defaults to calculated)'
    )

    # ============ Final Output ============
    final_qty = fields.Float(
        string='Final Output (L)',
        digits=(12, 2),
        compute='_compute_final_qty',
        store=True,
        help='Final standardized milk quantity'
    )

    # Verification
    final_fat_verified = fields.Float(
        string='Verified Fat %',
        digits=(5, 2),
        help='Final verified fat percentage'
    )
    final_snf_verified = fields.Float(
        string='Verified SNF %',
        digits=(5, 2),
        help='Final verified SNF percentage'
    )

    # State (linked to parent)
    state = fields.Selection(
        related='standardization_id.state',
        store=True,
        readonly=True
    )

    # Notes
    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(
        related='standardization_id.company_id',
        store=True
    )

    # ============ MRP Integration ============
    use_mrp = fields.Boolean(
        string='Use MRP',
        default=False,
        help='Create Manufacturing Order for this line'
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        domain="[('product_tmpl_id', '=', output_product_id)]",
        help='BOM to use for manufacturing order'
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        readonly=True,
        copy=False,
        help='Linked Manufacturing Order'
    )
    production_state = fields.Selection(
        related='production_id.state',
        string='MO State',
        readonly=True
    )

    # ============ Constraints ============
    @api.constrains('allocated_qty')
    def _check_allocated_qty(self):
        for line in self:
            # Only validate if line has a category and is being used
            if line.output_category_id and line.allocated_qty <= 0:
                raise ValidationError(_('Allocated quantity must be positive for %s!') % line.output_category_id.name)

    # ============ Compute Methods ============
    @api.depends('allocated_qty', 'standardization_id.aggregate_qty')
    def _compute_allocation_percentage(self):
        for line in self:
            if line.standardization_id.aggregate_qty:
                line.allocation_percentage = (line.allocated_qty / line.standardization_id.aggregate_qty) * 100
            else:
                line.allocation_percentage = 0


    @api.depends('input_snf', 'allocated_qty', 'milk_after_water')
    def _compute_estimated_snf(self):
        """
        Estimate SNF after water addition based on dilution.
        Formula: NewSNF% = OriginalSNF% × OriginalQty / TotalQty
        """
        for line in self:
            if line.allocated_qty > 0 and line.milk_after_water > 0:
                line.snf_after_water_estimated = (line.input_snf * line.allocated_qty) / line.milk_after_water
            else:
                line.snf_after_water_estimated = line.input_snf

    @api.depends('snf_after_water', 'target_snf')
    def _compute_snf_progress(self):
        """Compute SNF deficit and status."""
        for line in self:
            if line.snf_after_water > 0:
                line.snf_deficit = line.target_snf - line.snf_after_water
                if line.snf_after_water >= line.target_snf:
                    line.snf_status = 'ok'
                else:
                    line.snf_status = 'deficit'
            else:
                line.snf_deficit = 0
                line.snf_status = 'pending'

    @api.depends('allocated_qty', 'input_fat', 'target_fat', 'water_manual_override')
    def _compute_water(self):
        """
        Calculate water needed for fat standardization.
        Formula: Water = Qty × (Fat% - TargetFat%) / TargetFat%
        Derivation: (Qty + Water) × TargetFat% = Qty × Fat%

        If water_manual_override is True, keep the existing water_to_add value.
        """
        for line in self:
            # If water was manually set, only recalculate milk_after_water
            if line.water_manual_override and line.water_to_add > 0:
                line.milk_after_water = line.allocated_qty + line.water_to_add
                continue

            water = 0.0
            milk_after = line.allocated_qty

            if line.allocated_qty > 0 and line.target_fat > 0:
                if line.input_fat > line.target_fat:
                    # Only add water if input fat is higher than target
                    water = line.allocated_qty * (line.input_fat - line.target_fat) / line.target_fat
                    milk_after = line.allocated_qty + water

            line.water_to_add = water
            line.milk_after_water = milk_after

    def _inverse_water_to_add(self):
        """
        Inverse method for water_to_add - called when water is manually entered.
        Recalculates milk_after_water and sets manual override flag.
        """
        for line in self:
            if line.water_to_add > 0:
                line.water_manual_override = True
                line.milk_after_water = line.allocated_qty + line.water_to_add
            else:
                line.water_manual_override = False

    @api.depends('milk_after_water', 'snf_after_water', 'snf_after_water_estimated', 'target_snf', 'smp_snf_percent', 'water_manual_override')
    def _compute_smp(self):
        """
        Calculate SMP needed for SNF standardization.
        Formula: SMP = TotalMilk × (TargetSNF% - CurrentSNF%) / SMP_SNF%

        If water was manually entered and no measured SNF is available,
        use the estimated SNF (from dilution calculation) to provide an estimate.
        """
        for line in self:
            smp = 0.0

            if line.milk_after_water > 0 and line.smp_snf_percent > 0:
                # Use measured SNF if available, otherwise use estimated SNF
                current_snf = line.snf_after_water if line.snf_after_water > 0 else line.snf_after_water_estimated

                if current_snf > 0 and line.target_snf > current_snf:
                    # SNF deficit - need to add SMP
                    snf_deficit = line.target_snf - current_snf
                    smp = (line.milk_after_water * snf_deficit) / line.smp_snf_percent

            line.smp_to_add = smp

    @api.depends('milk_after_water', 'smp_consumed', 'smp_to_add')
    def _compute_final_qty(self):
        """
        Calculate final output quantity.
        Final = Milk after water + SMP added
        Note: SMP dissolves in milk, adding to volume (approximately 1kg SMP = ~0.5L volume increase)
        """
        for line in self:
            smp_qty = line.smp_consumed if line.smp_consumed > 0 else line.smp_to_add
            # SMP adds approximately 0.5L per kg when dissolved
            line.final_qty = line.milk_after_water + (smp_qty * 0.5)

    # ============ Onchange Methods ============
    @api.onchange('output_category_id')
    def _onchange_output_category(self):
        """Update targets and MRP settings when category changes"""
        if self.output_category_id:
            self.target_fat = self.output_category_id.target_fat
            self.target_snf = self.output_category_id.target_snf
            self.smp_snf_percent = self.output_category_id.smp_snf_percent
            self.output_product_id = self.output_category_id.output_product_id
            # MRP settings
            self.use_mrp = self.output_category_id.use_mrp
            self.bom_id = self.output_category_id.bom_id

    @api.onchange('water_to_add')
    def _onchange_water_to_add(self):
        """
        Handle manual water entry.
        Recalculates milk_after_water, estimated SNF, and default water consumed.
        """
        if self.water_to_add > 0:
            # Mark as manually overridden
            self.water_manual_override = True
            # Recalculate milk after water
            self.milk_after_water = self.allocated_qty + self.water_to_add
            # Default water consumed to the new value
            if not self.water_consumed or self.water_consumed != self.water_to_add:
                self.water_consumed = self.water_to_add
            # Recalculate estimated SNF after water (dilution effect)
            if self.allocated_qty > 0 and self.milk_after_water > 0:
                self.snf_after_water_estimated = (self.input_snf * self.allocated_qty) / self.milk_after_water
        else:
            self.water_manual_override = False
            if not self.water_consumed:
                self.water_consumed = self.water_to_add

    @api.onchange('smp_to_add')
    def _onchange_smp_to_add(self):
        """Default SMP consumed to calculated value"""
        if not self.smp_consumed:
            self.smp_consumed = self.smp_to_add

    @api.onchange('snf_after_water')
    def _onchange_snf_after_water(self):
        """Auto-calculate SMP when SNF after water is entered."""
        if self.snf_after_water > 0 and self.milk_after_water > 0:
            if self.snf_after_water < self.target_snf and self.smp_snf_percent > 0:
                smp = (self.milk_after_water * (self.target_snf - self.snf_after_water)) / self.smp_snf_percent
                self.smp_consumed = smp
            elif self.snf_after_water >= self.target_snf:
                self.smp_consumed = 0

    @api.onchange('allocated_qty')
    def _onchange_allocated_qty(self):
        """Reset water consumed when allocation changes."""
        if self.allocated_qty > 0 and self.water_to_add > 0:
            self.water_consumed = self.water_to_add

    # ============ Business Methods ============
    def action_set_default_water(self):
        """Set water consumed to calculated value"""
        for line in self:
            line.water_consumed = line.water_to_add

    def action_reset_water_calculation(self):
        """Reset water to auto-calculated value (remove manual override)"""
        for line in self:
            line.water_manual_override = False
            # Trigger recomputation by saving
            if line.allocated_qty > 0 and line.target_fat > 0 and line.input_fat > line.target_fat:
                water = line.allocated_qty * (line.input_fat - line.target_fat) / line.target_fat
                line.water_to_add = water
                line.milk_after_water = line.allocated_qty + water
            else:
                line.water_to_add = 0.0
                line.milk_after_water = line.allocated_qty
            line.water_consumed = line.water_to_add

    def action_set_default_smp(self):
        """Set SMP consumed to calculated value"""
        for line in self:
            line.smp_consumed = line.smp_to_add

    def validate_for_water_step(self):
        """Validate line is ready for water confirmation"""
        self.ensure_one()
        if self.allocated_qty <= 0:
            raise ValidationError(_('Allocated quantity must be positive for line: %s') % self.output_category_id.name)
        if self.input_fat < self.target_fat:
            raise ValidationError(
                _('Input Fat (%.2f%%) is less than Target Fat (%.2f%%) for line: %s. Cannot standardize.')
                % (self.input_fat, self.target_fat, self.output_category_id.name)
            )

    def validate_for_snf_step(self):
        """Validate line is ready for SNF confirmation"""
        self.ensure_one()
        if self.snf_after_water <= 0:
            raise ValidationError(
                _('Please enter SNF %% after water addition for line: %s') % self.output_category_id.name
            )

    def validate_for_completion(self):
        """Validate line is ready for completion"""
        self.ensure_one()
        if not self.final_fat_verified:
            raise ValidationError(
                _('Please enter verified Fat %% for line: %s') % self.output_category_id.name
            )
        if not self.final_snf_verified:
            raise ValidationError(
                _('Please enter verified SNF %% for line: %s') % self.output_category_id.name
            )

    # ============ MRP Methods ============
    def action_create_manufacturing_order(self):
        """Create Manufacturing Order for this line."""
        self.ensure_one()
        if not self.use_mrp:
            return False
        if self.production_id:
            raise ValidationError(_('Manufacturing Order already exists for line: %s') % self.output_category_id.name)
        if not self.output_product_id:
            raise ValidationError(_('Please select an output product for line: %s') % self.output_category_id.name)

        # Find or create BOM
        bom = self.bom_id
        if not bom:
            bom = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', self.output_product_id.product_tmpl_id.id),
                ('type', '=', 'normal'),
            ], limit=1)

        # Get products from settings
        ICP = self.env['ir.config_parameter'].sudo()
        raw_milk_id = int(ICP.get_param('milk_standardization.raw_milk_product_id', '0'))
        water_id = int(ICP.get_param('milk_standardization.water_product_id', '0'))
        smp_id = int(ICP.get_param('milk_standardization.smp_product_id', '0'))
        location_id = int(ICP.get_param('milk_standardization.processing_location_id', '0'))

        raw_milk_product = self.env['product.product'].browse(raw_milk_id) if raw_milk_id else self.standardization_id.raw_milk_product_id
        water_product = self.env['product.product'].browse(water_id) if water_id else False
        smp_product = self.env['product.product'].browse(smp_id) if smp_id else False
        stock_location = self.env['stock.location'].browse(location_id) if location_id else self.standardization_id.location_id

        # Create Manufacturing Order
        mo_vals = {
            'product_id': self.output_product_id.id,
            'product_qty': self.final_qty or self.milk_after_water,
            'product_uom_id': self.output_product_id.uom_id.id,
            'bom_id': bom.id if bom else False,
            'location_src_id': stock_location.id if stock_location else False,
            'location_dest_id': stock_location.id if stock_location else False,
            'origin': f'{self.standardization_id.name} - {self.output_category_id.name}',
            'standardization_id': self.standardization_id.id,
        }

        production = self.env['mrp.production'].create(mo_vals)

        # Add raw material moves if no BOM
        if not bom:
            moves_raw = []
            # Raw milk
            if raw_milk_product:
                moves_raw.append((0, 0, {
                    'product_id': raw_milk_product.id,
                    'product_uom_qty': self.allocated_qty,
                    'product_uom': raw_milk_product.uom_id.id,
                    'location_id': stock_location.id if stock_location else False,
                    'location_dest_id': production.production_location_id.id,
                    'raw_material_production_id': production.id,
                }))
            # Water
            if water_product and self.water_consumed > 0:
                moves_raw.append((0, 0, {
                    'product_id': water_product.id,
                    'product_uom_qty': self.water_consumed,
                    'product_uom': water_product.uom_id.id,
                    'location_id': stock_location.id if stock_location else False,
                    'location_dest_id': production.production_location_id.id,
                    'raw_material_production_id': production.id,
                }))
            # SMP
            if smp_product and self.smp_consumed > 0:
                moves_raw.append((0, 0, {
                    'product_id': smp_product.id,
                    'product_uom_qty': self.smp_consumed,
                    'product_uom': smp_product.uom_id.id,
                    'location_id': stock_location.id if stock_location else False,
                    'location_dest_id': production.production_location_id.id,
                    'raw_material_production_id': production.id,
                }))

            if moves_raw:
                production.write({'move_raw_ids': moves_raw})

        self.production_id = production.id
        return production

    def action_confirm_manufacturing_order(self):
        """Confirm the Manufacturing Order."""
        for line in self:
            if line.production_id and line.production_id.state == 'draft':
                line.production_id.action_confirm()

    def action_complete_manufacturing_order(self):
        """Mark Manufacturing Order as done."""
        for line in self:
            if line.production_id and line.production_id.state not in ('done', 'cancel'):
                production = line.production_id

                # Confirm if still in draft
                if production.state == 'draft':
                    production.action_confirm()

                # Assign materials
                if production.state == 'confirmed':
                    production.action_assign()

                # Set quantity producing
                production.qty_producing = line.final_qty

                # Update raw material move lines with actual quantities
                for move in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    # Determine the quantity to consume based on product
                    qty_to_consume = move.product_uom_qty

                    # Create or update move lines
                    if move.move_line_ids:
                        move.move_line_ids.write({'quantity': qty_to_consume})
                    elif qty_to_consume > 0:
                        self.env['stock.move.line'].create({
                            'move_id': move.id,
                            'product_id': move.product_id.id,
                            'product_uom_id': move.product_uom.id,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'quantity': qty_to_consume,
                            'company_id': move.company_id.id,
                            'production_id': production.id,
                        })

                # Update finished product move line
                for move in production.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    if move.product_id == line.output_product_id:
                        move.product_uom_qty = line.final_qty
                        if move.move_line_ids:
                            move.move_line_ids.write({'quantity': line.final_qty})
                        else:
                            self.env['stock.move.line'].create({
                                'move_id': move.id,
                                'product_id': move.product_id.id,
                                'product_uom_id': move.product_uom.id,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                                'quantity': line.final_qty,
                                'company_id': move.company_id.id,
                                'production_id': production.id,
                            })

                try:
                    production.button_mark_done()
                except Exception as e:
                    _logger.warning('Failed to mark MO %s as done: %s', production.name, str(e))

    def action_view_manufacturing_order(self):
        """Open the linked Manufacturing Order."""
        self.ensure_one()
        if not self.production_id:
            raise ValidationError(_('No Manufacturing Order linked to this line.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Manufacturing Order'),
            'res_model': 'mrp.production',
            'res_id': self.production_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
