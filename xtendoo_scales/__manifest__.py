# -*- coding: utf-8 -*-
{
    'name': 'Xtendoo Scales',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Mejora la integración de básculas USB con el POS',
    'description': """
        Xtendoo Scales
        ==============

        Este módulo mejora la integración de básculas USB con el Point of Sale.

        Características:
        * Evita que las entradas numéricas de la báscula se interpreten como códigos de barras
        * Permite ingresar peso directamente cuando hay un producto seleccionado
        * Compatible con campos de cantidad y numpad
    """,
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'point_of_sale',
    ],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'xtendoo_scales/static/src/app/services/barcode_reader_service.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
