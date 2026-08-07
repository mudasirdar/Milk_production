# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # ── Per-line dairy fields ─────────────────────────────────────────────
    rfaf_crates = fields.Integer(
        string='Crates',
        default=0,
        help='Number of crates dispatched for this product',
    )
    rfaf_dispatched_qty = fields.Float(
        string='Dispatched Qty',
        digits='Product Unit of Measure',
        default=0.0,
        help='Original quantity dispatched (before return/leakage)',
    )
    rfaf_return_qty = fields.Float(
        string='Return',
        digits='Product Unit of Measure',
        default=0.0,
        help='Quantity returned by the customer',
    )
    rfaf_leakage_qty = fields.Float(
        string='Leakage',
        digits='Product Unit of Measure',
        default=0.0,
        help='Quantity lost due to leakage / damage',
    )
    rfaf_sold_qty = fields.Float(
        string='Sold',
        digits='Product Unit of Measure',
        compute='_compute_sold_qty',
        store=True,
        help='Actual quantity sold = Dispatched − Return − Leakage',
    )

    @api.depends('rfaf_dispatched_qty', 'rfaf_return_qty', 'rfaf_leakage_qty')
    def _compute_sold_qty(self):
        for line in self:
            line.rfaf_sold_qty = max(
                (line.rfaf_dispatched_qty or 0.0)
                - (line.rfaf_return_qty or 0.0)
                - (line.rfaf_leakage_qty or 0.0),
                0.0,
            )

    @api.onchange('rfaf_crates')
    def _onchange_rfaf_crates(self):
        """Compute quantity from crates for products with crates enabled."""
        for line in self:
            if line.product_id and line.product_id.rfaf_use_crates and line.rfaf_crates:
                units_per_crate = line.product_id.rfaf_units_per_crate or 12.0
                qty = line.rfaf_crates * units_per_crate
                line.rfaf_dispatched_qty = qty
                line.quantity = qty

    @api.onchange('rfaf_dispatched_qty')
    def _onchange_dispatched_qty(self):
        """When dispatched qty is entered manually, set quantity."""
        for line in self:
            line.quantity = max(
                (line.rfaf_dispatched_qty or 0.0)
                - (line.rfaf_return_qty or 0.0)
                - (line.rfaf_leakage_qty or 0.0),
                0.0,
            )

    @api.onchange('rfaf_return_qty', 'rfaf_leakage_qty')
    def _onchange_return_leakage(self):
        """Reduce quantity when return or leakage is entered."""
        for line in self:
            if line.rfaf_dispatched_qty:
                line.quantity = max(
                    line.rfaf_dispatched_qty
                    - (line.rfaf_return_qty or 0.0)
                    - (line.rfaf_leakage_qty or 0.0),
                    0.0,
                )

    @api.onchange('quantity')
    def _onchange_quantity_sync_dispatched(self):
        """Sync dispatched qty when user sets quantity directly."""
        for line in self:
            if not line.rfaf_return_qty and not line.rfaf_leakage_qty:
                line.rfaf_dispatched_qty = line.quantity

    # ── Auto-sync Return & Leakage tracking records ──────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'rfaf_dispatched_qty' not in vals:
                vals['rfaf_dispatched_qty'] = vals.get('quantity', 0.0)
        lines = super().create(vals_list)
        lines._sync_return_leakage_records()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('rfaf_return_qty', 'rfaf_leakage_qty', 'price_unit', 'quantity')):
            self._sync_return_leakage_records()
        return res

    def _sync_return_leakage_records(self):
        """Create / update / delete rfaf.return.leakage records (header + lines)."""
        ReturnLeakage = self.env['rfaf.return.leakage']
        ReturnLeakageLine = self.env['rfaf.return.leakage.line']

        # Group lines by invoice
        invoice_lines = {}
        for line in self:
            if line.display_type != 'product':
                continue
            invoice_lines.setdefault(line.move_id, []).append(line)

        for move, lines in invoice_lines.items():
            # Find or create the header record for this invoice
            header = ReturnLeakage.search(
                [('invoice_id', '=', move.id)], limit=1,
            )
            has_any = any(
                l.rfaf_return_qty or l.rfaf_leakage_qty for l in lines
            )

            if not has_any and not header:
                continue

            if has_any and not header:
                header = ReturnLeakage.create({'invoice_id': move.id})

            for line in lines:
                existing_line = ReturnLeakageLine.search(
                    [('invoice_line_id', '=', line.id)], limit=1,
                )
                if line.rfaf_return_qty or line.rfaf_leakage_qty:
                    vals = {
                        'return_leakage_id': header.id,
                        'invoice_line_id': line.id,
                        'dispatched_qty': line.rfaf_dispatched_qty or line.quantity or 0.0,
                        'return_qty': line.rfaf_return_qty or 0.0,
                        'leakage_qty': line.rfaf_leakage_qty or 0.0,
                        'price_unit': line.price_unit or 0.0,
                    }
                    if existing_line:
                        existing_line.write(vals)
                    else:
                        ReturnLeakageLine.create(vals)
                elif existing_line:
                    existing_line.unlink()

            # If header has no more lines, delete it
            if header and not header.line_ids:
                header.unlink()
