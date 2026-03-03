# -*- coding: utf-8 -*-

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    feria_recharge_product_id = fields.Many2one(
        'product.product',
        string='Producto Recarga Monedero',
        help='Producto que se añadirá a la línea del pedido al pulsar el botón "Recarga".',
        domain=[('available_in_pos', '=', True)],
    )

    def _get_special_products(self):
        """Ensure the recharge product is loaded in the POS frontend."""
        res = super()._get_special_products()
        recharge_products = self.env['pos.config'].search([]).mapped('feria_recharge_product_id')
        return res | recharge_products


