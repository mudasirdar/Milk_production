{
    'name': 'Textbee SMS Integration',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Send SMS via Textbee API from Sale and Purchase Orders',
    'description': 'Integrates Textbee SMS API with Odoo for sending SMS notifications from Sale and Purchase Orders.',
    'author': 'Custom',
    'depends': ['sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
