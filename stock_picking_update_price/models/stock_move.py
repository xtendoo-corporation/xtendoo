# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError

import logging


class StockMove(models.Model):
    _inherit = "stock.move"

    previous_cost_price = fields.Float('Previous Cost', digits=dp.get_precision('Product Price'))


class Picking(models.Model):
    _inherit = "stock.picking"

    move_ids_cost_prices = fields.One2many('stock.move', 'picking_id', string="Stock moves cost prices")
    picking_price_ids = fields.One2many('select.picking.price', 'picking_id')
    picking_price_count = fields.Integer(compute='_compute_picking_price_count')

    @api.multi
    def _compute_picking_price_count(self):
        for record in self:
            record.picking_price_count = len(self.picking_price_ids)

    @api.multi
    def button_validate(self):
        for line in self.move_lines:
            line.previous_cost_price = line.product_id.standard_price

        result = super(Picking, self).button_validate()

        for line in self.move_lines:
            line.current_cost_price = line.product_id.standard_price

        return result

    @api.multi
    def action_open_picking_prices(self):
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_('The selected picking does not have validated yet. Please validate the picking.'))
            return

        view = self.env.ref('stock_picking_update_price.select_picking_price_form')

        return {'name': _('Picking Prices'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'select.picking.price',
                'view_id': view.id,
                'views': [(view.id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'domain': [('id', 'in', self.picking_price_ids)],
                'context': {'default_picking_id': self.id}}

    # @api.multi
    # def action_stock_picking(self):
    #     pickings = self.order_ids.mapped('picking_id').filtered(lambda x: x.state != 'done')
    #     action_picking = self.env.ref('stock.action_picking_tree_ready')
    #     action = action_picking.read()[0]
    #     action['context'] = {}
    #     action['domain'] = [('id', 'in', pickings.ids)]
    #     return action


class StockMove(models.Model):
    _inherit = 'stock.move'

    def get_search_last_purchase(self, product_id, picking_id):
        return self.search(
            [['product_id', '=', product_id.id], ['picking_id', '<>', picking_id.id]], limit=1,
            order='date desc')
