import base64
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    qr_content = fields.Char(
        string="Contenido del QR",
        copy=False,
        help="Texto o URL a codificar. Si está vacío: la URL pública del documento "
        "(si lo hay), código de barras, referencia interna o nombre.",
    )
    qr_image = fields.Binary(string="Imagen QR", attachment=True, copy=False)
    qr_image_filename = fields.Char(string="Nombre del fichero QR", copy=False)
    qr_document = fields.Binary(
        string="Documento QR (PDF o imagen)", attachment=True, copy=False,
        help="Archivo que se muestra al escanear el QR.",
    )
    qr_document_filename = fields.Char(string="Nombre del documento QR", copy=False)
    qr_access_token = fields.Char(string="Token QR", copy=False, index=True)
    qr_company_id = fields.Many2one(
        "res.company", string="Compañía del QR", copy=False,
        help="Compañía con la que se generó el QR; su URL y su activación rigen el acceso.",
    )
    qr_company_enabled = fields.Boolean(
        compute="_compute_qr_company_enabled",
        string="QR activo en la compañía",
    )

    @api.depends_context("company")
    def _compute_qr_company_enabled(self):
        enabled = self.env.company.qr_product_enabled
        for product in self:
            product.qr_company_enabled = enabled

    def _check_qr_company_enabled(self):
        if not self.env.company.qr_product_enabled:
            raise UserError(
                _("El QR de productos no está activado en la compañía %s.")
                % self.env.company.display_name
            )

    def _get_qr_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        if not self.qr_access_token:
            self.qr_access_token = secrets.token_urlsafe(16)
        return "%s/qr/producto/%s" % (base_url, self.qr_access_token)

    def _get_qr_value(self):
        self.ensure_one()
        return (
            self.qr_content
            or (self.qr_document and self._get_qr_url())
            or self.barcode
            or self.default_code
            or self.name
        )

    def action_generate_qr(self):
        self._check_qr_company_enabled()
        for product in self:
            value = product._get_qr_value()
            png = self.env["ir.actions.report"].barcode(
                "QR", value, width=400, height=400
            )
            product.write(
                {
                    "qr_image": base64.b64encode(png),
                    "qr_company_id": self.env.company.id,
                    "qr_image_filename": "qr_%s.png" % (product.default_code or product.id),
                }
            )
        return True

    def action_clear_qr(self):
        self._check_qr_company_enabled()
        self.write({"qr_image": False, "qr_image_filename": False})
        return True

    def action_print_qr(self):
        self._check_qr_company_enabled()
        return self.env.ref(
            "xtendoo_encapsulate_companies_qr.action_report_product_qr"
        ).report_action(self)
