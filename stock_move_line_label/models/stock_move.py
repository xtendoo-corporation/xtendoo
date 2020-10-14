# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.addons import decimal_precision as dp


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    label_qty = fields.Float(
        'Label Quantity',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Informative, not used in matching"
    )

    def action_edit_label(self):
        self.ensure_one()
        # Get the view
        view = self.env.ref('stock_move_line_label.view_stock_move_line_operation_label')
        return {
            'name': _('Label'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.move.line',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': dict(
                self.env.context
            ),
        }
