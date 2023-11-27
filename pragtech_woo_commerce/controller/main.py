# -*- coding: utf-8 -*-

import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WoocommerceController(http.Controller):

    @http.route(['/woocommerce_order_create'], type='json', auth='public', csrf=False)
    def woocommerce_order_create(self, **kwargs):
        data = request.jsonrequest
        request.env['sale.order'].sudo().woo_order_create(data)

    @http.route(['/woocommerce_order_update'], type='json', auth='public', csrf=False)
    def woocommerce_order_create(self, **kwargs):
        data = request.jsonrequest
        request.env['sale.order'].sudo().woo_order_update(data)
