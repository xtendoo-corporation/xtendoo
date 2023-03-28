# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2020-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from odoo import api, fields, models, _

class SaleOrderProductTemplate(models.Model):
    _inherit = "product.template"

    sale_order_qty = fields.Integer(string="Total sale order",compute='_compute_pending_sale_order_qty')

    def _compute_pending_sale_order_qty(self):
        for product in self:
            if product.sale_order_qty:
                continue
            if product:
                sale_order_qty = 0
                sale_order_line = self.env['sale.order.line'].search([('product_id.product_tmpl_id','=',product.id),('order_id.state','not in',('draft','done','cancel'))])
                if sale_order_line:
                    for sol in sale_order_line:
                        product.sale_order_qty += (sol.product_uom_qty - sol.qty_delivered)

    def display_pending_sale_order_qty(self):        
        if self.id:
            template_id = self.env.ref('sale.view_order_line_tree').id
            product_ids=[]
            so_line = self.env['sale.order.line'].search([('product_id.product_tmpl_id','=',self.id),('order_id.state','not in',('draft','done','cancel'))])
            for line_id in so_line:
                product_ids.append(line_id.id)
            return {
                    'name': _('List of Pending Sales Order Lines'),
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'sale.order.line',
                    'type': 'ir.actions.act_window',
                    'view_id': template_id,
                    'views': [(self.env.ref('sale.view_order_line_tree').id, 'tree')],
                    'domain': [('id','in',product_ids)]}

