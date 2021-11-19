{
    "name": "Importation from gestool",
    "category": "Product",
    "version": "14.0.1.0",
    "depends": ["product"],
    "description": """
        Wizard to Import from gestool.
        """,
    "data": [
        "security/ir.model.access.csv",
        "wizard/gestool_import.xml",
        "views/gestool_import.xml"
    ],
    "installable": True,
    "auto_install": True,
}
