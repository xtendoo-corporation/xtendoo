# -*- coding: utf-8 -*-
# Copyright Xtendoo

{
    "name": "Print Labels in Picking with barcode 128",
    "summary": "Print Product Labels in a Stock Picking with barcode 128",
    "author": "dani-xtendoo",
    "website": "https://xtendoo.es",
    "category": "Warehouse",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["stock"],
    "data": [
        "reports/labels_print.xml",
        "reports/template_labels.xml",
        "reports/product_label_128.xml",
    ],
    "installable": True,
}
