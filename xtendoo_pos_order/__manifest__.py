# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Xtendoo POS Order Backend",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Permite crear y gestionar órdenes POS desde el backend",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_config_view.xml",
        "views/pos_order_view.xml",
    ],
    "demo": [
        "demo/pos_config_demo.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}

