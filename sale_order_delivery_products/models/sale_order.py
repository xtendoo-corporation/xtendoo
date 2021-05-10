# Copyright 2021 Daniel Dominguez, Manuel Calero Solis - Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_view_picking(self):
        pick_ids = self.mapped('picking_ids')
        # no picking in this sale order
        if not pick_ids:
            return
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        # override the context to get rid of the default filtering on operation type
        result['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_origin': self.name,
        }
        result['domain'] = [('id', 'in', pick_ids.ids)]
        result['res_id'] = pick_ids[:1].id
        # choose the view_mode accordingly
        res = self.env.ref('stock.view_picking_form', False)
        form_view = [(res and res.id or False, 'form')]
        if 'views' in result:
            result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
        else:
            result['views'] = form_view
        return result

    def old_action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree_all')
        result = action.read()[0]
        # override the context to get rid of the default filtering on operation type
        result['context'] = {'default_partner_id': self.partner_id.id, 'default_origin': self.name}
        pick_ids = self.mapped('picking_ids')
        # choose the view_mode accordingly
        if not pick_ids:
            result['domain'] = "[('id','in',%s)]" % (pick_ids.ids)
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = pick_ids.id
        elif len(pick_ids) > 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            for picking in pick_ids:
                if picking.name.find('PIC') == 0:
                    result['res_id'] = picking.id
        return result
