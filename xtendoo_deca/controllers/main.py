# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class XtendooDecaController(http.Controller):

    @http.route('/deca/<string:token>', type='http', auth='public', csrf=False, methods=['GET'])
    def download_deca(self, token, **kwargs):
        """Descarga directa del PDF del DeCA, sin autenticación ni
        interacción manual, tal y como exige el apartado Tercero.3 y 4 de la
        Resolución de 5 de junio de 2026 (BOE-A-2026-12784)."""
        doc = request.env['xtendoo.deca.document'].sudo().search([
            ('token', '=', token),
        ], limit=1)
        if not doc or not doc.download_enabled or not doc.pdf_file:
            return request.not_found()
        pdf_content = base64.b64decode(doc.pdf_file)
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', 'inline; filename="%s"' % (doc.pdf_filename or 'DeCA.pdf')),
        ]
        return request.make_response(pdf_content, headers=headers)
