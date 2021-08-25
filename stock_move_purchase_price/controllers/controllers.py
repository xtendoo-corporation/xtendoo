# -*- coding: utf-8 -*-
from odoo import http

# class StockMiniumReport(http.Controller):
#     @http.route('/stock_move_purchase_price/stock_move_purchase_price/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/stock_move_purchase_price/stock_move_purchase_price/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('stock_move_purchase_price.listing', {
#             'root': '/stock_move_purchase_price/stock_move_purchase_price',
#             'objects': http.request.env['stock_move_purchase_price.stock_move_purchase_price'].search([]),
#         })

#     @http.route('/stock_move_purchase_price/stock_move_purchase_price/objects/<model("stock_move_purchase_price.stock_move_purchase_price"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('stock_move_purchase_price.object', {
#             'object': obj
#         })