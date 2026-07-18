from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class MilkStandardization(models.Model):
    _name = 'milk.standardization'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Milk Standardization Record'
    _order = 'date desc, id desc'

    # ── Identity ──────────────────────────────────────────────────────────
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('milk.standardization')
    )
    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        required=True,
    )
    state = fields.Selection([
        ('draft',    'Draft'),
        ('step1',    'Water Added'),
        ('step2',    'SMP Added'),
        ('done',     'Standardized'),
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')

    # ── Stock Integration Fields ───────────────────────────────────────────
    raw_milk_product_id = fields.Many2one(
        'product.product',
        string='Raw Milk (Input)',
        help='The raw milk product received from farmers',
        default=lambda self: self._get_default_raw_milk_product(),
    )
    product_id = fields.Many2one(
        'product.product',
        string='Standardized Milk (Output)',
        help='The standardized milk product to produce',
        default=lambda self: self._get_default_standardized_product(),
    )

    def _get_default_raw_milk_product(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.raw_milk_product_id'
        )
        if param:
            return int(param)
        return False

    def _get_default_standardized_product(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.standardized_product_id'
        )
        if param:
            return int(param)
        return False
    picking_ids = fields.Many2many(
        'stock.picking',
        'milk_standardization_picking_rel',
        'standardization_id',
        'picking_id',
        string='Source Receipts',
        help='The stock receipts from which milk was received',
    )
    picking_count = fields.Integer(
        compute='_compute_picking_count',
        string='Receipts',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Processing Location',
        default=lambda self: self._get_default_location(),
        help='Location where standardization takes place',
    )

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # ── Stock Move References ──────────────────────────────────────────────
    raw_milk_move_id = fields.Many2one('stock.move', string='Raw Milk Stock Move', copy=False)
    water_move_id = fields.Many2one('stock.move', string='Water Stock Move', copy=False)
    smp_move_id = fields.Many2one('stock.move', string='SMP Stock Move', copy=False)
    output_move_id = fields.Many2one('stock.move', string='Output Stock Move', copy=False)
    move_count = fields.Integer(compute='_compute_move_count', string='Stock Moves')

    def _get_default_location(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.processing_location_id'
        )
        if param:
            return int(param)
        return False

    @api.depends('water_move_id', 'smp_move_id')
    def _compute_move_count(self):
        for rec in self:
            count = 0
            if rec.water_move_id:
                count += 1
            if rec.smp_move_id:
                count += 1
            rec.move_count = count

    # ── MRP Integration Fields ───────────────────────────────────────────
    use_mrp = fields.Boolean(
        string='Use Manufacturing Order',
        default=True,
        help='Create Manufacturing Order for standardization process instead of direct stock moves',
    )
    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        copy=False,
        readonly=True,
        ondelete='set null',
    )
    production_state = fields.Selection(
        related='production_id.state',
        string='MO State',
        readonly=True,
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        domain="[('type', '=', 'milk_standardization')]",
        help='BOM to use for creating Manufacturing Order',
    )

    @api.onchange('use_mrp')
    def _onchange_use_mrp(self):
        """Set default BOM when MRP mode is enabled."""
        if self.use_mrp and not self.bom_id:
            # Try to get default BOM from settings
            default_bom_id = self.env['ir.config_parameter'].sudo().get_param(
                'milk_standardization.default_bom_id'
            )
            if default_bom_id:
                bom = self.env['mrp.bom'].browse(int(default_bom_id))
                if bom.exists() and bom.type == 'milk_standardization':
                    self.bom_id = bom
            else:
                # Find any milk standardization BOM
                bom = self.env['mrp.bom'].search([
                    ('type', '=', 'milk_standardization')
                ], limit=1)
                if bom:
                    self.bom_id = bom

    # ── STEP 1 : Aggregate Milk Input ─────────────────────────────────────
    aggregate_qty = fields.Float(
        string='Aggregate Milk Qty (L)',
        required=True,
        digits=(12, 3),
    )
    aggregate_fat = fields.Float(
        string='Aggregate Fat %',
        digits=(5, 2),
        help='Weighted average fat % of the incoming aggregate milk (auto-calculated from receipts)',
    )
    aggregate_snf = fields.Float(
        string='Aggregate SNF %',
        digits=(5, 2),
        help='Weighted average SNF % of the incoming aggregate milk (auto-calculated from receipts)',
    )

    # Government standard (editable for custom requirements)
    target_fat = fields.Float(
        string='Target Fat %',
        default=3.0,
        digits=(5, 2),
        help='Target fat percentage (default 3% as per government standard)',
    )

    # ── STEP 1 : Water Calculation ────────────────────────────────────────
    water_to_add = fields.Float(
        string='Water to Add (L)',
        compute='_compute_water',
        store=True,
        digits=(12, 3),
        help='Calculated volume of water needed to bring fat to target 3%',
    )
    milk_after_water = fields.Float(
        string='Total Milk After Water (L)',
        compute='_compute_water',
        store=True,
        digits=(12, 3),
    )

    # ── STEP 2 : SNF Input (after water addition) ─────────────────────────
    snf_after_water_estimated = fields.Float(
        string='Estimated SNF % After Water',
        compute='_compute_estimated_snf',
        store=True,
        digits=(5, 2),
        help='Estimated SNF % after water addition (calculated from dilution)',
    )
    snf_after_water = fields.Float(
        string='SNF % (After Water Addition)',
        digits=(5, 2),
        help='Actual SNF % measured AFTER water has been added — enter manually',
    )

    # Government standard (editable for custom requirements)
    target_snf = fields.Float(
        string='Target SNF %',
        default=9.5,
        digits=(5, 2),
        help='Target SNF percentage (default 9.5% as per government standard)',
    )
    smp_snf_percent = fields.Float(
        string='SMP SNF %',
        default=96.0,
        digits=(5, 2),
        help='SNF % of the Skimmed Milk Powder being used (typically ~96%)',
    )

    # ── Progress Indicators ────────────────────────────────────────────────
    snf_deficit = fields.Float(
        string='SNF Deficit %',
        compute='_compute_snf_deficit',
        digits=(5, 2),
        help='How much SNF % is below target',
    )
    is_snf_sufficient = fields.Boolean(
        string='SNF Sufficient',
        compute='_compute_snf_deficit',
        help='True if current SNF meets or exceeds target',
    )

    # ── STEP 2 : SMP Calculation ──────────────────────────────────────────
    smp_to_add = fields.Float(
        string='SMP to Add (kg)',
        compute='_compute_smp',
        store=True,
        digits=(12, 3),
        help='Calculated weight of SMP needed to bring SNF to target 9.5%',
    )
    final_qty = fields.Float(
        string='Final Standardized Qty (L)',
        compute='_compute_smp',
        store=True,
        digits=(12, 3),
    )

    # ── Actual consumption (editable - may differ from calculated) ────────
    water_consumed = fields.Float(
        string='Water Actually Used (L)',
        digits=(12, 3),
        help='Actual water added - defaults to calculated but can be adjusted',
    )
    smp_consumed = fields.Float(
        string='SMP Actually Used (kg)',
        digits=(12, 3),
        help='Actual SMP added - defaults to calculated but can be adjusted',
    )

    # ── Final verified values ─────────────────────────────────────────────
    final_fat_verified = fields.Float(string='Final Fat % (Verified)', digits=(5, 2))
    final_snf_verified = fields.Float(string='Final SNF % (Verified)', digits=(5, 2))

    # ── Multi-Output Category Support ──────────────────────────────────────
    # Allows splitting raw milk into multiple output categories with different SNF targets
    use_multi_output = fields.Boolean(
        string='Multiple Output Categories',
        default=False,
        help='Enable to split raw milk into multiple output categories (e.g., Standard Milk 9.5 SNF, Curd Base 10.5 SNF)'
    )
    standardization_line_ids = fields.One2many(
        'milk.standardization.line',
        'standardization_id',
        string='Output Lines',
        help='Lines for each output category with specific SNF targets'
    )
    line_count = fields.Integer(
        compute='_compute_line_count',
        string='Output Categories'
    )
    total_allocated_qty = fields.Float(
        string='Total Allocated (L)',
        compute='_compute_line_totals',
        store=True,
        digits=(12, 3),
        help='Sum of all allocated quantities in lines'
    )
    unallocated_qty = fields.Float(
        string='Unallocated Qty (L)',
        compute='_compute_line_totals',
        store=True,
        digits=(12, 3),
        help='Aggregate quantity minus total allocated'
    )
    total_water_calculated = fields.Float(
        string='Total Water (Calculated)',
        compute='_compute_line_totals',
        store=True,
        digits=(12, 3),
        help='Sum of water needed for all lines'
    )
    total_smp_calculated = fields.Float(
        string='Total SMP (Calculated)',
        compute='_compute_line_totals',
        store=True,
        digits=(12, 3),
        help='Sum of SMP needed for all lines'
    )
    total_final_output = fields.Float(
        string='Total Final Output (L)',
        compute='_compute_line_totals',
        store=True,
        digits=(12, 3),
        help='Sum of final output from all lines'
    )

    @api.depends('standardization_line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.standardization_line_ids)

    @api.depends('standardization_line_ids.allocated_qty', 'standardization_line_ids.water_to_add',
                 'standardization_line_ids.smp_to_add', 'standardization_line_ids.final_qty',
                 'aggregate_qty')
    def _compute_line_totals(self):
        for rec in self:
            lines = rec.standardization_line_ids
            rec.total_allocated_qty = sum(lines.mapped('allocated_qty'))
            rec.unallocated_qty = rec.aggregate_qty - rec.total_allocated_qty
            rec.total_water_calculated = sum(lines.mapped('water_to_add'))
            rec.total_smp_calculated = sum(lines.mapped('smp_to_add'))
            rec.total_final_output = sum(lines.mapped('final_qty'))

    @api.constrains('standardization_line_ids', 'aggregate_qty', 'use_multi_output')
    def _check_allocation(self):
        """Ensure total allocation does not exceed aggregate quantity."""
        for rec in self:
            if rec.use_multi_output and rec.standardization_line_ids:
                total = sum(rec.standardization_line_ids.mapped('allocated_qty'))
                if total > rec.aggregate_qty + 0.001:  # Small tolerance for floating point
                    raise ValidationError(
                        _('Total allocated quantity (%.3f L) exceeds aggregate milk quantity (%.3f L)')
                        % (total, rec.aggregate_qty)
                    )

    # ──────────────────────────────────────────────────────────────────────
    # COMPUTE: Estimated SNF after water addition
    #   SNF gets diluted when water is added
    #   Formula: NewSNF% = OriginalSNF% × OriginalQty / (OriginalQty + Water)
    # ──────────────────────────────────────────────────────────────────────
    @api.depends('aggregate_snf', 'aggregate_qty', 'water_to_add')
    def _compute_estimated_snf(self):
        for rec in self:
            if rec.aggregate_qty > 0 and rec.milk_after_water > 0:
                rec.snf_after_water_estimated = (rec.aggregate_snf * rec.aggregate_qty) / rec.milk_after_water
            else:
                rec.snf_after_water_estimated = rec.aggregate_snf

    @api.depends('snf_after_water', 'target_snf')
    def _compute_snf_deficit(self):
        for rec in self:
            if rec.snf_after_water > 0:
                rec.snf_deficit = rec.target_snf - rec.snf_after_water
                rec.is_snf_sufficient = rec.snf_after_water >= rec.target_snf
            else:
                rec.snf_deficit = 0
                rec.is_snf_sufficient = False

    @api.onchange('snf_after_water')
    def _onchange_snf_after_water(self):
        """Auto-calculate SMP when SNF after water is entered."""
        if self.snf_after_water > 0 and self.milk_after_water > 0:
            # SMP calculation is done by _compute_smp, but we also set smp_consumed
            if self.snf_after_water < self.target_snf and self.smp_snf_percent > 0:
                smp = (
                    self.milk_after_water
                    * (self.target_snf - self.snf_after_water)
                    / self.smp_snf_percent
                )
                self.smp_consumed = smp

    @api.onchange('water_to_add')
    def _onchange_water_to_add(self):
        """Auto-set water consumed when water to add is calculated."""
        if self.water_to_add > 0 and not self.water_consumed:
            self.water_consumed = self.water_to_add

    # ──────────────────────────────────────────────────────────────────────
    # COMPUTE: Water to Add
    #   Formula:  Water = Qty × (Fat% − 3) / 3
    #   Derivation:
    #     Original fat mass  = Qty × Fat%
    #     After adding W litres of water fat mass stays the same:
    #       (Qty + W) × 3% = Qty × Fat%
    #       W = Qty × (Fat% − 3) / 3
    # ──────────────────────────────────────────────────────────────────────
    @api.depends('aggregate_qty', 'aggregate_fat', 'target_fat')
    def _compute_water(self):
        for rec in self:
            if rec.aggregate_fat <= rec.target_fat or rec.aggregate_qty <= 0:
                rec.water_to_add = 0.0
                rec.milk_after_water = rec.aggregate_qty
            else:
                water = rec.aggregate_qty * (rec.aggregate_fat - rec.target_fat) / rec.target_fat
                rec.water_to_add = water
                rec.milk_after_water = rec.aggregate_qty + water

    # ──────────────────────────────────────────────────────────────────────
    # COMPUTE: SMP to Add
    #   Formula:  SMP = TotalMilk × (TargetSNF − CurrentSNF) / SMP_SNF%
    #   Derivation:
    #     SNF mass in milk       = TotalMilk × CurrentSNF%
    #     SNF mass needed        = TotalMilk × TargetSNF%
    #     Extra SNF needed       = TotalMilk × (TargetSNF% − CurrentSNF%)
    #     SMP needed             = ExtraSNF / SMP_SNF%
    # ──────────────────────────────────────────────────────────────────────
    @api.depends('milk_after_water', 'snf_after_water', 'target_snf', 'smp_snf_percent')
    def _compute_smp(self):
        for rec in self:
            if (
                rec.snf_after_water <= 0
                or rec.smp_snf_percent <= 0
                or rec.snf_after_water >= rec.target_snf
                or rec.milk_after_water <= 0
            ):
                rec.smp_to_add = 0.0
                rec.final_qty = rec.milk_after_water
            else:
                smp = (
                    rec.milk_after_water
                    * (rec.target_snf - rec.snf_after_water)
                    / rec.smp_snf_percent
                )
                rec.smp_to_add = smp
                # SMP adds ≈ 1 litre per kg (approximate; adjust density if needed)
                rec.final_qty = rec.milk_after_water + smp

    # ── Validations ───────────────────────────────────────────────────────
    def _validate_fat_for_standardization(self):
        """Validate fat % before starting standardization process."""
        for rec in self:
            if rec.aggregate_fat <= 0:
                raise ValidationError('Aggregate Fat % must be greater than 0. Please enter the fat %.')
            if rec.aggregate_fat <= 3.0:
                raise ValidationError(
                    'Aggregate Fat % is already ≤ 3%. No water addition required.'
                )

    # ── State transitions ─────────────────────────────────────────────────
    def _get_water_product(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.water_product_id'
        )
        if param:
            product = self.env['product.product'].browse(int(param))
            if product.exists():
                return product
        raise UserError('Please configure Water Product in Settings > Milk Standardization.')

    def _get_smp_product(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.smp_product_id'
        )
        if param:
            product = self.env['product.product'].browse(int(param))
            if product.exists():
                return product
        raise UserError('Please configure SMP Product in Settings > Milk Standardization.')

    def _get_stock_location(self):
        """Get default stock location for consuming materials."""
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_id.id)], limit=1
        )
        if warehouse:
            return warehouse.lot_stock_id
        raise UserError('No warehouse found for the company.')

    def _create_stock_move(self, product, qty, location_src, location_dest, reference):
        """Create and validate a stock move."""
        move = self.env['stock.move'].create({
            'name': reference,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'origin': reference,
            'company_id': self.company_id.id,
        })

        move._action_confirm()
        move._action_assign()

        # Create move line manually if not created
        if not move.move_line_ids:
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'location_id': location_src.id,
                'location_dest_id': location_dest.id,
                'quantity': qty,
                'company_id': self.company_id.id,
            })
        else:
            move.move_line_ids.write({'quantity': qty})

        move._action_done()
        return move

    def _consume_product(self, product, qty, reference):
        """Consume a product from stock (decrease on-hand quantity)."""
        if qty <= 0 or not product:
            return

        stock_location = self._get_stock_location()

        # Directly update quant - decrease quantity
        quant = self.env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id', '=', stock_location.id),
        ], limit=1)

        if quant:
            new_qty = quant.quantity - qty
            quant.write({'quantity': new_qty})
        else:
            # Create negative quant
            self.env['stock.quant'].sudo().create({
                'product_id': product.id,
                'location_id': stock_location.id,
                'quantity': -qty,
            })

    def _produce_product(self, product, qty, location=None):
        """Produce a product to stock (increase on-hand quantity)."""
        if qty <= 0 or not product:
            return

        if not location:
            location = self._get_stock_location()

        # Directly update quant - increase quantity
        quant = self.env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
        ], limit=1)

        if quant:
            new_qty = quant.quantity + qty
            quant.write({'quantity': new_qty})
        else:
            # Create new quant
            self.env['stock.quant'].sudo().create({
                'product_id': product.id,
                'location_id': location.id,
                'quantity': qty,
            })

    def action_confirm_water(self):
        """Confirm water addition - creates stock move or updates MO."""
        # Validate fat % before proceeding
        self._validate_fat_for_standardization()

        for rec in self:
            # Set actual water consumed (default to calculated if not entered)
            if not rec.water_consumed:
                rec.water_consumed = rec.water_to_add

            if rec.use_mrp:
                # MRP Mode: Auto-create MO if not exists
                if not rec.production_id and rec.bom_id:
                    rec._auto_create_manufacturing_order()
                # Update MO with water quantity
                if rec.production_id:
                    rec.production_id._update_standardization_quantities(rec)
            else:
                # Direct Mode: Consume water from stock
                if rec.water_consumed > 0:
                    water_product = rec._get_water_product()
                    rec._consume_product(water_product, rec.water_consumed, f'{rec.name} - Water Consumed')

            rec.state = 'step1'

    def action_confirm_snf(self):
        """Confirm SNF entry - creates stock move or updates MO."""
        for rec in self:
            if not rec.snf_after_water:
                raise ValidationError(_('Please enter the SNF % after water addition.'))

            # Set actual SMP consumed (default to calculated if not entered)
            if not rec.smp_consumed:
                rec.smp_consumed = rec.smp_to_add

            if rec.use_mrp:
                # MRP Mode: Update MO with SMP quantity
                if rec.production_id:
                    rec.production_id._update_standardization_quantities(rec)
            else:
                # Direct Mode: Consume SMP from stock
                if rec.smp_consumed > 0:
                    smp_product = rec._get_smp_product()
                    rec._consume_product(smp_product, rec.smp_consumed, f'{rec.name} - SMP Consumed')

            rec.state = 'step2'

    def _get_production_location(self):
        """Get virtual production location for inventory adjustments."""
        location = self.env['stock.location'].search([
            ('usage', '=', 'production'),
            ('company_id', 'in', [self.company_id.id, False]),
        ], limit=1)
        if not location:
            # Fallback: search by name
            location = self.env['stock.location'].search([
                ('name', 'ilike', 'production'),
                ('usage', '=', 'production'),
            ], limit=1)
        if not location:
            raise UserError('Production location not found. Please check your stock configuration.')
        return location

    def action_done(self):
        """Mark as done - complete MO or update inventory directly."""
        for rec in self:
            # Validate that final verified values are entered
            if not rec.final_fat_verified:
                raise UserError(_('Please enter the Final Fat % (Verified) before marking as standardized.'))
            if not rec.final_snf_verified:
                raise UserError(_('Please enter the Final SNF % (Verified) before marking as standardized.'))

            # Use actual consumed values
            water_used = rec.water_consumed or 0
            smp_used = rec.smp_consumed or 0
            raw_milk_qty = rec.aggregate_qty or 0
            final_qty = raw_milk_qty + water_used + smp_used

            # Get products
            water_product = rec._get_water_product()
            smp_product = rec._get_smp_product()
            stock_location = rec._get_stock_location()

            if rec.use_mrp and rec.production_id:
                # MRP Mode: Try to complete the Manufacturing Order
                production = rec.production_id
                try:
                    if production.state == 'draft':
                        production.action_confirm()
                    if production.state == 'confirmed':
                        production.action_assign()

                    # Set quantity produced
                    if production.state in ('confirmed', 'progress', 'to_close'):
                        production.qty_producing = final_qty

                        # Update raw material move quantities and their move lines
                        for move in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                            if move.product_id == water_product:
                                qty_to_consume = water_used
                            elif move.product_id == smp_product:
                                qty_to_consume = smp_used
                            elif move.product_id == rec.raw_milk_product_id:
                                qty_to_consume = raw_milk_qty
                            else:
                                continue

                            # Update move quantity
                            move.product_uom_qty = qty_to_consume

                            # Update or create move lines with quantity
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

                        # Mark MO as done
                        production.button_mark_done()
                except Exception:
                    pass  # Fallback to direct consumption below

                rec.message_post(
                    body=_('Manufacturing Order %s completed. '
                           'Raw milk: %.3f L, Water: %.3f L, SMP: %.3f kg → Standardized milk: %.3f L')
                    % (production.name, raw_milk_qty, water_used, smp_used, final_qty)
                )
            else:
                rec.message_post(
                    body=_('Standardization complete:\n'
                           '• Raw milk consumed: %.3f L\n'
                           '• Water consumed: %.3f L\n'
                           '• SMP consumed: %.3f kg\n'
                           '• Standardized milk produced: %.3f L')
                    % (raw_milk_qty, water_used, smp_used, final_qty)
                )

            # ALWAYS consume materials directly using quant update
            # This ensures inventory is updated in all scenarios
            rec._consume_product(water_product, water_used, f'{rec.name} - Water')
            rec._consume_product(smp_product, smp_used, f'{rec.name} - SMP')
            if rec.raw_milk_product_id and raw_milk_qty > 0:
                rec._consume_product(rec.raw_milk_product_id, raw_milk_qty, f'{rec.name} - Raw Milk')

            # Produce standardized milk
            if rec.product_id and final_qty > 0:
                rec._produce_product(rec.product_id, final_qty, stock_location)

            rec.state = 'done'

    def action_reset(self):
        """Reset to draft. Note: Stock moves are not reversed."""
        for rec in self:
            rec.state = 'draft'

    def action_view_stock_moves(self):
        """Open related stock moves."""
        self.ensure_one()
        move_ids = []
        if self.water_move_id:
            move_ids.append(self.water_move_id.id)
        if self.smp_move_id:
            move_ids.append(self.smp_move_id.id)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Moves',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', move_ids)],
            'context': {'create': False},
        }

    def action_view_pickings(self):
        """Open related source pickings."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Source Receipts',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': {'create': False},
        }

    # ── MRP Integration Methods ──────────────────────────────────────────

    def action_create_manufacturing_order(self):
        """Create Manufacturing Order from standardization record."""
        self.ensure_one()

        if not self.use_mrp:
            raise UserError(_('MRP mode is not enabled for this standardization.'))

        if self.production_id:
            raise UserError(_('A Manufacturing Order already exists for this standardization.'))

        if not self.bom_id:
            raise UserError(_('Please select a Bill of Materials before creating Manufacturing Order.'))

        if not self.product_id:
            raise UserError(_('Please select a Milk Product before creating Manufacturing Order.'))

        if self.aggregate_qty <= 0:
            raise UserError(_('Aggregate Milk Quantity must be greater than 0.'))

        # Validate fat % before creating MO
        self._validate_fat_for_standardization()

        mo_vals = self._prepare_mo_values()
        production = self.env['mrp.production'].create(mo_vals)

        # Update component quantities based on standardization calculations
        production._update_standardization_quantities(self)

        self.production_id = production.id

        self.message_post(
            body=_('Manufacturing Order %s created with calculated quantities: Water %.3f L')
            % (production.name, self.water_to_add)
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Manufacturing Order'),
            'res_model': 'mrp.production',
            'res_id': production.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _auto_create_manufacturing_order(self):
        """Auto-create Manufacturing Order (called internally, no UI return)."""
        self.ensure_one()

        if self.production_id:
            return  # Already exists

        if not self.bom_id:
            # Try to find default BOM
            default_bom_id = self.env['ir.config_parameter'].sudo().get_param(
                'milk_standardization.default_bom_id'
            )
            if default_bom_id:
                self.bom_id = int(default_bom_id)
            else:
                # Find any milk standardization BOM
                bom = self.env['mrp.bom'].search([
                    ('type', '=', 'milk_standardization')
                ], limit=1)
                if bom:
                    self.bom_id = bom.id

        if not self.bom_id:
            raise UserError(_('No Bill of Materials found. Please create a Milk Standardization BOM first.'))

        mo_vals = self._prepare_mo_values()
        production = self.env['mrp.production'].create(mo_vals)
        production._update_standardization_quantities(self)
        self.production_id = production.id

        self.message_post(
            body=_('Manufacturing Order %s auto-created') % production.name
        )

    def _prepare_mo_values(self):
        """Prepare values for Manufacturing Order creation."""
        self.ensure_one()

        # Calculate final quantity (aggregate + water + smp estimate)
        estimated_final_qty = self.milk_after_water
        if self.aggregate_snf > 0 and self.aggregate_snf < self.target_snf:
            # Estimate SMP based on aggregate SNF (will be recalculated after water step)
            estimated_smp = (
                self.milk_after_water
                * (self.target_snf - self.aggregate_snf)
                / self.smp_snf_percent
            )
            estimated_final_qty += estimated_smp

        return {
            'bom_id': self.bom_id.id,
            'product_id': self.product_id.id,
            'product_qty': estimated_final_qty or self.aggregate_qty,
            'product_uom_id': self.product_id.uom_id.id,
            'standardization_id': self.id,
            'origin': self.name,
            'date_start': fields.Datetime.now(),
            'aggregate_fat_percent': self.aggregate_fat,
        }

    def action_view_manufacturing_order(self):
        """Open the related Manufacturing Order."""
        self.ensure_one()
        if not self.production_id:
            raise UserError(_('No Manufacturing Order linked to this standardization.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Manufacturing Order'),
            'res_model': 'mrp.production',
            'res_id': self.production_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Multi-Output Category Methods ──────────────────────────────────────

    def action_add_output_line(self):
        """Open wizard to add a new output line."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Output Category'),
            'res_model': 'milk.standardization.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_standardization_id': self.id,
            },
        }

    def action_view_output_lines(self):
        """View all output lines for this standardization."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Output Categories'),
            'res_model': 'milk.standardization.line',
            'view_mode': 'list,form',
            'domain': [('standardization_id', '=', self.id)],
            'context': {
                'default_standardization_id': self.id,
            },
        }

    def action_distribute_equally(self):
        """Distribute aggregate quantity equally among all output lines."""
        self.ensure_one()
        if not self.standardization_line_ids:
            raise UserError(_('Please add output categories first.'))

        qty_per_line = self.aggregate_qty / len(self.standardization_line_ids)
        for line in self.standardization_line_ids:
            line.allocated_qty = qty_per_line

    def action_allocate_remaining(self):
        """Allocate remaining quantity to a specific line (opens wizard)."""
        self.ensure_one()
        if self.unallocated_qty <= 0:
            raise UserError(_('No unallocated quantity remaining.'))

        # Return action to select which line gets the remaining
        return {
            'type': 'ir.actions.act_window',
            'name': _('Allocate Remaining: %.3f L') % self.unallocated_qty,
            'res_model': 'milk.standardization.line',
            'view_mode': 'list',
            'domain': [('standardization_id', '=', self.id)],
            'context': {
                'default_standardization_id': self.id,
            },
        }

    def create_default_lines_from_categories(self):
        """Create output lines from all active categories (helper method)."""
        self.ensure_one()
        categories = self.env['milk.output.category'].search([
            ('active', '=', True),
            '|',
            ('company_id', '=', self.company_id.id),
            ('company_id', '=', False),
        ])

        if not categories:
            raise UserError(_('No active milk output categories found. Please create categories first.'))

        # Clear existing lines
        self.standardization_line_ids.unlink()

        # Create lines for each category
        qty_per_category = self.aggregate_qty / len(categories) if categories else 0
        for category in categories:
            self.env['milk.standardization.line'].create({
                'standardization_id': self.id,
                'output_category_id': category.id,
                'allocated_qty': qty_per_category,
            })

    def _validate_lines_for_water_step(self):
        """Validate all lines are ready for water confirmation."""
        for rec in self:
            if not rec.use_multi_output:
                return
            if not rec.standardization_line_ids:
                raise ValidationError(_('Please add output category lines before proceeding.'))
            if rec.unallocated_qty > 0.001:
                raise ValidationError(
                    _('There is %.3f L of unallocated milk. Please allocate all milk to output categories.')
                    % rec.unallocated_qty
                )
            for line in rec.standardization_line_ids:
                line.validate_for_water_step()

    def _validate_lines_for_snf_step(self):
        """Validate all lines are ready for SNF confirmation."""
        for rec in self:
            if not rec.use_multi_output:
                return
            for line in rec.standardization_line_ids:
                line.validate_for_snf_step()

    def _validate_lines_for_completion(self):
        """Validate all lines are ready for completion."""
        for rec in self:
            if not rec.use_multi_output:
                return
            for line in rec.standardization_line_ids:
                line.validate_for_completion()

    def action_confirm_water_multi(self):
        """Confirm water addition for multi-output mode."""
        for rec in self:
            if not rec.use_multi_output:
                return rec.action_confirm_water()

            # Validate lines
            rec._validate_lines_for_water_step()

            # Set default water consumed for each line
            for line in rec.standardization_line_ids:
                if not line.water_consumed:
                    line.water_consumed = line.water_to_add

            # Update parent totals for convenience
            rec.water_consumed = sum(rec.standardization_line_ids.mapped('water_consumed'))

            # Note: Actual inventory consumption happens in action_done_multi
            rec.state = 'step1'

    def action_confirm_snf_multi(self):
        """Confirm SNF entry for multi-output mode."""
        for rec in self:
            if not rec.use_multi_output:
                return rec.action_confirm_snf()

            # Validate lines
            rec._validate_lines_for_snf_step()

            # Set default SMP consumed for each line
            for line in rec.standardization_line_ids:
                if not line.smp_consumed:
                    line.smp_consumed = line.smp_to_add

            # Update parent totals
            rec.smp_consumed = sum(rec.standardization_line_ids.mapped('smp_consumed'))

            # For MRP lines, create Manufacturing Orders (for tracking only)
            for line in rec.standardization_line_ids.filtered(lambda l: l.use_mrp):
                if not line.production_id:
                    try:
                        line.action_create_manufacturing_order()
                        line.action_confirm_manufacturing_order()
                    except Exception:
                        pass  # MO creation is optional for tracking

            rec.state = 'step2'

    def action_done_multi(self):
        """Complete standardization for multi-output mode - produces multiple products."""
        for rec in self:
            if not rec.use_multi_output:
                return rec.action_done()

            # Validate lines
            rec._validate_lines_for_completion()

            stock_location = rec._get_stock_location()

            # Produce each output product and consume materials
            message_lines = [_('Multi-output standardization complete:')]
            message_lines.append(_('• Raw milk consumed: %.3f L') % rec.aggregate_qty)
            message_lines.append(_('• Total water consumed: %.3f L') % rec.water_consumed)
            message_lines.append(_('• Total SMP consumed: %.3f kg') % rec.smp_consumed)
            message_lines.append('')
            message_lines.append(_('Output Products:'))

            for line in rec.standardization_line_ids:
                if not line.output_product_id or line.final_qty <= 0:
                    continue

                # Consume raw milk for this line
                if rec.raw_milk_product_id and line.allocated_qty > 0:
                    rec._consume_product(rec.raw_milk_product_id, line.allocated_qty, f'{rec.name} - {line.output_category_id.name} Raw Milk')

                # Consume water for this line
                if line.water_consumed > 0:
                    water_product = rec._get_water_product()
                    rec._consume_product(water_product, line.water_consumed, f'{rec.name} - {line.output_category_id.name} Water')

                # Consume SMP for this line
                if line.smp_consumed > 0:
                    smp_product = rec._get_smp_product()
                    rec._consume_product(smp_product, line.smp_consumed, f'{rec.name} - {line.output_category_id.name} SMP')

                # Produce output product
                rec._produce_product(line.output_product_id, line.final_qty, stock_location)

                # Track MO info for message if applicable
                mo_info = ''
                if line.use_mrp and line.production_id:
                    mo_info = f' [MO: {line.production_id.name}]'
                    # Try to complete MO for tracking purposes
                    try:
                        line.action_complete_manufacturing_order()
                    except Exception:
                        pass

                message_lines.append(
                    _('• %s: %.3f L (Fat: %.2f%%, SNF: %.2f%%)%s')
                    % (line.output_product_id.name, line.final_qty,
                       line.final_fat_verified, line.final_snf_verified, mo_info)
                )

            rec.message_post(body='<br/>'.join(message_lines))
            rec.state = 'done'

