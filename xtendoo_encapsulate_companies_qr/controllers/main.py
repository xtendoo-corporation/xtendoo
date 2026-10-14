from odoo import http
from odoo.http import request


class ProductQRController(http.Controller):
    @http.route("/qr/producto/<string:token>", type="http", auth="public", sitemap=False)
    def product_qr_document(self, token, **kwargs):
        product = (
            request.env["product.template"]
            .sudo()
            .search([("qr_access_token", "=", token), ("qr_document", "!=", False)], limit=1)
        )
        if not product or not product.qr_company_id.qr_product_enabled:
            return request.not_found()
        return (
            request.env["ir.binary"]
            ._get_stream_from(product, "qr_document", filename_field="qr_document_filename")
            .get_response()
        )
