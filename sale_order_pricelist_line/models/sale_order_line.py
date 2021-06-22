from odoo import api, fields, models

import logging




class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def _default_pricelist(self):
        logging.info("*" * 20)
        logging.info(self.env.id)
        logging.info("*" * 20)

        return self.order_id.pricelist_id

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        store=True
    )

    @api.onchange('product_id')
    def product_id_change(self):
        result = super().product_id_change()
        self.pricelist_id = self.order_id.pricelist_id.id
        return result





