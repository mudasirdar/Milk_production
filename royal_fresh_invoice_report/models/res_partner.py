# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    rfaf_crate_line_ids = fields.One2many(
        'rfaf.customer.crate.line', 'partner_id', string='Crate Lines',
    )
    rfaf_crate_balance_ids = fields.One2many(
        'rfaf.customer.crate.balance', 'partner_id', string='Crate Balances',
    )


class RfafCustomerCrateBalance(models.Model):
    """Summary of crate balance per crate size per customer.
    Auto-computed from customer crate tracking lines."""
    _name = 'rfaf.customer.crate.balance'
    _description = 'Customer Crate Balance by Size'
    _order = 'crate_size'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade',
    )
    crate_size = fields.Float(
        string='Units per Crate', digits='Product Unit of Measure',
    )
    initial_balance = fields.Integer(
        string='Initial Balance',
        help='Manually entered opening balance from migration. '
             'This value is added to the tracked balance.',
    )
    total_issued = fields.Integer(string='Total Issued')
    total_returned = fields.Integer(string='Total Returned')
    balance = fields.Integer(
        string='Balance', compute='_compute_balance', store=True,
    )

    @api.depends('initial_balance', 'total_issued', 'total_returned')
    def _compute_balance(self):
        for rec in self:
            rec.balance = (rec.initial_balance or 0) + (rec.total_issued or 0) - (rec.total_returned or 0)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_previous_crate_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'initial_balance' in vals or 'crate_size' in vals:
            self._sync_previous_crate_lines()
        return res

    def _sync_previous_crate_lines(self):
        """Create/update 'Previous Balance' lines in crate tracking."""
        CustomerCrate = self.env['rfaf.customer.crate']
        CrateLine = self.env['rfaf.customer.crate.line']

        for rec in self:
            if not rec.partner_id or not rec.initial_balance:
                # Remove existing previous line if initial_balance is 0
                existing = CrateLine.search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('line_type', '=', 'previous'),
                    ('crate_size', '=', rec.crate_size),
                ], limit=1)
                if existing and not rec.initial_balance:
                    existing.unlink()
                continue

            # Find or create customer crate header
            header = CustomerCrate.search(
                [('partner_id', '=', rec.partner_id.id)], limit=1,
            )
            if not header:
                header = CustomerCrate.create({
                    'partner_id': rec.partner_id.id,
                })

            # Find existing previous line for this crate size
            existing = CrateLine.search([
                ('customer_crate_id', '=', header.id),
                ('line_type', '=', 'previous'),
                ('crate_size', '=', rec.crate_size),
            ], limit=1)

            vals = {
                'customer_crate_id': header.id,
                'line_type': 'previous',
                'crate_size': rec.crate_size,
                'crates_issued': rec.initial_balance,
                'crates_returned': 0,
                'date': fields.Date.today(),
            }
            if existing:
                existing.write(vals)
            else:
                CrateLine.create(vals)

    @api.model
    def _recompute_partner_balances(self, partner):
        """Recompute crate balance summary for a partner from their crate tracking lines.
        Preserves manually entered initial_balance for migration data."""
        CrateLine = self.env['rfaf.customer.crate.line']
        lines = CrateLine.search([
            ('partner_id', '=', partner.id),
            ('line_type', '=', 'so'),
        ])

        # Group by crate_size
        size_map = {}
        for line in lines:
            cs = line.crate_size
            if cs not in size_map:
                size_map[cs] = {'issued': 0, 'returned': 0}
            size_map[cs]['issued'] += line.crates_issued
            size_map[cs]['returned'] += line.crates_returned

        existing = self.search([('partner_id', '=', partner.id)])
        existing_map = {r.crate_size: r for r in existing}

        # Update existing or create new — balance auto-computes via _compute_balance
        for crate_size, totals in size_map.items():
            if crate_size in existing_map:
                existing_map[crate_size].write({
                    'total_issued': totals['issued'],
                    'total_returned': totals['returned'],
                })
                del existing_map[crate_size]
            else:
                self.create({
                    'partner_id': partner.id,
                    'crate_size': crate_size,
                    'total_issued': totals['issued'],
                    'total_returned': totals['returned'],
                })

        # Keep manually entered sizes that have no tracking lines — reset tracked values
        for rec in existing_map.values():
            rec.write({
                'total_issued': 0,
                'total_returned': 0,
            })
