# -*- coding: utf-8 -*-
from odoo import http

# class CrmLeadNumber(http.Controller):
#     @http.route('/crm_lead_number/crm_lead_number/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/crm_lead_number/crm_lead_number/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('crm_lead_number.listing', {
#             'root': '/crm_lead_number/crm_lead_number',
#             'objects': http.request.env['crm_lead_number.crm_lead_number'].search([]),
#         })

#     @http.route('/crm_lead_number/crm_lead_number/objects/<model("crm_lead_number.crm_lead_number"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('crm_lead_number.object', {
#             'object': obj
#         })