from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Link to milk standardization record
    standardization_id = fields.Many2one(
        'milk.standardization',
        string='Milk Standardization',
        ondelete='set null',
        index=True,
        copy=False,
    )

    is_milk_standardization = fields.Boolean(
        related='bom_id.is_milk_standardization',
        store=True,
        string='Is Milk Standardization',
    )

    # Milk standardization specific fields for tracking
    aggregate_fat_percent = fields.Float(
        string='Aggregate Fat %',
        digits=(5, 2),
        help='Fat percentage of the input milk',
    )
    snf_after_water_percent = fields.Float(
        string='SNF After Water %',
        digits=(5, 2),
        help='SNF percentage measured after water addition',
    )
    water_qty_calculated = fields.Float(
        string='Water Qty (Calculated)',
        digits=(12, 3),
        compute='_compute_standardization_quantities',
        store=True,
    )
    smp_qty_calculated = fields.Float(
        string='SMP Qty (Calculated)',
        digits=(12, 3),
        compute='_compute_standardization_quantities',
        store=True,
    )

    @api.depends('product_qty', 'aggregate_fat_percent', 'snf_after_water_percent', 'bom_id')
    def _compute_standardization_quantities(self):
        """Compute water and SMP quantities based on standardization formulas."""
        for production in self:
            if not production.is_milk_standardization or not production.bom_id:
                production.water_qty_calculated = 0.0
                production.smp_qty_calculated = 0.0
                continue

            quantities = production.bom_id._get_milk_standardization_quantities(
                aggregate_qty=production.product_qty,
                aggregate_fat=production.aggregate_fat_percent or 0,
                snf_after_water=production.snf_after_water_percent or 0,
            )
            production.water_qty_calculated = quantities.get('water_qty', 0.0)
            production.smp_qty_calculated = quantities.get('smp_qty', 0.0)

    def _update_standardization_quantities(self, standardization=None):
        """
        Update raw material move quantities based on standardization calculations.
        Called when creating MO from standardization or when measurements are updated.
        """
        self.ensure_one()

        if not self.is_milk_standardization:
            return

        std = standardization or self.standardization_id
        if not std:
            return

        # Update MO fields from standardization
        self.aggregate_fat_percent = std.aggregate_fat
        self.snf_after_water_percent = std.snf_after_water

        # Get component products
        water_product = std._get_water_product()
        smp_product = std._get_smp_product()

        # Update water move quantity
        water_move = self.move_raw_ids.filtered(
            lambda m: m.product_id == water_product and m.state not in ('done', 'cancel')
        )
        if water_move:
            water_move.write({'product_uom_qty': std.water_to_add or 0})

        # Update SMP move quantity (only if SNF has been measured)
        if std.snf_after_water > 0:
            smp_move = self.move_raw_ids.filtered(
                lambda m: m.product_id == smp_product and m.state not in ('done', 'cancel')
            )
            if smp_move:
                smp_move.write({'product_uom_qty': std.smp_to_add or 0})

    def action_confirm(self):
        """Override to update quantities for milk standardization MOs before confirmation."""
        for production in self:
            if production.is_milk_standardization and production.standardization_id:
                production._update_standardization_quantities()
        return super().action_confirm()

    def button_mark_done(self):
        """Override to update standardization record when MO is completed."""
        result = super().button_mark_done()

        for production in self:
            if production.is_milk_standardization and production.standardization_id:
                std = production.standardization_id
                # Update standardization state if all work orders are done
                if std.state != 'done':
                    # Get actual consumed quantities from moves
                    water_product = std._get_water_product()
                    smp_product = std._get_smp_product()

                    water_move = production.move_raw_ids.filtered(
                        lambda m: m.product_id == water_product and m.state == 'done'
                    )
                    smp_move = production.move_raw_ids.filtered(
                        lambda m: m.product_id == smp_product and m.state == 'done'
                    )

                    if water_move:
                        std.water_consumed = sum(water_move.mapped('quantity'))
                    if smp_move:
                        std.smp_consumed = sum(smp_move.mapped('quantity'))

                    std.state = 'done'
                    std.message_post(
                        body=_(
                            'Manufacturing Order %s completed. '
                            'Water consumed: %.3f L, SMP consumed: %.3f kg'
                        ) % (production.name, std.water_consumed, std.smp_consumed)
                    )

        return result

    def action_view_standardization(self):
        """Open the related standardization record."""
        self.ensure_one()
        if not self.standardization_id:
            raise UserError(_('No standardization record linked to this Manufacturing Order.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Milk Standardization'),
            'res_model': 'milk.standardization',
            'res_id': self.standardization_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
