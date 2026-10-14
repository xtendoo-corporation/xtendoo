from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    qr_product_enabled = fields.Boolean(
        string="Activar QR en productos",
        help="Si se activa, los productos mostrarán la pestaña QR únicamente "
        "mientras esta compañía sea la activa.",
    )
