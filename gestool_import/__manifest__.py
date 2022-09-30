{
    "name": "Importation from gestool",
    "category": "Product",
    "version": "15.0.1.0",
    "depends": ["product"],
    "license": "AGPL-3",
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
