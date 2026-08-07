# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RfafInvoiceCrateReturn(models.Model):
    _name = 'rfaf.invoice.crate.return'
    _description = 'Invoice Crate Return by Size'
    _order = 'date desc, id desc'

    move_id = fields.Many2one(
        'account.move', string='Invoice', required=True, ondelete='cascade',
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        related='move_id.partner_id', store=True,
    )
    date = fields.Date(
        string='Date', related='move_id.invoice_date', store=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        compute='_compute_sale_order', store=True,
    )
    crate_size = fields.Float(
        string='Units per Crate',
        digits='Product Unit of Measure',
        readonly=True,
    )
    previous_balance = fields.Integer(
        string='Previous', compute='_compute_previous_balance',
    )
    crates_issued = fields.Integer(
        string='Issued', readonly=True,
    )
    crates_returned = fields.Integer(
        string='Returned',
    )

    @api.depends('move_id.invoice_line_ids.sale_line_ids')
    def _compute_sale_order(self):
        for rec in self:
            sale_orders = rec.move_id.invoice_line_ids.sale_line_ids.mapped('order_id')
            rec.sale_order_id = sale_orders[:1].id if sale_orders else False

    @api.depends('partner_id', 'crate_size')
    def _compute_previous_balance(self):
        """Get the customer's current crate balance for this crate size."""
        Balance = self.env['rfaf.customer.crate.balance']
        for rec in self:
            if rec.partner_id and rec.crate_size:
                bal = Balance.search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('crate_size', '=', rec.crate_size),
                ], limit=1)
                rec.previous_balance = bal.balance if bal else 0
            else:
                rec.previous_balance = 0

    def write(self, vals):
        res = super().write(vals)
        if 'crates_returned' in vals:
            self._sync_to_customer_crate()
        return res

    def _sync_to_customer_crate(self):
        """Sync return crates to existing customer crate tracking lines."""
        CrateLine = self.env['rfaf.customer.crate.line']

        for rec in self:
            move = rec.move_id
            if not move.partner_id:
                continue

            # Find the SO linked to this invoice
            sale_orders = move.invoice_line_ids.sale_line_ids.mapped('order_id')

            # Find existing customer crate lines from those SOs with matching crate size
            domain = [
                ('sale_order_id', 'in', sale_orders.ids),
                ('crate_size', '=', rec.crate_size),
            ]
            crate_lines = CrateLine.search(domain)

            if not crate_lines:
                continue

            # Distribute returned crates across matching lines (proportional to issued)
            total_issued = sum(crate_lines.mapped('crates_issued'))
            remaining = rec.crates_returned

            for i, cl in enumerate(crate_lines):
                if i == len(crate_lines) - 1:
                    cl.crates_returned = remaining
                else:
                    share = int(rec.crates_returned * cl.crates_issued / total_issued) if total_issued else 0
                    cl.crates_returned = share
                    remaining -= share

            # Recompute partner crate balance summary
            self.env['rfaf.customer.crate.balance']._recompute_partner_balances(move.partner_id)
