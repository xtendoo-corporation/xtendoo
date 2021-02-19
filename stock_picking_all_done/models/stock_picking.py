# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def action_all_as_done(self):

        #_logger.info("*" * 80)
        #_logger.info("action_all_as_done")

        if not self.move_lines and not self.move_line_ids and not self.move_ids_without_package:
            raise UserError(_('Please add some items to move.'))

        if self.move_line_ids:
            for move_line in self.move_line_ids:
                move_line.qty_done = move_line.product_uom_qty

        if self.move_ids_without_package:
            for move_line in self.move_ids_without_package:
                move_line.quantity_done = move_line.product_qty

