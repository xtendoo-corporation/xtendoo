# -*- coding: utf-8 -*-
# Copyright 2021 - Abraham Carrasco https://xtendoo.es/

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.onchange('move_ids_without_package')
    def _onchange_move(self):
        categories = []
        for line in self.move_ids_without_package:
            categories.append(line.product_id.categ_id.id)
        stock_used_categories = self.env["product.category"].search([('id', 'in', categories)])
        self.stock_used_categories = stock_used_categories

    @api.depends('move_ids_without_package.product_id.categ_id')
    def _compute_stock_used_categories(self):
        for stock in self:
            categories = stock.move_ids_without_package.mapped('product_id.categ_id')
            stock.stock_used_categories = [(6, 0, categories.ids)]

    stock_used_categories = fields.Many2many(
        'product.category',
        string='Categoria',
        compute=_compute_stock_used_categories,
    )
