# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MilkDemandReportWizard(models.TransientModel):
    _name = 'milk.demand.report.wizard'
    _description = 'Milk Demand PDF Report Wizard'

    date = fields.Date(
        string='Demand Date',
        default=fields.Date.today,
        required=True,
        help='Select the date for which you want to download the demand PDF.'
    )

    def action_print_report(self):
        self.ensure_one()
        report_date = self.date
        demands = self.env['milk.demand'].search([
            ('demand_date', '=', report_date),
            ('state', '!=', 'cancelled')
        ])

        if not demands:
            raise UserError(_("No active milk demands found for date %s.") % report_date.strftime('%d-%m-%Y'))

        return self.env.ref('milk_demand.action_report_today_milk_demand').with_context(
            date=report_date
        ).report_action(demands, data={'date': fields.Date.to_string(report_date)})
