{
    "name": "Xtendoo Sale Barcode Scanner",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "summary": "Añade productos a pedidos de venta escaneando códigos de barras",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "AGPL-3",
    "depends": ["sale_management", "barcodes"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "xtendoo_sale_barcode_scanner/static/src/**/*.js",
        ],
        "web.assets_unit_tests": [
            "xtendoo_sale_barcode_scanner/static/tests/**/*.test.js",
        ],
    },
    "installable": True,
    "application": False,
}

