{
    "name": "Infortisa Product Import",
    "category": "Product",
    "version": "14.0.1.0",
    "depends": ["product"],
    "description": """
        Wizard to Import Infortisa Products.
        """,
    "depends": ["sale_management",],
    "data": ["wizard/infortisa_product_import.xml", "views/product.xml",],
    "installable": True,
    "auto_install": True,
}
