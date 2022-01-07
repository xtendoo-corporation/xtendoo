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
                for line in sale.order_line:
                    qty += line.product_uom_qty
                    qty_delivery += line.qty_delivered
                if qty_delivery == 0:
                    sale.picking_state = "not_delivery"
                elif qty_delivery == qty:
                    sale.picking_state = "delivered"
                elif qty_delivery < qty:
                    has_back_order = False
                    has_return = False
                    pickings_back_order = self.env['stock.picking'].search([('sale_id', '=', sale.id),('state', '!=', 'done')])
                    pickings = self.env['stock.picking'].search(
                        [('sale_id', '=', sale.id)])
                    if len(pickings) != 0:
                        for picking in pickings:
                            if picking.origin.find('Retorno') != -1:
                                has_return = True
                    if len(pickings_back_order) != 0:
                        has_back_order = True
                    if has_back_order or has_return:
                        sale.picking_state = "partially_delivered"
                    else:
                        sale.picking_state = "delivered"




