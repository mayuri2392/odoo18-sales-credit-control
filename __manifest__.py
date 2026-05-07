{
    'name': 'Sales Credit Control',
    'version': '1.1.0',
    'summary': 'Credit control, approval workflows, and below-cost governance for Sales Orders',
    'depends': ['sale', 'sales_team', 'stock', 'account', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        # Configuration
        'views/credit_tier_view.xml',

        # Views
        'views/res_config_settings_view.xml',
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',
        'views/res_partner_kanban_badge.xml',

        # Wizards
        'views/approval_reason_views.xml',
        'views/credit_limit_request_wizard_view.xml',
        'views/credit_limit_reject_wizard_view.xml',
        'views/below_cost_reject_wizard_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
