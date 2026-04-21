# Copyright 2026 Xtendoo - Manuel Calero
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Account Payment Return Import ISO20022 - Match by Concept",
    "summary": """
        Mejora el casado automático de devoluciones importadas desde ficheros
        ISO20022 (PAIN 002) usando el campo 'concept' (RmtInf/Ustrd) como
        referencia de factura y resolviendo el cliente por nombre exacto.""",
    "version": "18.0.1.0.0",
    "development_status": "Beta",
    "license": "AGPL-3",
    "author": "Xtendoo",
    "website": "https://xtendoo.es",
    "depends": [
        "account_payment_return_import_iso20022",
    ],
    "data": [],
    "installable": True,
    "auto_install": False,
}

