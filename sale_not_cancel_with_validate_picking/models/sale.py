# Copyright 2021 Daniel Domínguez- Xtendoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        picking_ids=self.env['stock.picking'].search([
            ('sale_id', '=', self.id),
            ('state', '=', 'done')
        ])
        picking_validates=""
        if picking_ids:
            for picking in picking_ids:
                if picking_validates == '':
                    picking_validates= picking.name
                else:
                    picking_validates=picking_validates+", "+picking.name
            raise UserError(_("You cannot cancel an order with validated deliveries, you must first cancel %s") % (picking_validates))
        self.env['stock.picking'].search([
            ('sale_id', '=', self.id)
        ]).unlink()
        return res
