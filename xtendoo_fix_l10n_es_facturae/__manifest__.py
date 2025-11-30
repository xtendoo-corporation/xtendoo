{
    'name': 'Xtendoo L10N ES Facturae Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Fix for empty elements in Facturae XML generation',
    'description': 'Removes empty elements from Facturae XML to comply with FACE validation.',
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'license': 'AGPL-3',
    'depends': [
        'l10n_es_facturae',
    ],
    'data': [
        'views/report_facturae.xml',
    ],
    'installable': True,
    'auto_install': False,
}

