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
    rfaf_previous_crats = fields.Integer(string='Previous Crats')
    rfaf_total_crats = fields.Integer(
        string='Total Crats',
        compute='_compute_crats_totals',
        store=True,
    )
    rfaf_return_crets = fields.Integer(string='Return Crets')
    rfaf_total_crats_bal = fields.Integer(
        string='Total Crats Balance',
        compute='_compute_crats_totals',
        store=True,
    )

    # ── Financial carry-over ──────────────────────────────────────────────
    rfaf_previous_balance = fields.Monetary(
        string='Previous Balance',
        currency_field='currency_id',
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
    @api.depends('invoice_line_ids.rfaf_crates')
    def _compute_bill_crats(self):
        for move in self:
            move.rfaf_bill_crats = sum(move.invoice_line_ids.mapped('rfaf_crates'))

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
