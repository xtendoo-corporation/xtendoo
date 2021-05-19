# © 2021 Manuel Calero - Xtendoo (https://xtendoo.es)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Product Recommendations in Website",
    "category": "e-commerce",
    "author": "Xtendoo, "
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/e-commerce",
    "version": "13.0.1.1.1",
    "license": "AGPL-3",
    "depends": [
        "website_sale"
    ],
    "data": [
        "data/website_menu.xml",
        "views/product_recommendations.xml",
    ],
    "demo": [
        "demo/assets.xml",
        "demo/product_brand_demo.xml",
        "demo/product_product_demo.xml",
    ],
    "installable": True,
}
