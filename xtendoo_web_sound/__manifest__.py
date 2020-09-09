# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Xtendoo Web Sound',
    'summary': """
        Send sounds messages to user""",
    'version': '12.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Xtendoo,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/web',
    'depends': [
        'web',
        'bus',
        'base',
    ],
    'data': [
        'views/res_users_demo.xml',
        'views/web_sound_assets.xml',
    ],
    'installable': True,
    'qweb': [
        'static/src/xml/web_sound_widget.xml',
    ],    
}
