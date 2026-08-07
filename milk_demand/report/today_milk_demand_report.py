# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ReportTodayMilkDemand(models.AbstractModel):
    _name = 'report.milk_demand.report_today_milk_demand_template'
    _description = 'Today Milk Demand Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        report_date = data.get('date') or self.env.context.get('date')

        if docids:
            demands = self.env['milk.demand'].browse(docids)
            if not report_date and demands:
                report_date = demands[0].demand_date
        else:
            if not report_date:
                report_date = fields.Date.today()
            if isinstance(report_date, str):
                report_date = fields.Date.from_string(report_date)
            demands = self.env['milk.demand'].search([
                ('demand_date', '=', report_date),
                ('state', '!=', 'cancelled')
            ])

        if isinstance(report_date, str):
            report_date = fields.Date.from_string(report_date)
        elif not report_date:
            report_date = fields.Date.today()

        lines = demands.mapped('line_ids')
        products = lines.mapped('product_id').sorted(key=lambda p: p.name or p.display_name or '')

        customer_groups = {}
        for line in lines:
            partner = line.demand_id.partner_id
            if not partner:
                continue
            if partner not in customer_groups:
                customer_groups[partner] = {
                    'partner': partner,
                    'demands': self.env['milk.demand'],
                    'product_qty': {prod.id: 0.0 for prod in products},
                    'product_crates': {prod.id: 0 for prod in products},
                    'total_qty': 0.0,
                    'total_crates': 0,
                }
            customer_groups[partner]['demands'] |= line.demand_id
            customer_groups[partner]['product_qty'][line.product_id.id] += line.quantity
            customer_groups[partner]['product_crates'][line.product_id.id] += line.crates
            customer_groups[partner]['total_qty'] += line.quantity
            customer_groups[partner]['total_crates'] += line.crates

        sorted_partners = sorted(customer_groups.keys(), key=lambda p: p.name or '')
        customer_matrix = []
        product_totals = {prod.id: 0.0 for prod in products}
        product_crate_totals = {prod.id: 0 for prod in products}
        grand_total_qty = 0.0
        grand_total_crates = 0

        for idx, partner in enumerate(sorted_partners, start=1):
            cdata = customer_groups[partner]
            demand_refs = ', '.join(cdata['demands'].mapped('name'))
            row = {
                's_no': idx,
                'customer_name': partner.name,
                'customer_code': partner.ref or '',
                'demand_refs': demand_refs,
                'product_qty': cdata['product_qty'],
                'product_crates': cdata['product_crates'],
                'total_qty': cdata['total_qty'],
                'total_crates': cdata['total_crates'],
            }
            customer_matrix.append(row)

            for prod_id, qty in cdata['product_qty'].items():
                product_totals[prod_id] += qty
            for prod_id, crates in cdata['product_crates'].items():
                product_crate_totals[prod_id] += crates
            grand_total_qty += cdata['total_qty']
            grand_total_crates += cdata['total_crates']

        return {
            'doc_ids': docids,
            'doc_model': 'milk.demand',
            'docs': demands,
            'today_date': report_date,
            'products': products,
            'customer_matrix': customer_matrix,
            'product_totals': product_totals,
            'product_crate_totals': product_crate_totals,
            'grand_total_qty': grand_total_qty,
            'grand_total_crates': grand_total_crates,
            'company': self.env.company,
        }
