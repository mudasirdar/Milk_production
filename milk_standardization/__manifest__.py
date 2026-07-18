{
    'name': 'Milk Standardization',
    'version': '19.0.2.0.0',
    'summary': 'Dairy milk fat & SNF standardization using water and SMP with MRP integration',
    'description': """
        This module helps dairy companies standardize aggregate milk to meet
        government guidelines:
        - Fat: 3% (add water)
        - SNF: 9.5% (add SMP / Skimmed Milk Powder)

        Features:
        - Auto-create standardization from purchase receipts
        - Track water and SMP consumption in inventory
        - Automatic stock moves for materials used
        - Full MRP Integration with Manufacturing Orders
        - Work Orders for Water Addition and SMP Addition steps
        - BOM-based manufacturing with dynamic quantity calculations

        Multi-Output Category Support:
        - Split raw milk into multiple output categories
        - Different SNF targets per category (e.g., 9.5% for milk, 10.5% for curd)
        - Configure custom output products per category
        - Independent water and SMP calculations per line
        - Track production of multiple milk products from single batch
    """,
    'author': 'Your Company',
    'category': 'Manufacturing',
    'depends': ['stock', 'mrp', 'mail', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/mrp_workcenter_data.xml',
        'views/milk_output_category_views.xml',
        'views/milk_standardization_line_views.xml',
        'views/milk_standardization_views.xml',
        'views/milk_standardization_menu.xml',
        'views/stock_picking_views.xml',
        'views/purchase_views.xml',
        'views/res_config_settings_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'milk_standardization/static/src/css/milk_standardization.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
