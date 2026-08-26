{
    "name": "Portal sin datos económicos",
    "summary": "Perfil de portal que oculta y bloquea pedidos, facturas y pagos",
    "author": "Xtendoo",
    "website": "https://www.xtendoo.com",
    "license": "LGPL-3",
    "version": "19.0.1.0.0",
    "category": "Website/Portal",
    "depends": [
        "portal",
        "sale",
        "account",
        "account_payment",
        "payment",
    ],
    "data": [
        "security/portal_no_economics_groups.xml",
        "views/portal_templates.xml",
    ],
    "installable": True,
    "application": False,
}
