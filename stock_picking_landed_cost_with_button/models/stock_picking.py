# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    landing_ids = fields.Many2many(
        'stock.landed.cost',
        string='Landed',
        copy=False,
        states={'done': [('readonly', True)]}
    )

    @api.multi
    def action_open_landed_cost(self):
        self.ensure_one()
        action = {'name': _('Landed Costs'),
                  'view_type': 'form',
                  'view_mode': 'tree',
                  'res_model': 'stock.landed.cost',
                  'type': 'ir.actions.act_window',
                  'context': {'default_picking_id': self.id}}
        landings = self.mapped('landing_ids')
        if len(landings) > 1:
            action['domain'] = [('id', 'in', landings.ids)]
            action['views'] = [
                (self.env.ref('stock_landed_costs.view_stock_landed_cost_tree').id, 'tree'),
                (self.env.ref('stock_landed_costs.view_stock_landed_cost_form').id, 'form'),
            ]
            return action
        if len(landings) == 1:
            action['views'] = [
                (self.env.ref('stock_landed_costs.view_stock_landed_cost_form').id, 'form')]
            action['res_id'] = landings.id
            return action
        action['views'] = [
            (self.env.ref('stock_landed_costs.view_stock_landed_cost_form').id, 'form')]
        return action

