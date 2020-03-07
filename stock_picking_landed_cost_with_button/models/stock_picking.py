# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    landing_ids = fields.Many2many(
        'stock.landed.cost', string='Landed',
        copy=False, states={'done': [('readonly', True)]})

    @api.multi
    def action_open_landed_cost(self):
        self.ensure_one()
        view = self.env.ref('stock_landed_costs.view_stock_landed_cost_form')
        action = {'name': _('Landed Costs'),
                  'view_type': 'form',
                  'view_mode': 'tree',
                  'res_model': 'stock.landed.cost',
                  'view_id': view.id,
                  'views': [(view.id, 'form')],
                  'type': 'ir.actions.act_window',
                  'context': {'default_picking_id': self.id}}

        if self.landing_ids:
            landing_ids = set([line.id for line in self.landing_ids])
            action['domain'] = "[('id', 'in', %s)]" % list(landing_ids)

            import logging 
            logging.info("*"*80)
            logging.info(landing_ids)
            logging.info("*"*80)

#            if len(landing_ids) == 1:
#                action['res_id'] = list(landing_ids)[0]
#            else:
#                action['domain'] = "[('id', 'in', %s)]" % list(landing_ids)

        return action

