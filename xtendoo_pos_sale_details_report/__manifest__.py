# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
{
    "name": "Xtendoo - POS Daily Sales Report",
    "summary": (
        "Redesigns the POS daily sales report (X/Z): session summary, "
        "payments grouped by method with count and total, one line per "
        "product without barcodes or categories, and invoice summary."
    ),
    "version": "19.0.1.0.0",
    "category": "Sales/Point of Sale",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.es",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/report_saledetails.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
