# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Xtendoo Product Barcode Report",
    "summary": "Añade un wizard en el que indicar cuantas etiquetas se van a generar",
    "version": "12.0.1.0.0",
    "author": "Dani Domínguez",
    "website": "https://xtendoo.es/",
    "license": "AGPL-3",
    "category": "Extra Tools",
    "depends": [
        "base",
        "product",
        "stock",
    ],
    "data": [
        "data/paperformat_label.xml",
        "report/report_label_barcode.xml",
        "report/report_label_barcode_template.xml",
        "wizard/product_barcode_selection_printing_view.xml",
    ],
    "installable": True,
}
