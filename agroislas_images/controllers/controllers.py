# -*- coding: utf-8 -*-
from odoo import http

# class AgroislasImages(http.Controller):
#     @http.route('/agroislas_images/agroislas_images/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/agroislas_images/agroislas_images/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('agroislas_images.listing', {
#             'root': '/agroislas_images/agroislas_images',
#             'objects': http.request.env['agroislas_images.agroislas_images'].search([]),
#         })

#     @http.route('/agroislas_images/agroislas_images/objects/<model("agroislas_images.agroislas_images"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('agroislas_images.object', {
#             'object': obj
#         })