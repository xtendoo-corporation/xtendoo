# -*- coding: utf-8 -*-
{
    'name': "Xtendoo Initial Config",
    'summary': """
        Configuración inicial automática para instalaciones Odoo 18.0
    """,
    'version': "18.0.1.0.0",
    'author': "Manuel Calero, Xtendoo SLU",
    '"website': "https://xtendoo.es",
    'description': """
        Este módulo se encarga de realizar las configuraciones iniciales de Odoo 18.0:
        - Instalar el módulo de contactos
        - Instalar el idioma español (es_ES)
        - Cambiar a todos los usuarios y contactos al idioma español
        - Desinstalar el idioma inglés (en_US)
        - Instalar los módulos l10n_es_toponyms y web_responsive
        - Cambiar los datos de la compañía actual
        - Creación de cuentas de correo en OVH mediante su API
    """,
    'author': "Xtendoo",
    'website': "https://www.xtendoo.es",
    'category': 'Tools',
    'version': '18.0.1.0.0',
    'depends': [
        'base',
        'contacts',
        'stock',
        'l10n_es_toponyms',
    ],
    'data': [
        'data/security.xml',
        'data/company.xml',
        'views/xtendoo_config_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'wizards/ovh_email_creator_views.xml',
        'security/ir.model.access.csv',
        'data/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'external_dependencies': {
        'python': ['ovh'],
    },
}
