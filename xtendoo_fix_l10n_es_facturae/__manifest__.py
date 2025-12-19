{
    'name': 'Xtendoo L10N ES Facturae Fix',
    'version': '18.0.2.0.0',
    'category': 'Accounting',
    'summary': 'Fix for empty elements in Facturae XML generation',
    'description': '''
        Removes empty elements from Facturae XML to comply with FACE validation.

        This module extends report.report_xml.abstract to automatically apply
        cleanup_xml_node() to all XML reports, ensuring that:
        - Empty XML elements are removed
        - Whitespace is properly cleaned
        - XML structure is optimized

        This approach applies the fix globally to all XML reports, not just
        Facturae templates.
    ''',
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.com',
    'license': 'AGPL-3',
    'depends': [
        'report_xml',
        'l10n_es_facturae',
        'l10n_es_edi_facturae',
    ],
    'installable': True,
    'auto_install': False,
}
