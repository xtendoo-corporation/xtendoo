{
    "name": "Importation from gestool",
    "category": "Product",
    "version": "15.0.1.0",
    "depends": ["product"],
    "description": """
        Wizard to Import from gestool.
        """,
    "data": [
        "security/ir.model.access.csv",
        "wizard/webservice_import.xml",
        "views/webservice_import.xml"
    ],
    "installable": True,
    "auto_install": True,
}
