import logging
from odoo import models, fields, api
from datetime import date

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    has_milk_product = fields.Boolean(
        compute='_compute_has_milk_product',
        store=True,
        string='Has Milk Product',
    )

    @api.depends('order_line.product_id', 'order_line.is_milk_product')
    def _compute_has_milk_product(self):
        for order in self:
            order.has_milk_product = any(line.is_milk_product for line in order.order_line)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    milk_fat_percentage = fields.Float(
        string='Fat %',
        digits=(5, 2),
        help='Fat percentage of the milk being purchased',
    )
    milk_snf_percentage = fields.Float(
        string='SNF %',
        digits=(5, 2),
        help='SNF (Solids-Not-Fat) percentage of the milk being purchased',
    )
    is_milk_product = fields.Boolean(
        compute='_compute_is_milk_product',
        store=True,
        string='Is Milk Product',
    )

    @api.depends('product_id', 'product_id.categ_id')
    def _compute_is_milk_product(self):
        # Get milk category from settings
        milk_category_id = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.milk_category_id'
        )
        milk_category_id = int(milk_category_id) if milk_category_id else False

        for line in self:
            is_milk = False
            if milk_category_id and line.product_id:
                # Check if product's category matches milk category (including parent categories)
                category = line.product_id.categ_id
                while category:
                    if category.id == milk_category_id:
                        is_milk = True
                        break
                    category = category.parent_id
            line.is_milk_product = is_milk

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        """Override to copy fat % and SNF % to stock move."""
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        vals['milk_fat_percentage'] = self.milk_fat_percentage
        vals['milk_snf_percentage'] = self.milk_snf_percentage
        return vals


