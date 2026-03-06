{
    'name': 'Paneer Batti Weight',
    'version': '19.0.1.0.0',
    'summary': 'Tare weight deduction for Paneer Batti containers in Sale Orders',
    'description': """
Paneer Batti Weight Deduction
==============================
When selling Paneer Batti, the paneer comes packed inside heavy containers (battis).
This module lets you enter:
  - Gross Weight (total weight including battis)
  - Number of Battis
  - Weight per Batti (auto-filled from product, overridable)

And automatically calculates:
  Net Paneer Weight = Gross Weight - (Number of Battis x Batti Weight)

The net weight is automatically set as the invoiced quantity on the sale order line.

These fields ONLY appear for the Paneer Batti product (identified by internal reference = 'paneer_batti').
All other products are completely unaffected.

Compatible with: Odoo 17, 18, 19 — Community & Enterprise
    """,
    'author': 'GoExalt System LLP',
    'website': 'www.exaltssytem.com',
    'category': 'Sales/Sales',
    'depends': ['sale', 'product'],
    'data': [
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
