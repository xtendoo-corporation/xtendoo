{
    'name': 'Firma Digital PDF',
    'version': '18.0.0.1',
    'category': 'Tools',
    'summary': 'Firma digital de documentos PDF con certificados',
    'author': 'Tu Nombre',
    'depends': [
        'base',
        'certificate',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizards/sign_pdf_wizard.xml',
    ],
    'external_dependencies': {
        'python': ['endesive', 'PyPDF2'],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
