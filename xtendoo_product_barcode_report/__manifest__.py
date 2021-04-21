# Copyright 2020 Carlos Roca <carlos.roca@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Xtendoo Product Barcode Report",
    "summary": "It provides a wizard to select how many barcodes print.",
    "version": "12.0.1.0.0",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://odoo-community.org/",
    "license": "AGPL-3",
    "maintainers": ["CarlosRoca13"],
    "category": "Extra Tools",
    "depends": [
        "base",
        "product",
        "stock",
    ],
    "data": [
        #"views/res_config_settings_view.xml",
        "data/paperformat_label.xml",
        "report/report_label_barcode.xml",
        "report/report_label_barcode_template.xml",
        "wizard/product_barcode_selection_printing_view.xml",
    ],
    "installable": True,
}
