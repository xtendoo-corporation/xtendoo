{
    "name": "Importation from gestool",
    "category": "Product",
    "version": "17.0.1.0.0",
    "depends": ["product"],
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
