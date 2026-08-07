# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class RfafPoReportWizard(models.TransientModel):
    _name = 'rfaf.po.report.wizard'
    _description = 'Purchase Order PDF Report Wizard'

    date = fields.Date(
        string='PO Date',
        default=fields.Date.today,
        required=True,
        help='Select the date for which you want to download the Purchase Order PDF.',
    )

    def action_print_report(self):
        self.ensure_one()
        orders = self.env['purchase.order'].search([
            ('date_order', '>=', fields.Datetime.to_datetime(self.date)),
            ('date_order', '<', fields.Datetime.to_datetime(self.date + __import__('datetime').timedelta(days=1))),
            ('state', 'in', ('purchase', 'done')),
        ])
        if not orders:
            raise UserError(
                _("No confirmed purchase orders found for date %s.")
                % self.date.strftime('%d-%m-%Y')
            )
        return self.env.ref(
            'royal_fresh_invoice_report.action_report_rfaf_purchase_order'
        ).with_context(date=self.date).report_action(
            orders, data={'date': fields.Date.to_string(self.date)}
        )
