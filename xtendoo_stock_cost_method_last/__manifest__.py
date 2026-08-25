# Copyright 2016-2019 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Xtendoo Last Price Costing Method",
    "version": "17.0.1.0.0",
    "category": "Warehouse",
    "license": "AGPL-3",
    "summary": "Add a new Costing Method 'Last Price'",
    "author": "Akretion,Odoo Community Association (OCA), Camilo",
    "website": "https://github.com/OCA/stock-logistics-workflow",
    "depends": [
        "stock",
        "stock_account",
        "purchase",
        # l10n_es: dependencia técnica, no funcional. Sin ella, l10n_es
        # puede cargar sus datos (product_data.xml) antes de que este
        # módulo registre 'last' en property_cost_method, y la escritura
        # en product.product_category_all (valor ya guardado en producción)
        # falla con "Wrong value for ... property_cost_method: 'last'"
        # durante --update all. Ver dji 16->17, 2026-08-24.
        "l10n_es",
    ],
    "data": [
    #    "views/product.xml",
    ],
    "installable": True,
}
