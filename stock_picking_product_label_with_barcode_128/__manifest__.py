# -*- coding: utf-8 -*-
# Copyright Xtendoo

{
    "name": "Print Labels in Picking",
    "summary": "Print Product Labels in a Stock Picking",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-reporting",
    "category": "Warehouse",
    "version": "12.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["stock"],
    "data": [
        "reports/report_print_labels.xml",
        "reports/report_print_labels_template.xml",
    ],
    "installable": True,
}
