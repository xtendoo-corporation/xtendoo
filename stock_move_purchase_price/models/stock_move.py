# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"
    _description = "Stock Move"

    move_price_unit = fields.Float(
        'Move price unit', compute='_compute_move_price_unit',
        digits=dp.get_precision('Product Price'),
        readonly=True, help='Price that has already been assigned for this move')

    @api.multi
    def _compute_move_price_unit(self):
        """ Fill the `move price` field on a stock move
        """

        for record in self:
            if len(record.picking_id.purchase_id) > 0:
                for order_line in record.picking_id.purchase_id.order_line:
                    if order_line.product_id == record.product_id:
                        record.move_price_unit = order_line.price_unit

            if len(record.picking_id.sale_id) > 0:
                for order_line in record.picking_id.sale_id.order_line:
                    if order_line.product_id == record.product_id:
                        record.move_price_unit = order_line.price_unit
