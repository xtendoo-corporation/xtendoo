# Copyright 2004-2010 OpenERP SA (<http://www.openerp.com>)
# Copyright 2011-2015 Serpent Consulting Services Pvt. Ltd.
# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2019 Open Source Integrators
# Copyright 2020 Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Xtendoo Web Widget Digitized Signature',
    'version': '13.0.1.0.0',
    'author': 'Xtendoo, '
              'Serpent Consulting Services Pvt. Ltd., '
              'Agile Business Group, '
              'Tecnativa, '
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/web',
    'license': 'AGPL-3',
    'category': 'Web',
    'depends': [
        'web',
        'mail',
        'stock',
    ],
    'data': [
        'views/web_navigator_geolocation_view.xml',
        'views/res_users_view.xml',
        'views/stock_picking_view.xml',
    ],
    'qweb': [
        'static/src/xml/navigator_geolocation.xml',
    ],
    'installable': True,
    'development_status': 'Production/Stable',
    'maintainers': [
        'mgosai',
        'javier lagares',
        'manuel calero'
    ],
}
