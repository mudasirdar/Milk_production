# -*- coding: utf-8 -*-
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        self._sync_customer_crate_records()
        return res

    def _sync_customer_crate_records(self):
        """Auto-create/update customer crate tracking from confirmed SO lines."""
        CustomerCrate = self.env['rfaf.customer.crate']
        CrateLine = self.env['rfaf.customer.crate.line']

        for order in self:
            crate_lines = order.order_line.filtered(
                lambda l: l.rfaf_crates and l.product_id.rfaf_use_crates
            )
            if not crate_lines:
                continue

            # Find or create the customer crate header
            header = CustomerCrate.search(
                [('partner_id', '=', order.partner_id.id)], limit=1,
            )
            if not header:
                header = CustomerCrate.create({
                    'partner_id': order.partner_id.id,
                })

            for sol in crate_lines:
                existing = CrateLine.search([
                    ('sale_order_line_id', '=', sol.id),
                ], limit=1)
                vals = {
                    'customer_crate_id': header.id,
                    'sale_order_id': order.id,
                    'sale_order_line_id': sol.id,
                    'crate_size': sol.product_id.rfaf_units_per_crate or 0.0,
                    'date': order.date_order.date() if order.date_order else False,
                    'crates_issued': sol.rfaf_crates,
                }
                if existing:
                    existing.write(vals)
                else:
                    CrateLine.create(vals)

            # Recompute partner crate balance summary
            self.env['rfaf.customer.crate.balance']._recompute_partner_balances(order.partner_id)
