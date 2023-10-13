# -*- coding: utf-8 -*-
{
    'name': 'Attachment Preview',
    'version': '16.0.4',
    'sequence': 1,
    'category': 'Services/Tools',
    'summary': """This module adds a new widget, "many2many_attachment_preview", which enables the user to view attachments without downloading them.""",
    'description': """ User can preview a document without downloading. """,
    'author': 'Odox Softhub',
    'price': 15,
    'currency': 'USD',
    'website': 'https://www.odoxsofthub.com',
    'support': 'support@odoxsofthub.com',
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'odx_m2m_attachment_preview/static/src/js/widget.js',
            'odx_m2m_attachment_preview/static/src/scss/style.scss',
            'odx_m2m_attachment_preview/static/src/xml/widget_view.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/thumbnail.gif'],
}
