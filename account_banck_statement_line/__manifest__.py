# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    'name': 'Account Bank Statement Line - Full Edit',
    'summary': 'Permite editar todos los campos de líneas de extracto bancario',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'author': 'Xtendoo Software S.L.U.',
    'website': 'https://www.xtendoo.es',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_statement_base',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'wizard/edit_confirm_wizard_views.xml',
        'views/account_bank_statement_line_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
