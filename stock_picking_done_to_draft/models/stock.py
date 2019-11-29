# -*- coding: utf-8 -*-

from odoo import _, models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.multi
    def action_back_to_draft(self):
        if self.filtered(lambda m: m.state == 'done'):
            self.write({'state': 'draft'})
            self.write({'quantity_done': 0})
        self._action_confirm()
        self._action_assign()




class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.multi
    def action_back_to_draft(self):
        moves = self.mapped('move_lines')
        moves.action_back_to_draft()


