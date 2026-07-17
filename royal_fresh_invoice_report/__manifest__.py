# -*- coding: utf-8 -*-
{
    'name': 'Royal Fresh Agro Farm - Invoice Report',
    'version': '19.0.1.0.0',
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
        - Signature of Receiver
    """,
    'author': 'Royal Fresh Agro Farm',
    'website': '',
    'depends': ['account', 'product', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'report/invoice_report.xml',
        'report/invoice_report_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
