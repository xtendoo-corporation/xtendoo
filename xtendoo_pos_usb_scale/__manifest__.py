# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "POS USB Scale",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "summary": "Integración de báscula USB que envía peso como teclado en el POS",
    "description": """
        Permite usar una báscula USB que simula entrada de teclado en el POS de Odoo.

        Características:
        - Detecta automáticamente cuando la entrada tiene formato de peso (NN.DDD)
        - Aplica el peso como cantidad del producto seleccionado
        - No interfiere con el escaneo normal de códigos de barras
        - Configurable por punto de venta

        Formato esperado de la báscula:
        - Números decimales con formato NN.DDD (ej: 12.345, 0.500, 25.000)
        - La báscula debe enviar los datos como pulsaciones de teclado
        - Debe terminar con Enter o Tab
    """,
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
    ],
    "data": [
        "views/pos_config_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "xtendoo_pos_usb_scale/static/src/js/usb_scale_service.js",
            "xtendoo_pos_usb_scale/static/src/js/pos_store_patch.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
