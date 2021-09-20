# -*- coding: utf-8 -*-
{
    'name': "Number of Leads",
    'description': 'Show number of leads at top of every column in CRM.',
    'author': "Iván Ramos Jiménez",
    'website': "https://ivan.ramos.name",
    'category': 'Lead Automation',
    'version': '12.0.1.0.0',
    'depends': ['crm','web'],
    'data': [
        'views/templates.xml',
    ],
    'qweb': [
        'static/src/xml/custom_header.xml',
    ],
    'auto_install': False,
    'installable': True,
}