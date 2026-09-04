# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Agro / Dairy specific fields ──────────────────────────────────────
    rfaf_challan_no = fields.Char(
        string='Challan No.',
        help='Challan / delivery note number (e.g. Ch No. 2715)',
    )
    rfaf_route = fields.Char(
        string='Route',
        help='Delivery route name (e.g. Wahipora Route)',
    )
    rfaf_serial_no = fields.Char(
        string='Bill No.',
        help='Sequential bill number printed on the physical challan (e.g. 2023)',
    )

    # ── Crates tracking ───────────────────────────────────────────────────
    rfaf_bill_crats = fields.Integer(
        string='Bill Crats',
        compute='_compute_bill_crats',
        store=True,
        help='Total crates from all invoice lines',
    )
    rfaf_previous_crats = fields.Integer(
        string='Previous Crats',
        compute='_compute_previous_crats',
        store=True,
    )
    rfaf_total_crats = fields.Integer(
        string='Total Crats',
        compute='_compute_crats_totals',
        store=True,
    )
    rfaf_crate_return_ids = fields.One2many(
        'rfaf.invoice.crate.return', 'move_id', string='Crate Returns',
    )
    rfaf_return_crets = fields.Integer(
        string='Return Crets',
        compute='_compute_return_crets',
        store=True,
    )
    rfaf_total_crats_bal = fields.Integer(
        string='Total Crats Balance',
        compute='_compute_crats_totals',
        store=True,
    )

    # ── Financial carry-over ──────────────────────────────────────────────
    rfaf_previous_balance = fields.Monetary(
        string='Previous Balance',
        compute='_compute_previous_balance',
        currency_field='currency_id',
        help='Automatically fetched from the customer accounting balance (total receivable due), excluding the current invoice.',
    )
    rfaf_received_cash = fields.Monetary(
        string='Received Cash / Chq. / Transfer',
        currency_field='currency_id',
    )
    rfaf_total_balance = fields.Monetary(
        string='Total Balance',
        compute='_compute_total_balance',
        store=True,
        currency_field='currency_id',
    )

    # ── Computed fields ───────────────────────────────────────────────────
    @api.depends('partner_id', 'currency_id', 'invoice_date')
    def _compute_previous_balance(self):
        for move in self:
            balance = 0.0
            if move.partner_id and move.move_type in ('out_invoice', 'out_refund'):
                # Use invoice_date as the cutoff so the "previous" balance
                # reflects what was outstanding before this invoice's date.
                # Fall back to today when the date is not yet set (draft state).
                cutoff_date = move.invoice_date or fields.Date.context_today(move)

                domain = [
                    ('partner_id', '=', move.partner_id.commercial_partner_id.id),
                    # Only customer-receivable lines; do NOT mix in liability_payable
                    # (vendor payable) lines as they have opposite sign meaning.
                    ('account_id.account_type', '=', 'asset_receivable'),
                    ('parent_state', '=', 'posted'),
                    ('reconciled', '=', False),
                    # Only lines whose move date is strictly before this invoice
                    ('date', '<', cutoff_date),
                ]
                # Exclude current invoice's own lines (safety guard for same-date)
                if move.id:
                    domain.append(('move_id', '!=', move.id))
                lines = self.env['account.move.line'].search(domain)
                # amount_residual is positive for unpaid debit (invoice) lines
                # and negative for unapplied credit (refund/payment) lines —
                # summing gives the net outstanding balance correctly.
                balance = sum(lines.mapped('amount_residual'))
            move.rfaf_previous_balance = balance

    @api.depends('partner_id')
    def _compute_previous_crats(self):
        Balance = self.env['rfaf.customer.crate.balance']
        for move in self:
            if move.partner_id and move.move_type in ('out_invoice', 'out_refund'):
                balances = Balance.search([('partner_id', '=', move.partner_id.id)])
                move.rfaf_previous_crats = sum(balances.mapped('balance'))
            else:
                move.rfaf_previous_crats = 0

    @api.depends('invoice_line_ids.rfaf_crates', 'invoice_line_ids.product_id')
    def _compute_bill_crats(self):
        for move in self:
            move.rfaf_bill_crats = sum(move.invoice_line_ids.mapped('rfaf_crates'))

    @api.depends('rfaf_crate_return_ids.crates_returned')
    def _compute_return_crets(self):
        for move in self:
            move.rfaf_return_crets = sum(
                move.rfaf_crate_return_ids.mapped('crates_returned')
            )

    @api.depends('rfaf_bill_crats', 'rfaf_previous_crats', 'rfaf_return_crets')
    def _compute_crats_totals(self):
        for move in self:
            total = (move.rfaf_bill_crats or 0) + (move.rfaf_previous_crats or 0)
            move.rfaf_total_crats = total
            move.rfaf_total_crats_bal = total - (move.rfaf_return_crets or 0)

    @api.depends('amount_total', 'rfaf_previous_balance', 'rfaf_received_cash')
    def _compute_total_balance(self):
        for move in self:
            move.rfaf_total_balance = (
                (move.amount_total or 0.0)
                + (move.rfaf_previous_balance or 0.0)
                - (move.rfaf_received_cash or 0.0)
            )

    # ── Sync crate return lines on save ───────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._populate_crate_return_lines()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if 'invoice_line_ids' in vals:
            self._populate_crate_return_lines()
        return res

    def _populate_crate_return_lines(self):
        """Auto-populate crate return lines grouped by crate size from invoice products."""
        CrateReturn = self.env['rfaf.invoice.crate.return']
        for move in self:
            if not move.id or move.move_type not in ('out_invoice', 'out_refund'):
                continue

            # Group invoice lines by crate size
            size_map = {}
            for line in move.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product'
                and l.product_id.rfaf_use_crates
                and l.rfaf_crates
            ):
                crate_size = line.product_id.rfaf_units_per_crate or 0.0
                if crate_size not in size_map:
                    size_map[crate_size] = 0
                size_map[crate_size] += line.rfaf_crates

            existing = CrateReturn.search([('move_id', '=', move.id)])
            existing_map = {r.crate_size: r for r in existing}

            # Update or create lines for active crate sizes
            for crate_size, issued in size_map.items():
                if crate_size in existing_map:
                    existing_map[crate_size].write({'crates_issued': issued})
                    del existing_map[crate_size]
                else:
                    CrateReturn.create({
                        'move_id': move.id,
                        'crate_size': crate_size,
                        'crates_issued': issued,
                        'crates_returned': 0,
                    })

            # Remove lines for crate sizes no longer in the invoice
            for leftover in existing_map.values():
                leftover.unlink()
