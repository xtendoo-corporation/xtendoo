{
    'name': "Multi-Company Encapsulate Contacts",
    'summary': "Force company_id in Contacts and Settings.",
    'description': "Technical module to encapsulate Contacts and Settings within the active company.",
    'author': "Xtendoo",
    'category': 'Technical',
    'version': '19.0.1.0.0',
    'depends': ['base', 'contacts'],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'data': [
        'security/partner_rules.xml',
        'security/res_partner_bank.xml',
        'security/res_company_rules.xml',
        'views/res_partner_views.xml',
        'views/res_users_views.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'assets': {
        'web.assets_backend': [
            'xtendoo_encapsulate_companies_contacts/static/src/js/relational_utils_company_patch.js',
        ],
    },
}
