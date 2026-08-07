# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ReportRfafPurchaseOrder(models.AbstractModel):
    _name = 'report.royal_fresh_invoice_report.report_rfaf_po_template'
    _description = 'Purchase Order Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        report_date = data.get('date') or self.env.context.get('date')

        if isinstance(report_date, str):
            report_date = fields.Date.from_string(report_date)
        elif not report_date:
            report_date = fields.Date.today()

        if docids:
            orders = self.env['purchase.order'].browse(docids)
        else:
            orders = self.env['purchase.order'].search([
                ('date_order', '>=', fields.Datetime.to_datetime(report_date)),
                ('date_order', '<', fields.Datetime.to_datetime(
                    report_date + __import__('datetime').timedelta(days=1)
                )),
                ('state', 'in', ('purchase', 'done')),
            ])

        lines = orders.mapped('order_line')
        products = lines.mapped('product_id').sorted(
            key=lambda p: p.name or p.display_name or ''
        )

        # Build supplier matrix
        supplier_groups = {}
        for line in lines:
            partner = line.order_id.partner_id
            if partner not in supplier_groups:
                supplier_groups[partner] = {
                    'partner': partner,
                    'product_qty': {prod.id: 0.0 for prod in products},
                    'total_qty': 0.0,
                }
            supplier_groups[partner]['product_qty'][line.product_id.id] += line.product_qty
            supplier_groups[partner]['total_qty'] += line.product_qty

        sorted_partners = sorted(supplier_groups.keys(), key=lambda p: p.name or '')
        supplier_matrix = []
        product_totals = {prod.id: 0.0 for prod in products}
        grand_total_qty = 0.0

        for idx, partner in enumerate(sorted_partners, start=1):
            sdata = supplier_groups[partner]
            row = {
                's_no': idx,
                'supplier_name': partner.name,
                'supplier_code': partner.ref or '',
                'product_qty': sdata['product_qty'],
                'total_qty': sdata['total_qty'],
            }
            supplier_matrix.append(row)
            for prod_id, qty in sdata['product_qty'].items():
                product_totals[prod_id] += qty
            grand_total_qty += sdata['total_qty']

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': orders,
            'report_date': report_date,
            'products': products,
            'supplier_matrix': supplier_matrix,
            'product_totals': product_totals,
            'grand_total_qty': grand_total_qty,
            'company': self.env.company,
        }
