#!/usr/bin/python3
# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
import base64
from odoo import http
from odoo.http import request, content_disposition


class Binary(http.Controller):
    @http.route('/web/binary/download_document', type='http', auth="public")
    # @serialize_exception
    def download_document(self, model, csv_wizard_id, filename=None):
        """
        Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str csv_wizard_id: id of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        wizard_id = request.env[model].browse([int(csv_wizard_id)])
        file_content = base64.b64decode(wizard_id.ebay_import_csv_data or '')
        if not file_content:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
            return request.make_response(
                file_content,
                [('Content-Type', 'application/octet-stream'), ('Content-Disposition', content_disposition(filename))])
