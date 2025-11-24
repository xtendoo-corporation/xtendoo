# -*- coding: utf-8 -*-
{
    'name': "Xtendoo Update Year",
    'summary': """
        Actualización diaria de la fecha de expiración de la base de datos
    """,
    'description': """
        Este módulo crea un trabajo programado (CRON) que actualiza
        diariamente a la 1:00 de la madrugada la fecha de expiración
        de la base de datos, estableciéndola al valor '2050-12-30 00:00:00'
    """,
    'author': "Xtendoo",
    'website': "https://www.xtendoo.es",
    'license': 'AGPL-3',
    'category': 'Tools',
    'version': '18.0.1.0',
    'depends': ['base'],
    'data': [
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
