{
    "name": "PoS Order To Sale Order picking delivered",
    "version": "17.0.1.0.0",
    "author": "GRAP,Odoo Community Association (OCA), Abraham Xtendoo",
    "category": "Point Of Sale",
    "license": "AGPL-3",
    "depends": ["point_of_sale", "sale_stock"],
    "maintainers": ["legalsylvain"],
    "development_status": "Production/Stable",
    "website": "https://github.com/OCA/pos",
    "data": ["views/view_res_config_settings.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_to_sale_order_picking_delivered/static/src/css/pos.scss",
            "pos_to_sale_order_picking_delivered/static/src/js/CreateOrderButton.esm.js",
            "pos_to_sale_order_picking_delivered/static/src/xml/CreateOrderButton.xml",
        ],
    },
    "installable": True,
}
