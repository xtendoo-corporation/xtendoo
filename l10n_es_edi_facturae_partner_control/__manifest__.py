{
    'name': 'Facturae Partner Control',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Control Facturae generation based on partner settings',
    'description': """
        This module controls Facturae generation based on partner settings.
        The Facturae checkbox in the send wizard will only be enabled by default
        when ALL customers related to the invoices have the 'facturae' field set to True.
        Uses the existing 'facturae' field from l10n_es_facturae module.
    """,
    'author': 'Xtendoo',
    'website': 'https://xtendoo.es',
    'depends': [
        'l10n_es_edi_facturae',
        'l10n_es_facturae',
        'account',
    ],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
