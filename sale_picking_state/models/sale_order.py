# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    picking_state = fields.Selection(
        string="Picking status",
        readonly=True,
        compute="_compute_picking_state",
        selection="get_picking_state",
        help="Overall status based on all pickings",
        store=True,
    )

    @api.model
    def get_picking_state(self):
        return [
            ("draft",""),
            ("not_delivery", _("Nothing Delivery")),
            ("partially_delivered", _("Partially delivered")),
            ("delivered", _("Delivered")),
        ]

    @api.depends("order_line.qty_delivered","order_line.product_uom_qty")
    def _compute_picking_state(self):
        for sale in self:
            sale.picking_state = "draft"
            if sale.state not in ['draft', 'sent']:
                qty = 0
                qty_delivery = 0
                pickings_back_order = self.env['stock.picking'].search(
                    [('sale_id', '=', sale.id), ('state', 'not in', ['done', 'cancel'])])
                for line in sale.order_line:
                    qty += line.product_uom_qty
                    qty_delivery += line.qty_delivered
                if qty_delivery <= 0:
                    sale.picking_state = "not_delivery"
                else:
                    if pickings_back_order:
                        sale.picking_state = "partially_delivered"
                    else:
                        sale.picking_state = "delivered"



