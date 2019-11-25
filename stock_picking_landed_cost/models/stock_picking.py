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

        action = {}
        action['name'] = _('Landed Costs')
        action['view_type'] = 'form'
        action['view_mode'] = 'tree'
        action['res_model'] = 'stock.landed.cost'
        action['view_id'] = view.id
        action['views'] = [(view.id, 'form')]
        action['type'] = 'ir.actions.act_window'
        action['context'] = {'default_picking_id': self.id}

        if self.landing_ids:
            landing_ids = set([line.id for line in self.landing_ids])
            if len(landing_ids) == 1:
                action['res_id'] = list(landing_ids)[0]
            else:
                action['domain'] = "[('id', 'in', %s)]" % list(landing_ids)
                
            # for landig in self.landing_ids:

        return action

        # return {
        #     'name': _('Landed Costs'),
        #     'view_type': 'form',
        #     'view_mode': 'tree',
        #     'res_model': 'stock.landed.cost',
        #     'view_id': view.id,
        #     'views': [(view.id, 'form')],
        #     'type': 'ir.actions.act_window',
        #     'context': {'default_picking_id': self.id},
        #     'target': 'current',
        # }

# self._context
# line_obj = self.env['purchase.cost.distribution.line']
# lines = line_obj.search([('picking_id', '=', self.id)])
# logging.getLogger("lines").warning("-"*80)
# logging.getLogger("lines").warning(lines)
# if lines:
#     mod_obj = self.env['ir.model.data']
#     model, action_id = tuple(
#         mod_obj.get_object_reference(
#             'purchase_landed_cost',
#             'action_purchase_cost_distribution'))
#     action = self.env[model].browse(action_id).read()[0]
#     ids = set([x.distribution.id for x in lines])
#     if len(ids) == 1:
#         res = mod_obj.get_object_reference(
#             'purchase_landed_cost', 'purchase_cost_distribution_form')
#         action['views'] = [(res and res[1] or False, 'form')]
#         action['res_id'] = list(ids)[0]
#     else:
#         action['domain'] = "[('id', 'in', %s)]" % list(ids)
#     return action

# from odoo import api, fields, models, _
# 
# class Picking(models.Model):
#     _inherit = "stock.picking"
# 
#     def button_test(self):
#         self.ensure_one()
#         view = self.env.ref('stock_landed_costs.view_stock_landed_cost_form')
#         
#         logging.getLogger("button_test").warning("-"*80)
#         logging.getLogger("button_test").warning("test button")
#         logging.getLogger("default_picking_id").warning(self.id)
# 
#         return {
#             'name': _('Landed Costs'),
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'stock.landed.cost',
#             'view_id': view.id,
#             'views': [(view.id, 'form')],
#             'type': 'ir.actions.act_window',
#             'context': {'default_picking_id': self.id},
#             'target': 'new',
#         }

