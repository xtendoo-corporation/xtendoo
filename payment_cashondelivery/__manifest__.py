{
    'name': 'Payment Provider: Contrarreembolso',
    'version': '17.0.0.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A payment provider for cashondelivery flows like contrarreembolsos.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'author': 'Guillermo Bárcena López',
    'data': [
        'views/payment_cashondelivery_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',  # Depends on `payment_method_cashondelivery`.
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_cashondelivery/static/src/js/post_processing.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3',
    'installable': True,
}
