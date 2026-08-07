# -*- coding: utf-8 -*-
{
    'name': 'Royal Fresh Agro Farm - Invoice Report',
    'version': '19.0.2.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom Invoice Report for Royal Fresh Agro Farm (Dairy/Agro format with Crates, Route, Challan, Return, Leakage)',
    'description': """
        Custom invoice report replicating the Royal Fresh Agro Farm
        challan/delivery bill format:
        - Company header with address
        - Customer name + Route
        - Challan No. & Date
        - Product table: Crates | Particulars | Qty | Return | Leakage | Sold | Rate | Amount
        - Crates tracking section (Bill Crats, Previous, Total, Return, Balance)
        - Financial summary: Bill Amount, Previous Balance, Received, Total Balance
        - Return & Leakage deduction from total order amount
        - Return & Leakage tracking module with search filters
        - Signature of Receiver
    """,
    'author': 'Royal Fresh Agro Farm',
    'website': '',
    'depends': ['account', 'product', 'sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/rfaf_return_leakage_views.xml',
        'views/rfaf_customer_crate_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'report/invoice_report.xml',
        'report/invoice_report_template.xml',
        'report/rfaf_po_report_views.xml',
        'report/rfaf_po_report_template.xml',
        'wizard/rfaf_po_report_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