class StockMove(models.Model):
    _inherit = 'stock.move'

    milk_fat_percentage = fields.Float(
        string='Fat %',
        digits=(5, 2),
        help='Fat percentage of the milk in this move',
    )
    milk_snf_percentage = fields.Float(
        string='SNF %',
        digits=(5, 2),
        help='SNF (Solids-Not-Fat) percentage of the milk in this move',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Copy fat% and snf% from purchase order line when creating stock moves."""
        moves = super().create(vals_list)
        for move in moves:
            # If fat/snf not set, try to get from purchase order line
            if move.purchase_line_id and (not move.milk_fat_percentage or not move.milk_snf_percentage):
                if not move.milk_fat_percentage and move.purchase_line_id.milk_fat_percentage:
                    move.milk_fat_percentage = move.purchase_line_id.milk_fat_percentage
                if not move.milk_snf_percentage and move.purchase_line_id.milk_snf_percentage:
                    move.milk_snf_percentage = move.purchase_line_id.milk_snf_percentage
        return moves

    def _action_done(self, cancel_backorder=False):
        """Ensure fat% and snf% are copied before completing the move."""
        for move in self:
            # Final check - copy from purchase line if still not set
            if move.purchase_line_id:
                if not move.milk_fat_percentage and move.purchase_line_id.milk_fat_percentage:
                    move.milk_fat_percentage = move.purchase_line_id.milk_fat_percentage
                if not move.milk_snf_percentage and move.purchase_line_id.milk_snf_percentage:
                    move.milk_snf_percentage = move.purchase_line_id.milk_snf_percentage
        return super()._action_done(cancel_backorder=cancel_backorder)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    standardization_ids = fields.Many2many(
        'milk.standardization',
        'milk_standardization_picking_rel',
        'picking_id',
        'standardization_id',
        string='Standardization Records',
    )
    standardization_count = fields.Integer(
        compute='_compute_standardization_count',
        string='Standardizations',
    )

    @api.depends('standardization_ids')
    def _compute_standardization_count(self):
        for picking in self:
            picking.standardization_count = len(picking.standardization_ids)

    def _get_milk_moves(self):
        """Get all moves with milk products from this picking."""
        # Get milk category from settings
        milk_category_id = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.milk_category_id'
        )
        milk_category_id = int(milk_category_id) if milk_category_id else False

        if not milk_category_id:
            return self.env['stock.move']

        milk_moves = self.env['stock.move']
        for move in self.move_ids:
            # Check if product's category matches milk category
            category = move.product_id.categ_id
            while category:
                if category.id == milk_category_id:
                    milk_moves |= move
                    break
                category = category.parent_id
        return milk_moves

    def _calculate_weighted_fat(self, milk_moves):
        """Calculate weighted average fat % from milk moves."""
        total_qty = 0.0
        total_fat_qty = 0.0  # qty × fat%

        for move in milk_moves:
            qty = move.quantity
            # Try move's fat%, then fall back to purchase line
            fat = move.milk_fat_percentage
            if not fat and move.purchase_line_id:
                fat = move.purchase_line_id.milk_fat_percentage or 0.0
            fat = fat or 0.0
            total_qty += qty
            total_fat_qty += qty * fat

        if total_qty > 0 and total_fat_qty > 0:
            return total_fat_qty / total_qty
        return 0.0

    def _calculate_weighted_snf(self, milk_moves):
        """Calculate weighted average SNF % from milk moves."""
        total_qty = 0.0
        total_snf_qty = 0.0  # qty × snf%

        for move in milk_moves:
            qty = move.quantity
            # Try move's snf%, then fall back to purchase line
            snf = move.milk_snf_percentage
            if not snf and move.purchase_line_id:
                snf = move.purchase_line_id.milk_snf_percentage or 0.0
            snf = snf or 0.0
            total_qty += qty
            total_snf_qty += qty * snf

        if total_qty > 0 and total_snf_qty > 0:
            return total_snf_qty / total_qty
        return 0.0

    def button_validate(self):
        """Override to auto-create daily standardization for milk products."""
        res = super().button_validate()

        # Process each picking that was validated
        for picking in self:
            _logger.info(f"MILK DEBUG button_validate - Processing picking {picking.name}, type={picking.picking_type_code}")

            # Only for incoming receipts
            if picking.picking_type_code != 'incoming':
                _logger.info(f"MILK DEBUG - Skipping: not incoming (type={picking.picking_type_code})")
                continue

            # Check milk category configuration
            milk_category_id = self.env['ir.config_parameter'].sudo().get_param(
                'milk_standardization.milk_category_id'
            )
            _logger.info(f"MILK DEBUG - milk_category_id from settings: {milk_category_id}")

            milk_moves = picking._get_milk_moves()
            _logger.info(f"MILK DEBUG - Found {len(milk_moves)} milk moves")

            if not milk_moves:
                _logger.info("MILK DEBUG - No milk moves found, checking why...")
                for move in picking.move_ids:
                    _logger.info(f"MILK DEBUG - Move {move.id}: product={move.product_id.name}, category={move.product_id.categ_id.name} (id={move.product_id.categ_id.id})")
                continue

            # Calculate total milk quantity and weighted fat/snf %
            total_qty = sum(milk_moves.mapped('quantity'))
            if total_qty <= 0:
                continue

            # DEBUG: Log what we're reading from moves
            for move in milk_moves:
                pol_fat = move.purchase_line_id.milk_fat_percentage if move.purchase_line_id else 'N/A'
                pol_snf = move.purchase_line_id.milk_snf_percentage if move.purchase_line_id else 'N/A'
                _logger.info(
                    f"MILK DEBUG - Move {move.id}: qty={move.quantity}, "
                    f"move.fat={move.milk_fat_percentage}, move.snf={move.milk_snf_percentage}, "
                    f"POL.fat={pol_fat}, POL.snf={pol_snf}, "
                    f"purchase_line_id={move.purchase_line_id.id if move.purchase_line_id else None}"
                )

            # Calculate weighted average fat % and SNF % for this picking
            picking_fat = picking._calculate_weighted_fat(milk_moves)
            picking_snf = picking._calculate_weighted_snf(milk_moves)
            _logger.info(f"MILK DEBUG - Calculated: fat={picking_fat}, snf={picking_snf}")

            # Get the raw milk product from the move (INPUT product)
            raw_milk_product = milk_moves[0].product_id

            # Get standardized milk product from settings (OUTPUT product)
            standardized_product_id = self.env['ir.config_parameter'].sudo().get_param(
                'milk_standardization.standardized_product_id'
            )
            standardized_product = False
            if standardized_product_id:
                standardized_product = self.env['product.product'].browse(int(standardized_product_id))

            # Find or create daily standardization record
            # Search by raw_milk_product_id (INPUT) since that's what we receive
            today = date.today()
            daily_standardization = self.env['milk.standardization'].search([
                ('date', '>=', f'{today} 00:00:00'),
                ('date', '<=', f'{today} 23:59:59'),
                ('state', '=', 'draft'),
                ('raw_milk_product_id', '=', raw_milk_product.id),
            ], limit=1)

            _logger.info(f"MILK DEBUG - Found daily_standardization: {daily_standardization.id if daily_standardization else None}")

            if daily_standardization:
                # Calculate new weighted average fat % and SNF %
                old_qty = daily_standardization.aggregate_qty
                old_fat = daily_standardization.aggregate_fat
                old_snf = daily_standardization.aggregate_snf or 0.0
                new_qty = old_qty + total_qty

                # Weighted average: (old_qty × old_value + new_qty × new_value) / total_qty
                if picking_fat > 0:
                    new_fat = ((old_qty * old_fat) + (total_qty * picking_fat)) / new_qty
                else:
                    new_fat = old_fat  # Keep old fat if new one not entered

                if picking_snf > 0:
                    new_snf = ((old_qty * old_snf) + (total_qty * picking_snf)) / new_qty
                else:
                    new_snf = old_snf  # Keep old snf if new one not entered

                daily_standardization.write({
                    'aggregate_qty': new_qty,
                    'aggregate_fat': new_fat,
                    'aggregate_snf': new_snf,
                    'notes': (daily_standardization.notes or '') +
                             f'\nAdded {total_qty}L @ {picking_fat:.2f}% fat, {picking_snf:.2f}% SNF from {picking.name} ({picking.partner_id.name or "Unknown"})',
                })
                # Link this picking
                daily_standardization.picking_ids = [(4, picking.id)]
                _logger.info(f"MILK DEBUG - Updated standardization {daily_standardization.id}: qty={new_qty}, fat={new_fat}, snf={new_snf}")
            else:
                # Create new daily standardization record
                # raw_milk_product_id = INPUT (what we received)
                # product_id = OUTPUT (standardized milk from settings)
                create_vals = {
                    'raw_milk_product_id': raw_milk_product.id,
                    'product_id': standardized_product.id if standardized_product else raw_milk_product.id,
                    'aggregate_qty': total_qty,
                    'aggregate_fat': picking_fat if picking_fat > 0 else 4.0,
                    'aggregate_snf': picking_snf if picking_snf > 0 else 8.5,
                    'notes': f'Auto-created from {picking.name} ({picking.partner_id.name or "Unknown"}): {total_qty}L @ {picking_fat:.2f}% fat, {picking_snf:.2f}% SNF',
                }
                _logger.info(f"MILK DEBUG - Creating standardization with: {create_vals}")
                standardization = self.env['milk.standardization'].create(create_vals)
                standardization.picking_ids = [(4, picking.id)]
                _logger.info(f"MILK DEBUG - Created standardization {standardization.id}")

        return res

    def action_create_standardization(self):
        """Create milk standardization record from this receipt, or redirect to existing one."""
        self.ensure_one()

        # Check if standardization already exists for this picking
        if self.standardization_ids:
            # Redirect to existing standardization record
            if len(self.standardization_ids) == 1:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Milk Standardization',
                    'res_model': 'milk.standardization',
                    'res_id': self.standardization_ids[0].id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                # Multiple records - show list
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Milk Standardization',
                    'res_model': 'milk.standardization',
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', self.standardization_ids.ids)],
                    'target': 'current',
                }

        # No existing record - create new one
        # Get all moves with their fat/snf values
        total_qty = 0.0
        total_fat_qty = 0.0
        total_snf_qty = 0.0
        raw_milk_product = False

        for move in self.move_ids:
            if not raw_milk_product:
                raw_milk_product = move.product_id

            qty = move.quantity or 0
            total_qty += qty

            # Get fat% - try move first, then purchase line
            fat = move.milk_fat_percentage or 0.0
            if not fat and move.purchase_line_id:
                fat = move.purchase_line_id.milk_fat_percentage or 0.0

            # Get snf% - try move first, then purchase line
            snf = move.milk_snf_percentage or 0.0
            if not snf and move.purchase_line_id:
                snf = move.purchase_line_id.milk_snf_percentage or 0.0

            total_fat_qty += qty * fat
            total_snf_qty += qty * snf

            _logger.info(
                f"MILK DEBUG action_create_standardization - Move {move.id}: "
                f"qty={qty}, fat={fat}, snf={snf}, "
                f"purchase_line_id={move.purchase_line_id.id if move.purchase_line_id else None}"
            )

        if not raw_milk_product:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Products',
                    'message': 'No products found in this receipt.',
                    'type': 'warning',
                }
            }

        # Calculate weighted averages
        picking_fat = (total_fat_qty / total_qty) if total_qty > 0 and total_fat_qty > 0 else 0.0
        picking_snf = (total_snf_qty / total_qty) if total_qty > 0 and total_snf_qty > 0 else 0.0

        _logger.info(f"MILK DEBUG - Calculated weighted: fat={picking_fat}, snf={picking_snf}")

        # Get standardized milk product from settings
        standardized_product_id = self.env['ir.config_parameter'].sudo().get_param(
            'milk_standardization.standardized_product_id'
        )
        standardized_product = False
        if standardized_product_id:
            standardized_product = self.env['product.product'].browse(int(standardized_product_id))

        # Create standardization record
        create_vals = {
            'raw_milk_product_id': raw_milk_product.id,
            'product_id': standardized_product.id if standardized_product else raw_milk_product.id,
            'aggregate_qty': total_qty,
            'aggregate_fat': picking_fat if picking_fat > 0 else 4.0,
            'aggregate_snf': picking_snf if picking_snf > 0 else 8.5,
            'notes': f'Created from {self.name}: {total_qty}L @ {picking_fat:.2f}% fat, {picking_snf:.2f}% SNF',
        }
        _logger.info(f"MILK DEBUG - Creating standardization with: {create_vals}")

        standardization = self.env['milk.standardization'].create(create_vals)
        # Link picking to standardization
        standardization.picking_ids = [(4, self.id)]

        return {
            'type': 'ir.actions.act_window',
            'name': 'Milk Standardization',
            'res_model': 'milk.standardization',
            'res_id': standardization.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_standardizations(self):
        """View related standardization records."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Standardization Records',
            'res_model': 'milk.standardization',
            'view_mode': 'list,form',
            'domain': [('picking_ids', 'in', self.id)],
        }
