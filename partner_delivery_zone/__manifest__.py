# Copyright 2018 Tecnativa - Sergio Teruel
# Copyright 2020 Xtendoo - Manuel Calero Solís
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Partner Delivery Zone by Xtendoo',
    'summary': 'Create a Delivery Zones and customers in sales orders',
    'version': '12.0.1.0.0',
    'development_status': 'Beta',
    'category': 'Delivery',
    'website': 'https://www.xtendoo.es',
    'author': 'Xtendoo',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'depends': [
        'sale_stock',
    ],
    'data': [
        'data/partner_sequence.xml',

        'security/ir.model.access.csv',

        'views/partner_delivery_zone_view.xml',
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',
        'views/stock_picking_view.xml',
        'views/account_payment_view.xml',
        'views/account_invoice_view.xml',

        'views/report_shipping.xml',

        'reports/report_sale_delivery_zone.xml',

        'wizards/wizards_select_visits_routes.xml',
        'wizards/wizards_report_sale_delivery_zone.xml',
    ],
}

