# -*- coding: utf-8 -*-
# Copyright 2021 - Daniel Domínguez https://xtendoo.es/

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    @api.onchange('order_line')
    def _onchange_order_line(self):
        print("/"*100)
        print("onchange order line")
        print("/"*100)
        self._get_used_categories()

    @api.model
    def _get_used_categories(self):
        print("*"*100)
        print("get used categories")
        print("*"*100)
        categories = []
        for line in self.order_line:
            categories.append(line.product_id.categ_id.id)
            print("-"*100)
        used_categories =self.env["product.category"].search([('id', 'in', categories)])
        self.used_categories = used_categories
        print("used categories", self.used_categories)
        print("-" * 100)




        #return self.env["product.category"].search([('id', '>', 0)])

    used_categories = fields.Many2many(
        'product.category',
        string='Categoria',
        default=lambda self: self._get_used_categories(),
        store=True,
    )
