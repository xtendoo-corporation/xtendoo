{
    "name": "AICIA - Importador de Proveedores, Clientes y Personal",
    "category": "Purchase",
    "version": "19.0.1.0.4",
    "depends": [
        "base",
        "purchase",
        "sale",
        "hr",
    ],
    "license": "AGPL-3",
    "application": True,
    "description": """
        Wizard para importar proveedores, clientes y personal desde archivos Excel.
        """,
    "data": [
        "security/ir.model.access.csv",
        "wizard/aicia_importer_wizard.xml",
        "views/aicia_importer_menu.xml"
    ],
    "external_dependencies": {
        "python": ["openpyxl"],
    },
    "installable": True,
}

