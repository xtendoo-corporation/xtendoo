# Copyright 2021 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Web Widget Navigator Geolocation',
    'version': '13.0.1.0.0',
    'author': 'Xtendoo, '
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/web',
    'license': 'AGPL-3',
    'category': 'Web',
    'depends': [
        'web',
        'mail',
    ],
    'data': [
        'views/web_navigator_geolocation_view.xml',
        'views/res_users_view.xml',
    ],
    'qweb': [
        'static/src/xml/navigator_geolocation.xml',
    ],
    'installable': True,
    'development_status': 'Production/Stable',
    'maintainers': ['Xtendoo - Manuel Calero'],
}
