from odoo import models, fields, api

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# Set this to the exact Internal Reference of your Paneer Batti product.
# Go to: Product → General Information → Internal Reference
# ─────────────────────────────────────────────────────────────────────────────
PANEER_BATTI_INTERNAL_REF = 'paneer_batti'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ── Flag: is this line the Paneer Batti product? ──────────────────────────
    is_paneer_batti = fields.Boolean(
        string='Is Paneer Batti',
        compute='_compute_is_paneer_batti',
        store=True,
    )

    # ── Batti weight input fields ─────────────────────────────────────────────
    gross_weight = fields.Float(
        string='Gross Weight (kg)',
        digits=(10, 3),
        default=0.0,
        help='Total weight including all batti containers.',
    )
    num_battis = fields.Integer(
        string='Number of Battis',
        default=0,
        help='Number of batti containers included in the gross weight.',
    )
    batti_weight = fields.Float(
        string='Batti Weight (kg)',
        digits=(10, 3),
        default=0.0,
        help='Weight of one batti in kg. Auto-filled from product but can be overridden.',
    )

    # ── Net weight: auto-computed, drives invoiced qty ────────────────────────
    net_weight = fields.Float(
        string='Net Paneer Weight (kg)',
        digits=(10, 3),
        compute='_compute_net_weight',
        store=True,
        readonly=True,
        help='Net Paneer Weight = Gross Weight − (Number of Battis × Batti Weight).',
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE METHODS
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends('product_id')
    def _compute_is_paneer_batti(self):
        """True only when the product's internal reference matches PANEER_BATTI_INTERNAL_REF."""
        for line in self:
            line.is_paneer_batti = bool(
                line.product_id
                and line.product_id.default_code == PANEER_BATTI_INTERNAL_REF
            )

    @api.depends('is_paneer_batti', 'gross_weight', 'num_battis', 'batti_weight')
    def _compute_net_weight(self):
        """
        Net Paneer Weight = Gross Weight − (Number of Battis × Batti Weight)
        Result is floored at 0.0 to prevent negative quantities.
        Only calculated for Paneer Batti lines; other lines get 0.0.
        """
        for line in self:
            if line.is_paneer_batti:
                tare = (line.num_battis or 0) * (line.batti_weight or 0.0)
                line.net_weight = max(round((line.gross_weight or 0.0) - tare, 3), 0.0)
            else:
                line.net_weight = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # ONCHANGE METHODS
    # ─────────────────────────────────────────────────────────────────────────

    @api.onchange('product_id')
    def _onchange_product_batti_fill(self):
        """
        When a product is selected on the order line:
        - If it is Paneer Batti  → auto-fill batti_weight from the product's tare setting.
        - If it is anything else → clear all batti-related fields so no stale data remains.
        """
        if (
            self.product_id
            and self.product_id.default_code == PANEER_BATTI_INTERNAL_REF
        ):
            self.batti_weight = self.product_id.tare_weight_per_batti or 0.4
        else:
            self.gross_weight = 0.0
            self.num_battis = 0
            self.batti_weight = 0.0

    @api.onchange('gross_weight', 'num_battis', 'batti_weight')
    def _onchange_batti_fields_sync_qty(self):
        """
        Whenever the gross weight or batti count/weight changes, recalculate the
        net paneer weight and push it to product_uom_qty so the invoice is
        correctly generated for the net weight only.
        """
        if self.is_paneer_batti:
            tare = (self.num_battis or 0) * (self.batti_weight or 0.0)
            net = max(round((self.gross_weight or 0.0) - tare, 3), 0.0)
            self.net_weight = net
            if net > 0:
                self.product_uom_qty = net
