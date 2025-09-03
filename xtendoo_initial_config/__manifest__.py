# -*- coding: utf-8 -*-
{
    'name': "Xtendoo Initial Config",
    'summary': """
        Configuración inicial automática para instalaciones Odoo 18.0
    """,
    'version': "18.0.1.0.0",
    'author': "Manuel Calero, Xtendoo SLU",
    'website': "https://xtendoo.es",
    'license': 'LGPL-3',
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
    'category': 'Tools',
    'depends': [
        'base',
        'contacts',
        'stock',
        'sale',
        'purchase',
        'l10n_es_toponyms',
    ],
    'data': [
        'data/company.xml',
        'wizards/ovh_email_creator_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
