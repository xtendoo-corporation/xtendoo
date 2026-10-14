{
    "name": "Multi-Company Encapsulate QR",
    "summary": "Código QR en productos, activable por compañía.",
    "description": "Permite activar el QR de producto en una compañía concreta. "
    "El resto de compañías no ve ni puede usar la funcionalidad.",
    "author": "Xtendoo",
    "category": "Technical",
    "version": "19.0.1.0.0",
    "depends": ["base", "product"],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "data": [
        "report/product_qr_report.xml",
        "views/res_company_views.xml",
        "views/product_template_views.xml",
    ],
}
