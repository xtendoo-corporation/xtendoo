{
    "name": "Importation from gestool",
    'author': 'Xtendoo',
    "category": "Product",
    "version": "19.0.1.1.0",
    "depends": [
        "point_of_sale",
        "product_multi_barcode",
    ],
    "license": "AGPL-3",
    "application": True,
    "description": """
        Wizard to Import from gestool.
        """,
    "data": [
        "security/ir.model.access.csv",
        "wizard/gestool_import.xml",
        "views/gestool_import.xml"
    ],
    "installable": True,
}
