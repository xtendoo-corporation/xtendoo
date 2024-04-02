# -*- coding: utf-8 -*-
# Copyright 2021 - Daniel Domínguez https://xtendoo.es/

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('order_line')
    def _onchange_order_line(self):
        categories = []
        for line in self.order_line:
            categories.append(line.product_id.categ_id.id)
        used_categories = self.env["product.category"].search([('id', 'in', categories)])
        self.used_categories = used_categories

    @api.depends('order_line.product_id.categ_id')
    def _compute_used_categories(self):
        for order in self:
            categories = order.order_line.mapped('product_id.categ_id')
            order.used_categories = [(6, 0, categories.ids)]

    used_categories = fields.Many2many(
        'product.category',
        string='Categoria',
        compute=_compute_used_categories,
    )
