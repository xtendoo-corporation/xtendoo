from odoo import api, fields, models

import logging




class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def _default_pricelist(self):
        logging.info("*" * 20)
        logging.info(self.order_id)
        logging.info("*" * 20)

        return 1

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        store=True
    )

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        result=super().product_id_change()
        self.pricelist_id = self.order_id.pricelist_id.id
        logging.info(result.get('pricelist_id'))
        return result





