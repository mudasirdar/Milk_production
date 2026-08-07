{
    'name': 'Milk Product Demand',
    'version': '19.0.1.0.0',
    'summary': 'Manage daily demand for milk products from customers',
    'description': """
        This module helps manage customer demand for milk products.

        Features:
        - Record daily demand from customers
        - Customer-specific demand tracking
        - Convert demand to Sales Orders
        - Edit demand before conversion
        - Track demand history
    """,
    'author': 'Your Company',
    'category': 'Sales',
    'depends': ['sale', 'product', 'royal_fresh_invoice_report'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'wizard/milk_demand_report_wizard_views.xml',
        'report/today_milk_demand_report_views.xml',
        'report/today_milk_demand_report_template.xml',
        'views/milk_demand_views.xml',
        'views/milk_demand_menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
